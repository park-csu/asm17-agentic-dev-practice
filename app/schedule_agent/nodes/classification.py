import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.schedule_agent.prompts import CLASSIFICATION_SYSTEM
from app.schedule_agent.schemas import AgentState, ClassificationResult

logger = logging.getLogger(__name__)


def classify_schedule(state: AgentState) -> dict:
    """일정이 task 분해 가능한 수준인지 판단하고 추가 질문을 생성한다."""
    title = state.get("title", "")
    detail = state.get("detail", "")
    detail_with_context = state.get("detail_with_context") or detail
    start_time = state.get("start_time", "")
    end_time = state.get("end_time", "")

    if state.get("classification_retry", 0) >= state.get("max_retry", 2):
        return {
            "is_decomposable": state.get("is_decomposable", True),
            "needs_question": False,
            "question": "",
            "question_source": "",
            "detail_with_context": detail_with_context,
        }

    try:
        llm = get_llm(temperature=0.0).with_structured_output(ClassificationResult)
        result = llm.invoke(
            [
                SystemMessage(content=CLASSIFICATION_SYSTEM),
                HumanMessage(
                    content=(
                        f"title: {title}\n"
                        f"detail: {detail}\n"
                        f"detail_with_context: {detail_with_context}\n"
                        f"start_time: {start_time}\n"
                        f"end_time: {end_time}"
                    )
                ),
            ]
        )
        result_dict = result.model_dump()
        if not result_dict["is_decomposable"]:
            result_dict["needs_question"] = False
            result_dict["question"] = ""
        result_dict["question_source"] = "classification" if result_dict["needs_question"] else ""
        return result_dict
    except Exception as e:
        logger.warning("Schedule classification failed: %s", e)
        needs_question = not start_time or not end_time or len(f"{title} {detail_with_context}".strip()) < 8
        return {
            "is_decomposable": True,
            "needs_question": needs_question,
            "question": "이 일정은 언제부터 언제까지 진행하고, 어떤 결과물이 나오면 될까요?" if needs_question else "",
            "question_source": "classification" if needs_question else "",
            "detail_with_context": detail_with_context,
        }
