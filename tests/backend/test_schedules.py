from datetime import datetime
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.schedules import ensure_user_exists, get_validation_context_schedules
from backend.db.models import Task, User
from tests.backend.factories import ScheduleFactory, TaskFactory


async def ensure_test_user(db_session: AsyncSession, user_id: UUID):
    user = await db_session.get(User, user_id)
    if user:
        return user
    user = User(id=user_id, email=f"{user_id}@test.local", name="테스트 사용자")
    db_session.add(user)
    await db_session.commit()
    return user


async def create_schedule(db_session: AsyncSession, **kwargs):
    schedule = ScheduleFactory.build(**kwargs)
    if schedule.user_id:
        await ensure_test_user(db_session, schedule.user_id)
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


async def create_task(db_session: AsyncSession, schedule_id, **kwargs):
    task = TaskFactory.build(schedule_id=schedule_id, **kwargs)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


# ── GET /schedules ──────────────────────────────────────────────

async def test_list_schedules_empty(client: AsyncClient):
    res = await client.get("/api/v1/schedules")
    assert res.status_code == 200
    assert res.json() == []


async def test_list_schedules_returns_all(client: AsyncClient, db_session: AsyncSession):
    await create_schedule(db_session, title="발표 준비")
    await create_schedule(db_session, title="회의")

    res = await client.get("/api/v1/schedules")
    assert res.status_code == 200
    assert len(res.json()) == 2
    titles = {s["title"] for s in res.json()}
    assert titles == {"발표 준비", "회의"}


# ── GET /schedules/{id} ─────────────────────────────────────────

