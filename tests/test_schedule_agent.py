import json
import unittest
from unittest.mock import patch

from app.api import create_schedule_tasks_stream
from app.schedule_agent.graph import (
    create_graph,
    route_after_classification,
    route_after_post_validate,
    route_after_pre_validate,
)
from app.schedule_agent.schemas import ScheduleTaskRequest


class ScheduleAgentGraphTest(unittest.TestCase):
    def test_route_after_classification_goes_to_ask_context(self):
        state = {"needs_question": True, "classification_retry": 0, "max_retry": 2}

        self.assertEqual(route_after_classification(state), "ask_context")

    def test_route_after_classification_goes_to_pre_validate_when_enough_context(self):
        state = {"needs_question": False, "classification_retry": 0, "max_retry": 2}

        self.assertEqual(route_after_classification(state), "pre_validate")

    def test_route_after_classification_stops_question_at_max_retry(self):
        state = {"needs_question": True, "classification_retry": 2, "max_retry": 2}

        self.assertEqual(route_after_classification(state), "pre_validate")

    def test_route_after_pre_validate(self):
        self.assertEqual(route_after_pre_validate({"is_valid": True}), "plan")
        self.assertEqual(route_after_pre_validate({"is_valid": False}), "fallback")

    def test_route_after_post_validate_retries_until_max_retry(self):
        retry_state = {"is_valid": False, "plan_retry": 1, "max_retry": 2}
        fallback_state = {"is_valid": False, "plan_retry": 2, "max_retry": 2}

        self.assertEqual(route_after_post_validate(retry_state), "plan")
        self.assertEqual(route_after_post_validate(fallback_state), "fallback")

    def test_graph_fallback_when_schedule_range_is_missing(self):
        graph = create_graph()
        result = graph.invoke(
            {
                "title": "발표 준비",
                "detail": "자료 조사와 발표자료 제작",
                "detail_with_context": "자료 조사와 발표자료 제작",
                "context_answer": "",
                "start_time": "",
                "end_time": "",
                "existing_schedules": [],
                "classification_retry": 2,
                "plan_retry": 0,
                "max_retry": 2,
                "needs_question": False,
                "question": "",
                "is_valid": False,
                "invalid_reason": "",
                "normalized_schedule": {},
                "tasks": [],
                "plan_reason": "",
                "status": "fallback",
                "fallback_reason": "",
                "answer": "",
            }
        )

        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["tasks"], [])
        self.assertIn("시간", result["fallback_reason"])


class ScheduleAgentStreamApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_stream_runs_graph_once_and_builds_done_from_last_value(self):
        class FakeGraph:
            def __init__(self):
                self.astream_calls = []
                self.ainvoke_called = False

            async def astream(self, state, stream_mode):
                self.astream_calls.append((state, stream_mode))
                yield "values", state
                yield "updates", {"classification": {"needs_question": False}}
                yield "updates", {"internal": {"ignored": True}}
                yield "updates", {"output": {"status": "ok", "answer": "완료"}}
                yield "values", {
                    **state,
                    "status": "ok",
                    "answer": "최종 응답",
                    "tasks": [{"title": "자료 조사"}],
                }

            async def ainvoke(self, state):
                self.ainvoke_called = True
                raise AssertionError("스트리밍 API에서 그래프를 다시 실행하면 안 됩니다.")

        fake_graph = FakeGraph()
        request = ScheduleTaskRequest(
            title="발표 준비",
            detail="자료 조사",
            start_time="2026-06-03T10:00:00+09:00",
            end_time="2026-06-03T12:00:00+09:00",
        )

        with patch("app.api.graph", fake_graph):
            response = await create_schedule_tasks_stream(request)
            body = "".join([chunk async for chunk in response.body_iterator])

        events = [
            json.loads(block.removeprefix("data: "))
            for block in body.strip().split("\n\n")
        ]
        done_data = json.loads(events[-1]["data"])

        self.assertEqual(len(fake_graph.astream_calls), 1)
        self.assertEqual(fake_graph.astream_calls[0][1], ["updates", "values"])
        self.assertFalse(fake_graph.ainvoke_called)
        self.assertEqual([event["node"] for event in events[:-1]], ["classification", "output"])
        self.assertEqual(events[-1]["event"], "done")
        self.assertEqual(done_data["status"], "ok")
        self.assertEqual(done_data["answer"], "최종 응답")
        self.assertEqual(done_data["tasks"], [{"title": "자료 조사"}])


if __name__ == "__main__":
    unittest.main()
