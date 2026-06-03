import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.schedule_agent.prompts import PRE_VALIDATE_SYSTEM
from app.schedule_agent.schemas import AgentState, PreValidationResult

logger = logging.getLogger(__name__)


def pre_validate_schedule(state: AgentState) -> dict:
    """일정 자체의 유효성과 시작/종료 시간 해석 가능 여부를 검증한다."""
    title = state.get("title", "")
    detail_with_context = state.get("detail_with_context") or state.get("detail", "")
    start_time = state.get("start_time", "")
    end_time = state.get("end_time", "")
    existing_schedules = state.get("existing_schedules", [])

    if not title.strip() and not detail_with_context.strip():
        return {"is_valid": False, "normalized_schedule": {}, "invalid_reason": "일정 제목과 상세 내용이 모두 비어 있습니다."}
    if not start_time.strip() or not end_time.strip():
        return {"is_valid": False, "normalized_schedule": {}, "invalid_reason": "일정 시작 시간 또는 종료 시간이 비어 있어 해석할 수 없습니다."}

    try:
        llm = get_llm(temperature=0.0).with_structured_output(PreValidationResult)
        result = llm.invoke(
            [
                SystemMessage(content=PRE_VALIDATE_SYSTEM),
                HumanMessage(
                    content=(
                        f"title: {title}\n"
                        f"detail_with_context: {detail_with_context}\n"
                        f"start_time: {start_time}\n"
                        f"end_time: {end_time}\n"
                        f"existing_schedules: {existing_schedules}"
                    )
                ),
            ]
        )
        return result.model_dump()
    except Exception as e:
        logger.warning("Schedule pre-validation failed: %s", e)
        return {
            "is_valid": True,
            "normalized_schedule": {
                "title": title,
                "detail": detail_with_context,
                "start_time": start_time,
                "end_time": end_time,
                "existing_schedules_checked": bool(existing_schedules),
            },
            "invalid_reason": "",
        }
