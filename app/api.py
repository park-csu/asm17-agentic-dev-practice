import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schedule_agent.graph import create_graph
from app.schedule_agent.schemas import ScheduleTaskRequest, ScheduleTaskResponse, StreamEvent

router = APIRouter()
graph = create_graph()
STREAM_NODE_NAMES = {
    "classification",
    "ask_context",
    "pre_validate",
    "plan",
    "post_validate",
    "output",
    "fallback",
}


def build_initial_state(request: ScheduleTaskRequest) -> dict:
    """요청 본문으로부터 일정 에이전트 초기 상태를 생성한다."""
    title = request.title or ""
    detail = request.detail
    detail_with_context = request.detail_with_context or detail

    return {
        "title": title,
        "detail": detail,
        "detail_with_context": detail_with_context,
        "location": request.location,
        "context_answer": request.context_answer,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "existing_schedules": request.existing_schedules,
        "classification_retry": request.classification_retry,
        "pre_validation_retry": request.pre_validation_retry,
        "plan_retry": request.plan_retry,
        "max_retry": request.max_retry,
        "needs_question": False,
        "question": "",
        "question_source": request.question_source,
        "pre_validation_question": request.pre_validation_question,
        "is_valid": False,
        "invalid_reason": "",
        "normalized_schedule": {},
        "tasks": [],
        "plan_reason": "",
        "status": "fallback",
        "fallback_reason": "",
        "answer": "",
    }


def build_response(result: dict) -> ScheduleTaskResponse:
    """그래프 최종 상태를 API 응답 모델로 변환한다."""
    return ScheduleTaskResponse(
        status=result.get("status", "fallback"),
        title=result.get("title", ""),
        detail_with_context=result.get("detail_with_context", ""),
        location=result.get("location", ""),
        start_time=result.get("start_time", ""),
        end_time=result.get("end_time", ""),
        normalized_schedule=result.get("normalized_schedule", {}),
        tasks=result.get("tasks", []),
        question=result.get("question", ""),
        classification_retry=result.get("classification_retry", 0),
        pre_validation_retry=result.get("pre_validation_retry", 0),
        plan_retry=result.get("plan_retry", 0),
        question_source=result.get("question_source", ""),
        pre_validation_question=result.get("pre_validation_question", ""),
        fallback_reason=result.get("fallback_reason", ""),
        answer=result.get("answer", ""),
    )


@router.post("/schedules/tasks/sync", response_model=ScheduleTaskResponse)
async def create_schedule_tasks_sync(request: ScheduleTaskRequest):
    """일정 에이전트를 동기 방식으로 실행하고 최종 상태를 반환한다."""
    result = await graph.ainvoke(build_initial_state(request))
    return build_response(result)


@router.post("/schedules/tasks/stream")
async def create_schedule_tasks_stream(request: ScheduleTaskRequest):
    """SSE 스트리밍으로 각 노드의 처리 과정을 실시간 전송한다."""

    async def gen():
        final_state: dict = {}
        async for mode, chunk in graph.astream(
            build_initial_state(request),
            stream_mode=["updates", "values"],
        ):
            if mode == "updates":
                for node_name, node_output in chunk.items():
                    if node_name not in STREAM_NODE_NAMES:
                        continue
                    sse = StreamEvent(
                        event="node",
                        node=node_name,
                        data=json.dumps(node_output, ensure_ascii=False, default=str),
                    )
                    yield f"data: {sse.model_dump_json()}\n\n"
            elif mode == "values":
                final_state = chunk

        done = StreamEvent(
            event="done",
            data=build_response(final_state).model_dump_json(),
        )
        yield f"data: {done.model_dump_json()}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
