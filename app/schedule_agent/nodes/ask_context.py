from app.schedule_agent.schemas import AgentState


def ask_context(state: AgentState) -> dict:
    """추가 질문을 반환하거나 사용자의 보충 답변을 누적 컨텍스트에 반영한다."""
    detail_with_context = state.get("detail_with_context") or state.get("detail", "")
    context_answer = state.get("context_answer", "").strip()
    question = state.get("question", "").strip()
    question_source = state.get("question_source", "")

    if context_answer:
        addition = f"\n추가 질문: {question}\n사용자 답변: {context_answer}" if question else f"\n사용자 답변: {context_answer}"
        return {
            "detail_with_context": f"{detail_with_context}{addition}".strip(),
            "is_decomposable": state.get("is_decomposable", True),
        }

    result = {
        "detail_with_context": detail_with_context,
        "is_decomposable": state.get("is_decomposable", True),
        "status": "needs_question",
    }
    if question_source == "pre_validate":
        result["pre_validation_retry"] = state.get("pre_validation_retry", 0) + 1
    else:
        result["classification_retry"] = state.get("classification_retry", 0) + 1
    return result
