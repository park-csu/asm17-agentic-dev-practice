import json
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import delete
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from backend.core.auth import get_current_user_id
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schedule_agent.graph import create_graph
from app.schedule_agent.schemas import StreamEvent
from backend.db.models import Schedule, Task, User
from backend.db.session import AsyncSessionLocal, get_session

router = APIRouter(tags=["schedules"])
graph = create_graph()

STREAM_NODE_NAMES = {"pre_validate", "classification", "ask_context", "plan", "post_validate", "output", "fallback"}


# ── 요청/응답 모델 ──────────────────────────────────────────────

class CreateScheduleRequest(BaseModel):
    model_config = {"json_schema_extra": {
        "examples": [{
            "title": "기말 발표 준비",
            "detail": "딥러닝 논문 리뷰 발표를 위해 논문 정리하고 슬라이드 10장 만들기",
            "location": "서울특별시",
            "start_time": "2026-06-10T10:00:00",
            "end_time": "2026-06-10T12:00:00",
            "max_retry": 2,
        }]
    }}

    title: Optional[str] = Field(default=None, description="일정 제목")
    detail: str = Field(default="", description="일정 상세 내용")
    location: str = Field(default="", description="일정 장소")
    start_time: str = Field(default="", description="시작 시간 (ISO 8601)")
    end_time: str = Field(default="", description="종료 시간 (ISO 8601)")
    detail_with_context: str = Field(default="", description="누적된 일정 상세 컨텍스트 (재요청 시 이전 응답값 그대로 전달)")
    context_answer: str = Field(default="", description="추가 질문에 대한 사용자 답변")
    question: str = Field(default="", description="이전 응답에서 받은 질문 (재요청 시 그대로 전달)")
    question_source: Literal["", "classification", "pre_validate"] = Field(default="", description="질문 출처")
    classification_retry: int = Field(default=0, description="분류 재시도 횟수 (이전 응답값 그대로 전달)")
    pre_validation_retry: int = Field(default=0, description="사전 검증 재시도 횟수 (이전 응답값 그대로 전달)")
    plan_retry: int = Field(default=0, description="계획 재시도 횟수 (이전 응답값 그대로 전달)")
    max_retry: int = Field(default=2, description="노드별 최대 재시도 횟수")


class UpdateScheduleRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"title": "수정된 발표 제목", "location": "부산광역시"}]}}

    title: Optional[str] = Field(default=None, description="변경할 제목")
    detail: Optional[str] = Field(default=None, description="변경할 상세 내용")
    location: Optional[str] = Field(default=None, description="변경할 장소")


class UpdateTaskRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"is_done": True}]}}

    is_done: Optional[bool] = Field(default=None, description="완료 여부")
    title: Optional[str] = Field(default=None, description="변경할 태스크 제목")
    description: Optional[str] = Field(default=None, description="변경할 태스크 설명")
    estimated_minutes: Optional[int] = Field(default=None, description="변경할 예상 소요 시간(분)")


class RegenerateScheduleRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"max_retry": 0}]}}

    context_answer: str = Field(default="", description="추가 질문에 대한 사용자 답변")
    question: str = Field(default="", description="이전 응답에서 받은 질문")
    question_source: Literal["", "classification", "pre_validate"] = Field(default="", description="질문 출처")
    classification_retry: int = Field(default=0, description="분류 재시도 횟수")
    pre_validation_retry: int = Field(default=0, description="사전 검증 재시도 횟수")
    plan_retry: int = Field(default=0, description="계획 재시도 횟수")
    max_retry: int = Field(default=2, description="노드별 최대 재시도 횟수")
    detail_with_context: str = Field(default="", description="누적된 일정 상세 컨텍스트")


class TaskResponse(BaseModel):
    id: str = Field(description="태스크 UUID")
    title: str = Field(description="태스크 제목")
    description: str = Field(description="태스크 설명")
    estimated_minutes: int = Field(description="예상 소요 시간(분)")
    order_index: int = Field(description="실행 순서")
    is_done: bool = Field(description="완료 여부")


class ScheduleResponse(BaseModel):
    id: str = Field(description="일정 UUID")
    title: str = Field(description="일정 제목")
    detail: str = Field(description="일정 상세 내용")
    location: str = Field(description="일정 장소")
    start_time: Optional[str] = Field(description="시작 시간 (ISO 8601)")
    end_time: Optional[str] = Field(description="종료 시간 (ISO 8601)")
    status: str = Field(description="에이전트 처리 결과 (ok / needs_question / fallback)")
    fallback_reason: str = Field(description="실패 이유 (status가 fallback일 때)")
    is_decomposable: bool = Field(description="서브태스크 분해 필요 여부")
    created_at: str = Field(description="생성 시각 (ISO 8601)")
    tasks: list[TaskResponse] = Field(default=[], description="생성된 서브태스크 목록")


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


