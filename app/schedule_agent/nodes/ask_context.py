from app.schedule_agent.schemas import AgentState


def ask_context(state: AgentState) -> dict:
    """추가 질문 상태를 반환하거나 사용자 답변을 컨텍스트에 누적한다."""
    detail_with_context = state.get("detail_with_context") or state.get("detail", "")
    context_answer = state.get("context_answer", "").strip()
    question = state.get("question", "").strip()
    question_source = state.get("question_source", "")

    if context_answer:
        addition = f"\n추가 질문: {question}\n사용자 답변: {context_answer}" if question else f"\n사용자 답변: {context_answer}"
        detail_with_context = f"{detail_with_context}{addition}".strip()

    result = {
        "detail_with_context": detail_with_context,
        "status": "needs_question",
    }
    if question_source == "pre_validate":
        result["pre_validation_retry"] = state.get("pre_validation_retry", 0) + 1
        result["pre_validation_question"] = question
    else:
        result["classification_retry"] = state.get("classification_retry", 0) + 1
    return result
