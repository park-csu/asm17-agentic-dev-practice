from langgraph.graph import END, START, StateGraph

from app.schedule_agent.nodes.ask_context import ask_context
from app.schedule_agent.nodes.classification import classify_schedule
from app.schedule_agent.nodes.fallback import build_fallback
from app.schedule_agent.nodes.output import build_output
from app.schedule_agent.nodes.plan import plan_tasks
from app.schedule_agent.nodes.post_validate import post_validate_tasks
from app.schedule_agent.nodes.pre_validate import pre_validate_schedule
from app.schedule_agent.schemas import AgentState


def route_after_classification(state: AgentState) -> str:
    """추가 질문 필요 여부에 따라 다음 노드를 결정한다."""
    retry = state.get("classification_retry", 0)
    max_retry = state.get("max_retry", 2)
    if state.get("needs_question", False) and retry < max_retry:
        return "ask_context"
    return "pre_validate"


def route_after_pre_validate(state: AgentState) -> str:
    """일정 유효성 검증 결과에 따라 계획 또는 실패로 이동한다."""
    return "plan" if state.get("is_valid", False) else "fallback"


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

    builder.add_node("classification", classify_schedule)
    builder.add_node("ask_context", ask_context)
    builder.add_node("pre_validate", pre_validate_schedule)
    builder.add_node("plan", plan_tasks)
    builder.add_node("post_validate", post_validate_tasks)
    builder.add_node("output", build_output)
    builder.add_node("fallback", build_fallback)

    builder.add_edge(START, "classification")
    builder.add_conditional_edges("classification", route_after_classification, {"ask_context": "ask_context", "pre_validate": "pre_validate"})
    builder.add_edge("ask_context", END)
    builder.add_conditional_edges("pre_validate", route_after_pre_validate, {"plan": "plan", "fallback": "fallback"})
    builder.add_edge("plan", "post_validate")
    builder.add_conditional_edges("post_validate", route_after_post_validate, {"output": "output", "plan": "plan", "fallback": "fallback"})
    builder.add_edge("output", END)
    builder.add_edge("fallback", END)

    return builder.compile()