async def get_overlapping_schedules(
    session: AsyncSession,
    start_time: str,
    end_time: str,
    exclude_schedule_id: UUID | None = None,
    user_id: UUID | None = None,
) -> list[dict]:
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
    if user_id is not None:
        stmt = stmt.where(Schedule.user_id == user_id)
    if exclude_schedule_id is not None:
        stmt = stmt.where(Schedule.id != exclude_schedule_id)
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


async def ensure_user_exists(session: AsyncSession, user_id: UUID) -> None:
    user = await session.get(User, user_id)
    if user:
        return

    session.add(User(
        id=user_id,
        email=f"{user_id}@taskpilot.local",
        name="",
    ))
    await session.commit()


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


async def save_result(result: dict, req: CreateScheduleRequest, user_id: Optional[UUID] = None) -> Schedule:
    """에이전트 결과를 DB에 저장하고 Schedule 인스턴스를 반환한다."""
    async with AsyncSessionLocal() as session:
        schedule = Schedule(
            user_id=user_id,
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

_STREAM_RESPONSE_DESC = """
**Content-Type:** `text/event-stream`

각 줄은 `data: <JSON>\\n\\n` 형식입니다.

### node 이벤트
에이전트 노드 실행마다 전송됩니다.

```
data: {"event": "node", "node": "pre_validate", "data": "{...}"}
data: {"event": "node", "node": "classification", "data": "{...}"}
data: {"event": "node", "node": "plan", "data": "{...}"}
data: {"event": "node", "node": "post_validate", "data": "{...}"}
data: {"event": "node", "node": "output", "data": "{...}"}
```

노드별 `data` 필드 (JSON 문자열):

| node | 주요 필드 |
|------|----------|
| `pre_validate` | `is_valid`, `needs_question`, `question`, `invalid_reason` |
| `classification` | `is_decomposable`, `needs_question`, `question`, `question_source` |
| `ask_context` | `detail_with_context`, `status`, `classification_retry` |
| `plan` | `tasks[]{title, estimated_minutes, order_index}` |
| `post_validate` | `is_valid`, `tasks[]` |
| `output` | `status: "ok"`, `tasks[]`, `answer` |
| `fallback` | `status: "fallback"`, `fallback_reason` |

### done 이벤트
스트리밍 완료 후 DB 저장이 끝나면 전송됩니다.

```
data: {"event": "done", "node": "", "data": "{...}"}
```

`data` 필드:

| 필드 | 타입 | 설명 |
|------|------|------|
| `schedule_id` | string | 저장된 일정 UUID |
| `status` | string | `ok` / `needs_question` / `fallback` |
| `tasks` | array | 생성된 서브태스크 목록 |
| `question` | string | 추가 질문 (needs_question일 때) |
| `question_source` | string | `classification` / `pre_validate` |
| `classification_retry` | int | 분류 재시도 횟수 |
| `pre_validation_retry` | int | 사전 검증 재시도 횟수 |
| `plan_retry` | int | 계획 재시도 횟수 |
| `detail_with_context` | string | 누적 컨텍스트 |
| `fallback_reason` | string | 실패 이유 |
"""


@router.post(
    "/stream",
    summary="일정 생성 및 에이전트 실행 (SSE)",
    description=f"""
일정을 생성하고 LangGraph 에이전트를 SSE 스트리밍으로 실행합니다.

에이전트가 추가 정보가 필요하면 `done` 이벤트에서 `status: needs_question`과 `question`을 반환합니다.
이 경우 사용자 답변을 `context_answer`에 담아 동일 엔드포인트를 재호출하면 에이전트가 이어서 실행됩니다.

재요청 시 `done` 이벤트에서 받은 `question`, `question_source`, retry 값, `detail_with_context`를 그대로 포함해야 합니다.

{_STREAM_RESPONSE_DESC}
""",
    responses={200: {"description": "SSE 스트림", "content": {"text/event-stream": {}}}},
)
async def create_schedule_stream(
    req: CreateScheduleRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    async with AsyncSessionLocal() as session:
        await ensure_user_exists(session, user_id)
        existing = await get_overlapping_schedules(session, req.start_time, req.end_time, user_id=user_id)

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

        saved = await save_result(final_state, req, user_id)
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


@router.get(
    "",
    response_model=list[ScheduleResponse],
    summary="일정 목록 조회",
    description="저장된 모든 일정을 최신순으로 반환합니다. 각 일정에 서브태스크 목록이 포함됩니다.",
)
async def list_schedules(
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
):
    results = await session.exec(
        select(Schedule)
        .where(Schedule.user_id == user_id)
        .order_by(Schedule.created_at.desc())
    )
    schedules = results.all()
    response = []
    for s in schedules:
        task_results = await session.exec(select(Task).where(Task.schedule_id == s.id))
        response.append(to_schedule_response(s, task_results.all()))
    return response


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="일정 상세 조회",
    description="일정 UUID로 상세 정보와 서브태스크 목록을 반환합니다.",
    responses={404: {"description": "일정을 찾을 수 없음"}},
)
async def get_schedule(
    schedule_id: UUID,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
):
    schedule = await session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != user_id:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    task_results = await session.exec(select(Task).where(Task.schedule_id == schedule_id))
    return to_schedule_response(schedule, task_results.all())


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="일정 수정",
    description="일정의 제목, 상세 내용, 장소를 수정합니다. 변경할 필드만 포함하면 됩니다.",
    responses={404: {"description": "일정을 찾을 수 없음"}},
)
async def update_schedule(
    schedule_id: UUID,
    req: UpdateScheduleRequest,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
):
    schedule = await session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != user_id:
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


