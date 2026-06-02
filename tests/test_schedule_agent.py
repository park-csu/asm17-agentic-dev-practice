import unittest

from app.schedule_agent.graph import (
    create_graph,
    route_after_classification,
    route_after_post_validate,
    route_after_pre_validate,
)


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


if __name__ == "__main__":
    unittest.main()
