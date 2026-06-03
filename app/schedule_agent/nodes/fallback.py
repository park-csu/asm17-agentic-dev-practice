from app.schedule_agent.prompts import FALLBACK_MESSAGE
from app.schedule_agent.schemas import AgentState


def build_fallback(state: AgentState) -> dict:
    """정상 task 생성이 불가능할 때 실패 결과를 반환한다."""
    fallback_reason = state.get("invalid_reason", "") or state.get("fallback_reason", "") or FALLBACK_MESSAGE
    return {
        "status": "fallback",
        "title": state.get("title", ""),
        "detail_with_context": state.get("detail_with_context") or state.get("detail", ""),
        "start_time": state.get("start_time", ""),
        "end_time": state.get("end_time", ""),
        "tasks": [],
        "fallback_reason": fallback_reason,
        "answer": fallback_reason,
    }
