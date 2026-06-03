from app.schedule_agent.schemas import AgentState


def build_output(state: AgentState) -> dict:
    """정상 task 생성 결과를 최종 응답으로 정리한다."""
    title = state.get("title", "")
    detail_with_context = state.get("detail_with_context") or state.get("detail", "")
    tasks = state.get("tasks", [])

    return {
        "status": "ok",
        "title": title,
        "detail_with_context": detail_with_context,
        "location": state.get("location", ""),
        "start_time": state.get("start_time", ""),
        "end_time": state.get("end_time", ""),
        "tasks": tasks,
        "answer": f"{title} 일정을 {len(tasks)}개의 하위 task로 분해했습니다.",
    }
