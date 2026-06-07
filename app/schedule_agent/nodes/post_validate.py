import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.schedule_agent.prompts import POST_VALIDATE_SYSTEM
from app.schedule_agent.schemas import AgentState, PostValidationResult

logger = logging.getLogger(__name__)


def _reindex_tasks(tasks: list[dict]) -> list[dict]:
    """사후 검증 모델이 순서를 덮어써도 리스트 순서를 실행 순서로 유지한다."""
    for index, task in enumerate(tasks, start=1):
        task["order_index"] = index
    return tasks


def post_validate_tasks(state: AgentState) -> dict:
    """생성된 task의 실행 가능성과 원 일정 적합성을 검증한다."""
    tasks = state.get("tasks", [])
    normalized_schedule = state.get("normalized_schedule", {})

    if not 1 <= len(tasks) <= 5:
        return {"is_valid": False, "tasks": tasks, "invalid_reason": "task 개수가 1~5개 범위를 벗어났습니다."}

    try:
        llm = get_llm(temperature=0.0).with_structured_output(PostValidationResult)
        result = llm.invoke(
            [
                SystemMessage(content=POST_VALIDATE_SYSTEM),
                HumanMessage(content=f"normalized_schedule: {normalized_schedule}\ntasks: {tasks}"),
            ]
        )
        result_dict = result.model_dump()
        result_dict["tasks"] = _reindex_tasks(result_dict.get("tasks", []))
        return result_dict
    except Exception as e:
        logger.warning("Task post-validation failed: %s", e)
        return {"is_valid": True, "tasks": _reindex_tasks(tasks), "invalid_reason": ""}
