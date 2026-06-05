from langgraph.graph import END, START, StateGraph

from app.schedule_agent.nodes.ask_context import ask_context
from app.schedule_agent.nodes.classification import classify_schedule
from app.schedule_agent.nodes.fallback import build_fallback
from app.schedule_agent.nodes.output import build_output
from app.schedule_agent.nodes.plan import plan_tasks
from app.schedule_agent.nodes.post_validate import post_validate_tasks
from app.schedule_agent.nodes.pre_validate import pre_validate_schedule
from app.schedule_agent.schemas import AgentState


def route_from_start(state: AgentState) -> str:
    """보충 답변이 있으면 먼저 누적 컨텍스트에 반영한다."""
    return "ask_context" if state.get("context_answer", "").strip() else "pre_validate"


def route_after_ask_context(state: AgentState) -> str:
    """질문 반환 또는 보충 답변 반영 이후 다음 노드를 결정한다."""
    if state.get("context_answer", "").strip():
        return "pre_validate" if state.get("question_source") == "pre_validate" else "classification"
    return "end"


def route_after_pre_validate(state: AgentState) -> str:
    """유효성 검증 결과에 따라 질문, 분류 또는 실패로 이동한다."""
    retry = state.get("pre_validation_retry", 0)
    max_retry = state.get("max_retry", 2)
    if state.get("needs_question", False) and retry < max_retry:
        return "ask_context"
    if not state.get("is_valid", False):
        return "fallback"
    return "classification"


def route_after_classification(state: AgentState) -> str:
    """분해 가능 여부와 추가 질문 필요성에 따라 다음 노드를 결정한다."""
    retry = state.get("classification_retry", 0)
    max_retry = state.get("max_retry", 2)
    if state.get("needs_question", False) and retry < max_retry:
        return "ask_context"
    if not state.get("is_decomposable", True):
        return "output"
    return "plan"


def route_after_post_validate(state: AgentState) -> str:
    """task 검증 결과와 재시도 횟수에 따라 다음 노드를 결정한다."""
    if state.get("is_valid", False):
        return "output"
    if state.get("plan_retry", 0) < state.get("max_retry", 2):
        return "plan"
    return "fallback"


def create_graph():
    """일정 서브태스크 생성 워크플로우 그래프를 생성한다."""
    builder = StateGraph(AgentState)

    builder.add_node("pre_validate", pre_validate_schedule)
    builder.add_node("classification", classify_schedule)
    builder.add_node("ask_context", ask_context)
    builder.add_node("plan", plan_tasks)
    builder.add_node("post_validate", post_validate_tasks)
    builder.add_node("output", build_output)
    builder.add_node("fallback", build_fallback)

    builder.add_conditional_edges(
        START,
        route_from_start,
        {"ask_context": "ask_context", "pre_validate": "pre_validate"},
    )
    builder.add_conditional_edges(
        "pre_validate",
        route_after_pre_validate,
        {"ask_context": "ask_context", "classification": "classification", "fallback": "fallback"},
    )
    builder.add_conditional_edges(
        "ask_context",
        route_after_ask_context,
        {"pre_validate": "pre_validate", "classification": "classification", "end": END},
    )
    builder.add_conditional_edges(
        "classification",
        route_after_classification,
        {"ask_context": "ask_context", "plan": "plan", "output": "output"},
    )
    builder.add_edge("plan", "post_validate")
    builder.add_conditional_edges(
        "post_validate",
        route_after_post_validate,
        {"output": "output", "plan": "plan", "fallback": "fallback"},
    )
    builder.add_edge("output", END)
    builder.add_edge("fallback", END)

    return builder.compile()
