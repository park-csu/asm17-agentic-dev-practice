from datetime import datetime
from uuid import UUID, uuid4

import factory

from backend.db.models import Schedule, Task, User

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.LazyFunction(uuid4)
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    name = factory.Sequence(lambda n: f"테스트유저{n}")
    created_at = factory.LazyFunction(datetime.utcnow)


class ScheduleFactory(factory.Factory):
    class Meta:
        model = Schedule

    id = factory.LazyFunction(uuid4)
    user_id = TEST_USER_ID
    title = factory.Sequence(lambda n: f"테스트 일정 {n}")
    detail = "테스트 상세 내용"
    location = "서울특별시"
    start_time = datetime(2026, 6, 10, 10, 0)
    end_time = datetime(2026, 6, 10, 12, 0)
    status = "ok"
    fallback_reason = ""
    is_decomposable = True
    created_at = factory.LazyFunction(datetime.utcnow)


class TaskFactory(factory.Factory):
    class Meta:
        model = Task

    id = factory.LazyFunction(uuid4)
    schedule_id = factory.LazyFunction(uuid4)
    title = factory.Sequence(lambda n: f"태스크 {n}")
    description = "태스크 설명"
    estimated_minutes = 30
    order_index = factory.Sequence(lambda n: n + 1)
    is_done = False
