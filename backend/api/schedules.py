import json
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schedule_agent.graph import create_graph
from app.schedule_agent.schemas import StreamEvent
from backend.db.models import Schedule, Task
from backend.db.session import AsyncSessionLocal, get_session

router = APIRouter()
graph = create_graph()

STREAM_NODE_NAMES = {"pre_validate", "classification", "ask_context", "plan", "post_validate", "output", "fallback"}


# ── 요청/응답 모델 ──────────────────────────────────────────────

class CreateScheduleRequest(BaseModel):
    title: Optional[str] = None
    detail: str = ""
    location: str = ""
    start_time: str = ""
    end_time: str = ""
    detail_with_context: str = ""
    context_answer: str = ""
    question: str = ""
    question_source: Literal["", "classification", "pre_validate"] = ""
    classification_retry: int = 0
    pre_validation_retry: int = 0
    plan_retry: int = 0
    max_retry: int = 2


class UpdateScheduleRequest(BaseModel):
    title: Optional[str] = None
    detail: Optional[str] = None
    location: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    is_done: Optional[bool] = None
    title: Optional[str] = None
    description: Optional[str] = None
    estimated_minutes: Optional[int] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    estimated_minutes: int
    order_index: int
    is_done: bool


class ScheduleResponse(BaseModel):
    id: str
    title: str
    detail: str
    location: str
    start_time: Optional[str]
    end_time: Optional[str]
    status: str
    fallback_reason: str
    is_decomposable: bool
    created_at: str
    tasks: list[TaskResponse] = []


# ── 헬퍼 ───────────────────────────────────────────────────────

def parse_datetime(value: str) -> Optional[datetime]:
    if not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M")
        except ValueError:
            return None


async def get_overlapping_schedules(session: AsyncSession, start_time: str, end_time: str) -> list[dict]:
    """저장된 ok 상태 일정 중 시간이 겹치는 것만 반환한다."""
    start_at = parse_datetime(start_time)
    end_at = parse_datetime(end_time)
    if not start_at or not end_at:
        return []
    stmt = select(Schedule).where(
        Schedule.status == "ok",
        Schedule.start_time < end_at,
        Schedule.end_time > start_at,
    )
    results = await session.exec(stmt)
    return [
        {
            "title": s.title,
            "location": s.location,
            "start_time": s.start_time.isoformat() if s.start_time else "",
            "end_time": s.end_time.isoformat() if s.end_time else "",
        }
        for s in results.all()
    ]


def build_agent_state(req: CreateScheduleRequest, existing_schedules: list[dict]) -> dict:
    title = req.title or ""
    detail_with_context = req.detail_with_context or req.detail
    return {
        "title": title,
        "detail": req.detail,
        "detail_with_context": detail_with_context,
        "location": req.location,
        "context_answer": req.context_answer,
        "start_time": req.start_time,
        "end_time": req.end_time,
        "existing_schedules": existing_schedules,
        "classification_retry": req.classification_retry,
        "pre_validation_retry": req.pre_validation_retry,
        "plan_retry": req.plan_retry,
        "max_retry": req.max_retry,
        "is_decomposable": True,
        "needs_question": False,
        "question": req.question,
        "question_source": req.question_source,
        "is_valid": False,
        "invalid_reason": "",
        "normalized_schedule": {},
        "tasks": [],
        "plan_reason": "",
        "status": "fallback",
        "fallback_reason": "",
        "answer": "",
    }


async def save_result(result: dict, req: CreateScheduleRequest) -> Schedule:
    """에이전트 결과를 DB에 저장하고 Schedule 인스턴스를 반환한다."""
    async with AsyncSessionLocal() as session:
        schedule = Schedule(
            title=result.get("title") or req.title or "",
            detail=req.detail,
            location=result.get("location") or req.location,
            start_time=parse_datetime(req.start_time),
            end_time=parse_datetime(req.end_time),
            status=result.get("status", "fallback"),
            fallback_reason=result.get("fallback_reason", ""),
            is_decomposable=result.get("is_decomposable", True),
        )
        session.add(schedule)
        await session.flush()

        for t in result.get("tasks", []):
            session.add(Task(
                schedule_id=schedule.id,
                title=t.get("title", ""),
                description=t.get("description", ""),
                estimated_minutes=t.get("estimated_minutes", 30),
                order_index=t.get("order_index", 1),
            ))

        await session.commit()
        await session.refresh(schedule)
        return schedule


def to_schedule_response(schedule: Schedule, tasks: list[Task]) -> ScheduleResponse:
    return ScheduleResponse(
        id=str(schedule.id),
        title=schedule.title,
        detail=schedule.detail,
        location=schedule.location,
        start_time=schedule.start_time.isoformat() if schedule.start_time else None,
        end_time=schedule.end_time.isoformat() if schedule.end_time else None,
        status=schedule.status,
        fallback_reason=schedule.fallback_reason,
        is_decomposable=schedule.is_decomposable,
        created_at=schedule.created_at.isoformat(),
        tasks=[
            TaskResponse(
                id=str(t.id),
                title=t.title,
                description=t.description,
                estimated_minutes=t.estimated_minutes,
                order_index=t.order_index,
                is_done=t.is_done,
            )
            for t in sorted(tasks, key=lambda x: x.order_index)
        ],
    )


# ── 엔드포인트 ─────────────────────────────────────────────────

