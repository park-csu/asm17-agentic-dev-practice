import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.schedule_agent.prompts import PLAN_SYSTEM
from app.schedule_agent.schemas import AgentState, PlanResult

logger = logging.getLogger(__name__)


def _normalize_task_fields(tasks: list[dict], normalized_schedule: dict) -> list[dict]:
    """LLM이 제대로 채우지 못하는 순서/시간 필드를 일정 정보 기반으로 보정한다.

    - order_index: LLM이 모두 1로 채우는 경향이 있어, 리스트 순서(=실행 순서)대로 1..n으로 재부여한다.
    - estimated_minutes: 값이 전부 동일(기본값 등)하고 일정 전체 길이(duration_minutes)를 알 수 있으면
      균등 분배해 합이 일정 길이와 어긋나지 않게 한다. LLM이 값을 다양하게 채운 경우에는 그대로 둔다.
    """
    if not tasks:
        return tasks

    # order_index 재부여: 리스트에 담긴 순서를 실행 순서로 간주한다.
    for index, task in enumerate(tasks, start=1):
        task["order_index"] = index

    # estimated_minutes 보정: 값이 전부 동일하고 일정 전체 길이를 알 때만 균등 분배한다.
    total_minutes = normalized_schedule.get("duration_minutes")
    estimated_values = [task.get("estimated_minutes") for task in tasks]
    is_uniform = len(set(estimated_values)) <= 1
    if isinstance(total_minutes, int) and total_minutes > 0 and is_uniform:
        task_count = len(tasks)
        base_minutes = total_minutes // task_count
        remainder = total_minutes - base_minutes * task_count
        for offset, task in enumerate(tasks):
            # 나머지는 앞쪽 task부터 1분씩 더해 합이 정확히 total_minutes가 되도록 한다.
            task["estimated_minutes"] = max(1, base_minutes + (1 if offset < remainder else 0))

    return tasks


def plan_tasks(state: AgentState) -> dict:
    """정규화된 일정을 실행 가능한 task 1~5개로 분해한다."""
    normalized_schedule = state.get("normalized_schedule", {})

    try:
        llm = get_llm(temperature=0.2).with_structured_output(PlanResult)
        result = llm.invoke([SystemMessage(content=PLAN_SYSTEM), HumanMessage(content=f"normalized_schedule: {normalized_schedule}")])
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

    tasks = _normalize_task_fields(payload.get("tasks", []), normalized_schedule)
    return {"tasks": tasks, "plan_reason": payload.get("plan_reason", ""), "plan_retry": state.get("plan_retry", 0) + 1}
