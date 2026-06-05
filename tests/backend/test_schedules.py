import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from tests.backend.factories import ScheduleFactory, TaskFactory


async def create_schedule(db_session: AsyncSession, **kwargs):
    schedule = ScheduleFactory.build(**kwargs)
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