@router.delete(
    "/{schedule_id}",
    status_code=204,
    summary="일정 삭제",
    description="일정과 연결된 모든 서브태스크를 삭제합니다.",
    responses={404: {"description": "일정을 찾을 수 없음"}},
)
async def delete_schedule(
    schedule_id: UUID,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
):
    schedule = await session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != user_id:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    await session.exec(delete(Task).where(Task.schedule_id == schedule_id))
    await session.flush()
    await session.delete(schedule)
    await session.commit()


@router.patch(
    "/{schedule_id}/tasks/{task_id}",
    response_model=TaskResponse,
    summary="태스크 수정",
    description="태스크의 완료 여부, 제목, 설명, 예상 시간을 수정합니다. 변경할 필드만 포함하면 됩니다.",
    responses={404: {"description": "태스크를 찾을 수 없음"}},
)
async def update_task(
    schedule_id: UUID,
    task_id: UUID,
    req: UpdateTaskRequest,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
):
    schedule = await session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != user_id:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
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


@router.delete(
    "/{schedule_id}/tasks/{task_id}",
    status_code=204,
    summary="태스크 삭제",
    description="특정 서브태스크를 삭제합니다.",
    responses={404: {"description": "태스크를 찾을 수 없음"}},
)
async def delete_task(
    schedule_id: UUID,
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
):
    schedule = await session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != user_id:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    task = await session.get(Task, task_id)
    if not task or task.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다.")
    await session.delete(task)
    await session.commit()


@router.post(
    "/{schedule_id}/stream",
    summary="태스크 재생성 (SSE)",
    description=f"""
기존 일정의 서브태스크를 에이전트로 재생성합니다. 기존 태스크는 삭제되고 새로 생성된 태스크로 교체됩니다.

에이전트가 추가 질문을 반환한 경우, `context_answer`와 이전 응답의 retry/question 값을 담아 재호출하면 이어서 실행됩니다.

{_STREAM_RESPONSE_DESC}
""",
    responses={
        200: {"description": "SSE 스트림", "content": {"text/event-stream": {}}},
        404: {"description": "일정을 찾을 수 없음"},
    },
)
async def regenerate_schedule_stream(
    schedule_id: UUID,
    req: RegenerateScheduleRequest = RegenerateScheduleRequest(),
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
):
    schedule = await session.get(Schedule, schedule_id)
    if not schedule or schedule.user_id != user_id:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")

    existing = await get_overlapping_schedules(
        session,
        schedule.start_time.isoformat() if schedule.start_time else "",
        schedule.end_time.isoformat() if schedule.end_time else "",
        exclude_schedule_id=schedule_id,
        user_id=user_id,
    )
    create_req = CreateScheduleRequest(
        title=schedule.title,
        detail=schedule.detail,
        detail_with_context=req.detail_with_context or schedule.detail,
        location=schedule.location,
        start_time=schedule.start_time.isoformat() if schedule.start_time else "",
        end_time=schedule.end_time.isoformat() if schedule.end_time else "",
        context_answer=req.context_answer,
        question=req.question,
        question_source=req.question_source,
        classification_retry=req.classification_retry,
        pre_validation_retry=req.pre_validation_retry,
        plan_retry=req.plan_retry,
        max_retry=req.max_retry,
    )
    initial_state = build_agent_state(create_req, existing)

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
            "question": final_state.get("question", ""),
            "question_source": final_state.get("question_source", ""),
            "classification_retry": final_state.get("classification_retry", 0),
            "pre_validation_retry": final_state.get("pre_validation_retry", 0),
            "plan_retry": final_state.get("plan_retry", 0),
            "detail_with_context": final_state.get("detail_with_context", ""),
            "fallback_reason": final_state.get("fallback_reason", ""),
        }
        done = StreamEvent(event="done", data=json.dumps(done_data, ensure_ascii=False, default=str))
        yield f"data: {done.model_dump_json()}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