async def test_get_schedule_with_tasks(client: AsyncClient, db_session: AsyncSession):
    schedule = await create_schedule(db_session, title="기말 발표 준비")
    await create_task(db_session, schedule.id, title="목차 작성", order_index=1)
    await create_task(db_session, schedule.id, title="슬라이드 제작", order_index=2)

    res = await client.get(f"/api/v1/schedules/{schedule.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "기말 발표 준비"
    assert len(data["tasks"]) == 2
    assert data["tasks"][0]["title"] == "목차 작성"
    assert data["tasks"][1]["title"] == "슬라이드 제작"


async def test_get_schedule_not_found(client: AsyncClient):
    from uuid import uuid4
    res = await client.get(f"/api/v1/schedules/{uuid4()}")
    assert res.status_code == 404


# ── PATCH /schedules/{id} ───────────────────────────────────────

async def test_update_schedule_title(client: AsyncClient, db_session: AsyncSession):
    schedule = await create_schedule(db_session, title="원래 제목")

    res = await client.patch(f"/api/v1/schedules/{schedule.id}", json={"title": "바뀐 제목"})
    assert res.status_code == 200
    assert res.json()["title"] == "바뀐 제목"


async def test_update_schedule_partial(client: AsyncClient, db_session: AsyncSession):
    schedule = await create_schedule(db_session, title="발표", location="서울")

    res = await client.patch(f"/api/v1/schedules/{schedule.id}", json={"location": "부산"})
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "발표"
    assert data["location"] == "부산"


async def test_update_schedule_not_found(client: AsyncClient):
    from uuid import uuid4
    res = await client.patch(f"/api/v1/schedules/{uuid4()}", json={"title": "없음"})
    assert res.status_code == 404


# ── DELETE /schedules/{id} ──────────────────────────────────────

async def test_delete_schedule(client: AsyncClient, db_session: AsyncSession):
    schedule = await create_schedule(db_session)
    await create_task(db_session, schedule.id)

    res = await client.delete(f"/api/v1/schedules/{schedule.id}")
    assert res.status_code == 204

    res = await client.get(f"/api/v1/schedules/{schedule.id}")
    assert res.status_code == 404
    task_results = await db_session.exec(select(Task).where(Task.schedule_id == schedule.id))
    assert task_results.all() == []


async def test_delete_schedule_not_found(client: AsyncClient):
    from uuid import uuid4
    res = await client.delete(f"/api/v1/schedules/{uuid4()}")
    assert res.status_code == 404


# ── PATCH /schedules/{id}/tasks/{task_id} ──────────────────────

async def test_update_task_is_done(client: AsyncClient, db_session: AsyncSession):
    schedule = await create_schedule(db_session)
    task = await create_task(db_session, schedule.id, is_done=False)

    res = await client.patch(
        f"/api/v1/schedules/{schedule.id}/tasks/{task.id}",
        json={"is_done": True},
    )
    assert res.status_code == 200
    assert res.json()["is_done"] is True


async def test_update_task_title(client: AsyncClient, db_session: AsyncSession):
    schedule = await create_schedule(db_session)
    task = await create_task(db_session, schedule.id, title="원래 태스크")

    res = await client.patch(
        f"/api/v1/schedules/{schedule.id}/tasks/{task.id}",
        json={"title": "수정된 태스크"},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "수정된 태스크"


async def test_update_task_not_found(client: AsyncClient, db_session: AsyncSession):
    from uuid import uuid4
    schedule = await create_schedule(db_session)
    res = await client.patch(
        f"/api/v1/schedules/{schedule.id}/tasks/{uuid4()}",
        json={"is_done": True},
    )
    assert res.status_code == 404


async def test_update_task_wrong_schedule(client: AsyncClient, db_session: AsyncSession):
    schedule_a = await create_schedule(db_session)
    schedule_b = await create_schedule(db_session)
    task = await create_task(db_session, schedule_a.id)

    res = await client.patch(
        f"/api/v1/schedules/{schedule_b.id}/tasks/{task.id}",
        json={"is_done": True},
    )
    assert res.status_code == 404


# ── existing_schedules 주입 ─────────────────────────────────────

async def test_get_validation_context_schedules_can_exclude_current_schedule(db_session: AsyncSession):
    current = await create_schedule(db_session, title="재생성 대상 일정")
    other = await create_schedule(db_session, title="겹치는 다른 일정")

    existing = await get_validation_context_schedules(
        db_session,
        current.start_time.isoformat(),
        current.end_time.isoformat(),
        exclude_schedule_id=current.id,
    )

    titles = {schedule["title"] for schedule in existing}
    assert "재생성 대상 일정" not in titles
    assert titles == {other.title}


async def test_get_validation_context_schedules_includes_nearby_non_overlapping_schedule(db_session: AsyncSession):
    await create_schedule(
        db_session,
        title="서울 팀 회의",
        location="서울특별시",
        start_time=datetime(2026, 6, 15, 9, 0),
        end_time=datetime(2026, 6, 15, 10, 0),
    )

    existing = await get_validation_context_schedules(
        db_session,
        "2026-06-15T11:00:00",
        "2026-06-15T12:00:00",
    )

    assert [schedule["title"] for schedule in existing] == ["서울 팀 회의"]
    assert existing[0]["location"] == "서울특별시"


async def test_get_validation_context_schedules_excludes_far_schedule(db_session: AsyncSession):
    await create_schedule(
        db_session,
        title="전날 저녁 회의",
        start_time=datetime(2026, 6, 14, 18, 0),
        end_time=datetime(2026, 6, 14, 19, 0),
    )

    existing = await get_validation_context_schedules(
        db_session,
        "2026-06-15T11:00:00",
        "2026-06-15T12:00:00",
    )

    assert existing == []


async def test_get_validation_context_schedules_filters_by_user_id(db_session: AsyncSession):
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    other_user_id = UUID("00000000-0000-0000-0000-000000000002")
    await create_schedule(db_session, title="내 일정", user_id=user_id)
    await create_schedule(db_session, title="다른 사용자 일정", user_id=other_user_id)

    existing = await get_validation_context_schedules(
        db_session,
        "2026-06-10T10:30:00",
        "2026-06-10T11:30:00",
        user_id=user_id,
    )

    titles = {schedule["title"] for schedule in existing}
    assert titles == {"내 일정"}


# ── 인증 사용자 보장 ───────────────────────────────────────────

async def test_ensure_user_exists_creates_missing_user(db_session: AsyncSession):
    user_id = UUID("00000000-0000-0000-0000-000000000123")

    await ensure_user_exists(db_session, user_id)

    result = await db_session.exec(select(User).where(User.id == user_id))
    user = result.one()
    assert user.email == f"{user_id}@taskpilot.local"


async def test_ensure_user_exists_keeps_existing_user(db_session: AsyncSession):
    user_id = UUID("00000000-0000-0000-0000-000000000124")
    db_session.add(User(id=user_id, email="user@example.com", name="사용자"))
    await db_session.commit()

    await ensure_user_exists(db_session, user_id)

    result = await db_session.exec(select(User).where(User.id == user_id))
    user = result.one()
    assert user.email == "user@example.com"
