import logging
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.schedule_agent.prompts import PLAN_SYSTEM
from app.schedule_agent.schemas import AgentState, PlanResult

logger = logging.getLogger(__name__)


def _parse_dt(value: str) -> datetime | None:
    """ISO 8601 또는 'YYYY-MM-DD HH:MM' 형식의 시간 문자열을 파싱한다."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _resolve_total_minutes(normalized_schedule: dict, state: AgentState) -> int | None:
    """일정 전체 길이(분)를 구한다.

    LLM이 채운 duration_minutes는 부정확할 수 있으므로(예: 120분 일정을 150분으로 계산),
    사용자가 실제 입력한 start/end로 직접 계산한 값을 최우선으로 신뢰한다.
    시간을 해석할 수 없을 때만 duration_minutes를 최후 수단으로 쓴다.
    """
    for source in (state, normalized_schedule):
        start = _parse_dt(str(source.get("start_time", "")))
        end = _parse_dt(str(source.get("end_time", "")))
        if start and end and end > start:
            return int((end - start).total_seconds() // 60)

    duration = normalized_schedule.get("duration_minutes")
    if isinstance(duration, int) and duration > 0:
        return duration
    return None


def _scale_tasks_to_duration(tasks: list[dict], total_minutes: int) -> None:
    """LLM이 매긴 estimated_minutes를 '작업별 소요 시간 비율'로 보고, 합이 정확히
    total_minutes가 되도록 비례 조정한다.

    예) LLM이 10/20/30/10 (비율 1:2:3:1)을 줬고 전체가 140분이면 → 20/40/60/20 (합 140).
        값이 전부 동일하면 비율도 같으므로 자연스럽게 균등 분배가 된다.

    - 비율 정보가 전혀 없으면(전부 0) 균등 분배로 폴백한다.
    - 각 task는 최소 1분을 보장하고, 반올림 오차는 앞쪽 task부터 1분씩 가감해 합을 정확히 맞춘다.
    """
    count = len(tasks)

    # LLM이 매긴 시간을 비율(가중치)로 사용한다(유효하지 않으면 0).
    weights: list[int] = []
    for task in tasks:
        value = task.get("estimated_minutes")
        weights.append(value if isinstance(value, int) and value > 0 else 0)
    weight_sum = sum(weights)

    if weight_sum == 0:
        # 비율 정보가 없으면 균등 분배
        base = total_minutes // count
        remainder = total_minutes - base * count
        allocated = [max(1, base + (1 if i < remainder else 0)) for i in range(count)]
    else:
        # 비율에 맞춰 전체 시간에 비례 분배 (weight × total / weight_sum)
        allocated = [max(1, round(weight * total_minutes / weight_sum)) for weight in weights]

    # 반올림·최소값 보정으로 합이 어긋나면 앞쪽 task부터 1분씩 조정해 정확히 total_minutes로 맞춘다.
    diff = total_minutes - sum(allocated)
    cursor = 0
    guard = 0
    max_iterations = total_minutes + count + 1
    while diff != 0 and guard < max_iterations:
        index = cursor % count
        if diff > 0:
            allocated[index] += 1
            diff -= 1
        elif allocated[index] > 1:
            allocated[index] -= 1
            diff += 1
        cursor += 1
        guard += 1

    for task, minutes in zip(tasks, allocated):
        task["estimated_minutes"] = minutes


def _normalize_task_fields(tasks: list[dict], total_minutes: int | None) -> list[dict]:
    """LLM이 제대로 채우지 못하는 순서/시간 필드를 일정 정보 기반으로 보정한다.

    - order_index: LLM이 모두 1로 채우는 경향이 있어, 리스트 순서(=실행 순서)대로 1..n으로 재부여한다.
    - estimated_minutes: LLM이 매긴 값을 '상대 비율'로 보고, 합이 일정 전체 길이가 되도록 비례 분배한다.
    """
    if not tasks:
        return tasks

    # order_index 재부여: 리스트에 담긴 순서를 실행 순서로 간주한다.
    for index, task in enumerate(tasks, start=1):
        task["order_index"] = index

    if isinstance(total_minutes, int) and total_minutes > 0:
        _scale_tasks_to_duration(tasks, total_minutes)

    return tasks


def _build_plan_human_message(
    normalized_schedule: dict,
    invalid_reason: str,
    previous_tasks: list[dict],
    total_minutes: int | None,
) -> str:
    """plan LLM 호출용 사용자 메시지를 구성한다.

    각 task의 estimated_minutes를 '작업별 소요 시간 비율'의 근거로 사용하므로, 작업마다
    현실적으로 다른 소요 시간을 매기도록 안내한다. 실제 합은 코드(_scale_tasks_to_duration)가
    전체 시간에 맞춰 정확히 조정한다.

    post_validate가 task를 거부해 plan으로 재진입한 경우(invalid_reason이 채워진 경우)에는
    거부 사유와 직전 task를 함께 전달해, 같은 문제를 반복하지 않고 교정하도록 유도한다.
    """
    lines = [f"normalized_schedule: {normalized_schedule}"]
    if isinstance(total_minutes, int) and total_minutes > 0:
        lines.append(
            f"available_minutes: {total_minutes}\n"
            "# estimated_minutes 지침 (반드시 따를 것):\n"
            "# - 모든 task에 같은 시간을 주지 마라. 작업 성격에 따라 소요 시간을 분명히 다르게 매겨라.\n"
            "# - 오래 걸리는 작업(예: 조리, 굽기, 끓이기)은 길게, 짧은 준비/마무리(예: 그릇 배치, 확인)는 짧게.\n"
            "# - 절대 시간이 아니라 '작업 간 상대 비율'이 중요하다. 정확한 총합은 시스템이 "
            f"available_minutes({total_minutes}분)에 맞춰 자동 조정하므로, 비율만 현실적으로 매기면 된다."
        )
    if invalid_reason:
        lines.append("")
        lines.append("[재생성 요청] 직전에 생성한 task가 사후 검증에서 다음 사유로 거부되었습니다.")
        lines.append(f"invalid_reason: {invalid_reason}")
        if previous_tasks:
            lines.append(f"rejected_tasks: {previous_tasks}")
        lines.append("위 거부 사유를 반드시 해소하도록 task를 다시 구성하세요. 거부된 task를 그대로 반복하지 마세요.")
    return "\n".join(lines)


def plan_tasks(state: AgentState) -> dict:
    """정규화된 일정을 실행 가능한 task 1~5개로 분해한다.

    post_validate에서 거부되어 재진입한 경우, state의 invalid_reason과 직전 task를
    프롬프트에 반영해 거부 사유를 해소하는 방향으로 task를 재생성한다.
    """
    normalized_schedule = state.get("normalized_schedule", {})
    invalid_reason = state.get("invalid_reason", "")
    previous_tasks = state.get("tasks", [])
    total_minutes = _resolve_total_minutes(normalized_schedule, state)

    try:
        llm = get_llm(temperature=0.2).with_structured_output(PlanResult)
        human_message = _build_plan_human_message(normalized_schedule, invalid_reason, previous_tasks, total_minutes)
        result = llm.invoke([SystemMessage(content=PLAN_SYSTEM), HumanMessage(content=human_message)])
        payload = result.model_dump()
    except Exception as e:
        logger.warning("Task planning failed: %s", e)
        title = normalized_schedule.get("title", "일정")
        payload = {
            "tasks": [
                {"title": f"{title} 준비하기", "description": "일정 수행에 필요한 자료와 조건을 확인합니다.", "estimated_minutes": 30, "order_index": 1},
                {"title": f"{title} 실행하기", "description": "확인한 조건에 맞춰 핵심 작업을 수행합니다.", "estimated_minutes": 60, "order_index": 2},
            ],
            "plan_reason": "LLM 계획 생성 실패로 기본 2단계 task를 생성했습니다.",
        }

    tasks = _normalize_task_fields(payload.get("tasks", []), total_minutes)
    # 이번 재생성으로 직전 거부 사유를 소비했으므로 invalid_reason을 비운다.
    # post_validate가 새 task를 다시 판단해 필요 시 새로운 사유를 채운다.
    return {
        "tasks": tasks,
        "plan_reason": payload.get("plan_reason", ""),
        "plan_retry": state.get("plan_retry", 0) + 1,
        "invalid_reason": "",
    }
