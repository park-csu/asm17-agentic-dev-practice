import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.schedule_agent.prompts import PLAN_SYSTEM
from app.schedule_agent.schemas import AgentState, PlanResult

logger = logging.getLogger(__name__)


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

    return {"tasks": payload.get("tasks", []), "plan_reason": payload.get("plan_reason", ""), "plan_retry": state.get("plan_retry", 0) + 1}
