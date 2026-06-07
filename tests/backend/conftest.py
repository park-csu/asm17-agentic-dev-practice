from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.core.auth import get_current_user_id
from backend.db.models import Schedule, Task, User  # noqa: F401 — 테이블 메타데이터 등록
from backend.db.session import get_session
from backend.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})

    @event.listens_for(engine.sync_engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_session():
        yield db_session

    async def override_user_id():
        return TEST_USER_ID

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user_id] = override_user_id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
