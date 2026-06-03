import logging
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.schedule_agent.prompts import PRE_VALIDATE_SYSTEM
from app.schedule_agent.schemas import AgentState, PreValidationResult

logger = logging.getLogger(__name__)

PHYSICAL_LOCATION_KEYWORDS = (
    "대면",
    "현장",
    "방문",
    "고객사",
    "사무실에 도착",
    "도착한 뒤",
)
FLEXIBLE_LOCATION_KEYWORDS = (
    "온라인",
    "원격",
    "화상",
    "이동 중",
    "노트북",
    "장소 무관",
)
QUESTION_PLACEHOLDER_KEYWORDS = (
    "null string",
    "empty string",
    "default value",
)


def parse_iso_datetime(value: str) -> datetime | None:
    """ISO 8601 시간 문자열을 파싱하고, 해석할 수 없으면 None을 반환한다."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def find_schedule_conflict(
    start_at: datetime,
    end_at: datetime,
    existing_schedules: list[dict],
) -> dict | None:
    """해석 가능한 기존 일정 중 요청 시간 범위와 겹치는 첫 일정을 반환한다."""
    for schedule in existing_schedules:
        existing_start = parse_iso_datetime(str(schedule.get("start_time", "")))
        existing_end = parse_iso_datetime(str(schedule.get("end_time", "")))
        if not existing_start or not existing_end:
            continue
        try:
            if start_at < existing_end and existing_start < end_at:
                return schedule
        except TypeError:
            continue
    return None


def build_travel_context(
    location: str,
    start_at: datetime | None,
    end_at: datetime | None,
    existing_schedules: list[dict],
) -> list[dict]:
    """위치가 명시된 비충돌 일정과 요청 일정 사이의 이동 시간 후보를 만든다."""
    if not location.strip() or not start_at or not end_at:
        return []

    travel_context = []
    for schedule in existing_schedules:
        existing_location = str(schedule.get("location", "")).strip()
        existing_start = parse_iso_datetime(str(schedule.get("start_time", "")))
        existing_end = parse_iso_datetime(str(schedule.get("end_time", "")))
        if not existing_location or not existing_start or not existing_end:
            continue
        try:
            if existing_end <= start_at:
                gap_minutes = int((start_at - existing_end).total_seconds() // 60)
                relation = "existing_before_request"
            elif end_at <= existing_start:
                gap_minutes = int((existing_start - end_at).total_seconds() // 60)
                relation = "request_before_existing"
            else:
                continue
        except TypeError:
            continue
        travel_context.append(
            {
                "request_location": location,
                "existing_title": str(schedule.get("title", "")),
                "existing_location": existing_location,
                "relation": relation,
                "gap_minutes": gap_minutes,
            }
        )
    return travel_context


def needs_location_requirement_question(
    title: str,
    detail_with_context: str,
    context_answer: str,
    travel_context: list[dict],
) -> bool:
    """위치 이동 검증에 필요한 장소 제약이 아직 불명확한지 판단한다."""
    if not travel_context or context_answer.strip():
        return False
    text = f"{title} {detail_with_context}".lower()
    has_physical_cue = any(keyword in text for keyword in PHYSICAL_LOCATION_KEYWORDS)
    has_flexible_cue = any(keyword in text for keyword in FLEXIBLE_LOCATION_KEYWORDS)
    return not has_physical_cue and not has_flexible_cue


def has_meaningful_question(question: str) -> bool:
    """모델이 실제 사용자 질문을 생성했는지 확인한다."""
    normalized = question.strip().lower()
    return bool(normalized) and not any(
        keyword in normalized for keyword in QUESTION_PLACEHOLDER_KEYWORDS
    )


def pre_validate_schedule(state: AgentState, *, strict: bool = False) -> dict:
    """일정 자체의 유효성과 시작/종료 시간 해석 가능 여부를 검증한다.

    strict 모드는 실제 LLM 성능 평가에서 모델 호출 또는 구조화 출력 오류를
    정상 결과로 오인하지 않도록 예외를 다시 발생시킨다.
    """
    title = state.get("title", "")
    detail_with_context = state.get("detail_with_context") or state.get("detail", "")
    location = state.get("location", "")
    context_answer = state.get("context_answer", "")
    pre_validation_question = state.get("pre_validation_question", "")
    start_time = state.get("start_time", "")
    end_time = state.get("end_time", "")
    existing_schedules = state.get("existing_schedules", [])

    if not title.strip() and not detail_with_context.strip():
        return {"is_valid": False, "normalized_schedule": {}, "invalid_reason": "일정 제목과 상세 내용이 모두 비어 있습니다."}
    if not start_time.strip() or not end_time.strip():
        return {"is_valid": False, "normalized_schedule": {}, "invalid_reason": "일정 시작 시간 또는 종료 시간이 비어 있어 해석할 수 없습니다."}

    start_at = parse_iso_datetime(start_time)
    end_at = parse_iso_datetime(end_time)
    if start_at and end_at:
        try:
            has_invalid_range = start_at >= end_at
        except TypeError:
            return {
                "is_valid": False,
                "normalized_schedule": {},
                "invalid_reason": "일정 시작 시간과 종료 시간의 시간대 형식이 서로 다릅니다.",
            }
        if has_invalid_range:
            return {
                "is_valid": False,
                "normalized_schedule": {},
                "invalid_reason": "일정 시작 시간은 종료 시간보다 빨라야 합니다.",
            }
        conflict = find_schedule_conflict(start_at, end_at, existing_schedules)
        if conflict:
            conflict_title = str(conflict.get("title", "")).strip()
            suffix = f" ({conflict_title})" if conflict_title else ""
            return {
                "is_valid": False,
                "normalized_schedule": {},
                "invalid_reason": f"기존 일정과 시간이 겹칩니다.{suffix}",
            }

    travel_context = build_travel_context(
        location,
        start_at,
        end_at,
        existing_schedules,
    )
    location_question_needed = needs_location_requirement_question(
        title,
        detail_with_context,
        context_answer,
        travel_context,
    )

    try:
        llm = get_llm(temperature=0.0).with_structured_output(PreValidationResult)
        result = llm.invoke(
            [
                SystemMessage(content=PRE_VALIDATE_SYSTEM),
                HumanMessage(
                    content=(
                        f"title: {title}\n"
                        f"detail_with_context: {detail_with_context}\n"
                        f"location: {location}\n"
                        f"pre_validation_question: {pre_validation_question}\n"
                        f"context_answer: {context_answer}\n"
                        f"start_time: {start_time}\n"
                        f"end_time: {end_time}\n"
                        f"existing_schedules: {existing_schedules}\n"
                        f"travel_context: {travel_context}"
                    )
                ),
            ]
        )
        result_dict = result.model_dump()
        if location_question_needed:
            result_dict["needs_question"] = True
            result_dict["is_valid"] = False
            result_dict["invalid_reason"] = ""
            if not has_meaningful_question(result_dict["question"]):
                result_dict["question"] = (
                    "이 작업은 해당 장소에 도착해야만 가능한가요, "
                    "아니면 이동 중이나 온라인으로도 가능한가요?"
                )
        elif result_dict["needs_question"]:
            result_dict["needs_question"] = False
            result_dict["question"] = ""

        if result_dict["needs_question"]:
            if state.get("pre_validation_retry", 0) >= state.get("max_retry", 2):
                return {
                    "is_valid": False,
                    "needs_question": False,
                    "question": "",
                    "question_source": "",
                    "normalized_schedule": {},
                    "invalid_reason": "위치 제약을 확인하지 못해 일정 유효성을 판단할 수 없습니다.",
                }
            result_dict["is_valid"] = False
            result_dict["question_source"] = "pre_validate"
            result_dict["pre_validation_question"] = result_dict["question"]
            result_dict["invalid_reason"] = ""
            return result_dict
        if not result_dict["is_valid"] and not result_dict["invalid_reason"].strip():
            if not start_at or not end_at:
                result_dict["invalid_reason"] = "일정 시간 표현을 해석할 수 없습니다."
            elif travel_context:
                result_dict["invalid_reason"] = "일정 위치 간 이동 가능성을 충족하지 못했습니다."
            else:
                result_dict["invalid_reason"] = "일정의 목적 또는 실행 조건이 유효성 검증 기준을 충족하지 못했습니다."
        result_dict["question_source"] = ""
        return result_dict
    except Exception as e:
        logger.warning("Schedule pre-validation failed: %s", e)
        if strict:
            raise
        return {
            "is_valid": False,
            "normalized_schedule": {},
            "invalid_reason": "일정 유효성 검증 중 오류가 발생했습니다.",
        }
