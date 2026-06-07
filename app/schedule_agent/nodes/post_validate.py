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
        # post_validate는 유효성만 판단한다. task 내용/시간은 plan이 만든 원본(tasks)을 유지해,
        # 검증 LLM의 재출력이 estimated_minutes를 기본값(30)으로 덮어쓰는 것을 막는다.
        return {
            "is_valid": result_dict["is_valid"],
            "tasks": _reindex_tasks(tasks),
            "invalid_reason": result_dict.get("invalid_reason", ""),
        }
    except Exception as e:
        logger.warning("Task post-validation failed: %s", e)
        return {"is_valid": True, "tasks": _reindex_tasks(tasks), "invalid_reason": ""}