@router.post("/stream")
async def create_schedule_stream(req: CreateScheduleRequest):
    """일정 에이전트를 SSE 스트리밍으로 실행하고 결과를 DB에 저장한다."""
    async with AsyncSessionLocal() as session:
        existing = await get_overlapping_schedules(session, req.start_time, req.end_time)

    initial_state = build_agent_state(req, existing)

    async def gen():
        final_state: dict = {}
        async for mode, chunk in graph.astream(initial_state, stream_mode=["updates", "values"]):
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

        saved = await save_result(final_state, req)
        done_data = {
            "schedule_id": str(saved.id),
            "status": final_state.get("status", "fallback"),
            "tasks": final_state.get("tasks", []),
            "question": final_state.get("question", ""),
            "question_source": final_state.get("question_source", ""),
            "classification_retry": final_state.get("classification_retry", 0),
            "pre_validation_retry": final_state.get("pre_validation_retry", 0),
            "plan_retry": final_state.get("plan_retry", 0),
            "detail_with_context": final_state.get("detail_with_context", ""),
            "fallback_reason": final_state.get("fallback_reason", ""),
            "answer": final_state.get("answer", ""),
        }
        done = StreamEvent(event="done", data=json.dumps(done_data, ensure_ascii=False, default=str))
        yield f"data: {done.model_dump_json()}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(session: AsyncSession = Depends(get_session)):
    """저장된 일정 목록을 반환한다."""
    results = await session.exec(select(Schedule).order_by(Schedule.created_at.desc()))
    schedules = results.all()
    response = []
    for s in schedules:
        task_results = await session.exec(select(Task).where(Task.schedule_id == s.id))
        response.append(to_schedule_response(s, task_results.all()))
    return response


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: UUID, session: AsyncSession = Depends(get_session)):
    """일정 상세와 태스크 목록을 반환한다."""
    schedule = await session.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    task_results = await session.exec(select(Task).where(Task.schedule_id == schedule_id))
    return to_schedule_response(schedule, task_results.all())


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    req: UpdateScheduleRequest,
    session: AsyncSession = Depends(get_session),
):
    """일정 제목, 상세, 위치를 수정한다."""
    schedule = await session.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    if req.title is not None:
        schedule.title = req.title
    if req.detail is not None:
        schedule.detail = req.detail
    if req.location is not None:
        schedule.location = req.location
    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)
    task_results = await session.exec(select(Task).where(Task.schedule_id == schedule_id))
    return to_schedule_response(schedule, task_results.all())


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: UUID, session: AsyncSession = Depends(get_session)):
    """일정과 연결된 태스크를 모두 삭제한다."""
    schedule = await session.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    task_results = await session.exec(select(Task).where(Task.schedule_id == schedule_id))
    for task in task_results.all():
        await session.delete(task)
    await session.delete(schedule)
    await session.commit()


@router.patch("/{schedule_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    schedule_id: UUID,
    task_id: UUID,
    req: UpdateTaskRequest,
    session: AsyncSession = Depends(get_session),
):
    """태스크 완료 여부 및 내용을 수정한다."""
    task = await session.get(Task, task_id)
    if not task or task.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다.")
    if req.is_done is not None:
        task.is_done = req.is_done
    if req.title is not None:
        task.title = req.title
    if req.description is not None:
        task.description = req.description
    if req.estimated_minutes is not None:
        task.estimated_minutes = req.estimated_minutes
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return TaskResponse(
        id=str(task.id),
        title=task.title,
        description=task.description,
        estimated_minutes=task.estimated_minutes,
        order_index=task.order_index,
        is_done=task.is_done,
    )


@router.post("/{schedule_id}/stream")
async def regenerate_schedule_stream(schedule_id: UUID, session: AsyncSession = Depends(get_session)):
    """기존 일정의 태스크를 에이전트로 재생성하고 SSE로 스트리밍한다."""
    schedule = await session.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")

    existing = await get_overlapping_schedules(
        session,
        schedule.start_time.isoformat() if schedule.start_time else "",
        schedule.end_time.isoformat() if schedule.end_time else "",
    )
    req = CreateScheduleRequest(
        title=schedule.title,
        detail=schedule.detail,
        location=schedule.location,
        start_time=schedule.start_time.isoformat() if schedule.start_time else "",
        end_time=schedule.end_time.isoformat() if schedule.end_time else "",
    )
    initial_state = build_agent_state(req, existing)

    async def gen():
        final_state: dict = {}
        async for mode, chunk in graph.astream(initial_state, stream_mode=["updates", "values"]):
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

        # 기존 태스크 삭제 후 재저장
        async with AsyncSessionLocal() as write_session:
            old_tasks = await write_session.exec(select(Task).where(Task.schedule_id == schedule_id))
            for t in old_tasks.all():
                await write_session.delete(t)
            schedule_obj = await write_session.get(Schedule, schedule_id)
            schedule_obj.status = final_state.get("status", "fallback")
            schedule_obj.fallback_reason = final_state.get("fallback_reason", "")
            schedule_obj.is_decomposable = final_state.get("is_decomposable", True)
            write_session.add(schedule_obj)
            for t in final_state.get("tasks", []):
                write_session.add(Task(
                    schedule_id=schedule_id,
                    title=t.get("title", ""),
                    description=t.get("description", ""),
                    estimated_minutes=t.get("estimated_minutes", 30),
                    order_index=t.get("order_index", 1),
                ))
            await write_session.commit()

        done_data = {
            "schedule_id": str(schedule_id),
            "status": final_state.get("status", "fallback"),
            "tasks": final_state.get("tasks", []),
            "fallback_reason": final_state.get("fallback_reason", ""),
        }
        done = StreamEvent(event="done", data=json.dumps(done_data, ensure_ascii=False, default=str))
        yield f"data: {done.model_dump_json()}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
