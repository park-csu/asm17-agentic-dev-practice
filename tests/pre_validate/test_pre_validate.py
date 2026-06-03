import unittest
from unittest.mock import MagicMock, patch

from app.api import build_initial_state, build_response
from app.schedule_agent.nodes.pre_validate import pre_validate_schedule
from app.schedule_agent.schemas import PreValidationResult, ScheduleTaskRequest


class FakeStructuredLlm:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def invoke(self, messages):
        if self.error:
            raise self.error
        return self.result


class FakeLlm:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def with_structured_output(self, schema):
        if schema is not PreValidationResult:
            raise AssertionError("PreValidationResult 구조화 출력을 사용해야 합니다.")
        return FakeStructuredLlm(result=self.result, error=self.error)


class PreValidateScheduleTest(unittest.TestCase):
    def test_api_state_and_response_preserve_location(self):
        request = ScheduleTaskRequest(
            title="부산 고객 미팅",
            detail="고객 요구사항을 확인한다.",
            location="부산광역시",
        )

        state = build_initial_state(request)
        response = build_response({**state, "status": "fallback"})

        self.assertEqual(state["location"], "부산광역시")
        self.assertEqual(response.location, "부산광역시")

    def test_rejects_when_title_and_detail_are_empty(self):
        result = pre_validate_schedule(
            {
                "title": "",
                "detail": "",
                "detail_with_context": "",
                "start_time": "2026-06-10T10:00:00+09:00",
                "end_time": "2026-06-10T11:00:00+09:00",
            }
        )

        self.assertFalse(result["is_valid"])
        self.assertEqual(result["normalized_schedule"], {})
        self.assertIn("제목", result["invalid_reason"])

    def test_rejects_when_schedule_range_is_missing(self):
        result = pre_validate_schedule(
            {
                "title": "발표 준비",
                "detail_with_context": "발표 자료를 준비한다.",
                "start_time": "",
                "end_time": "",
            }
        )

        self.assertFalse(result["is_valid"])
        self.assertEqual(result["normalized_schedule"], {})
        self.assertIn("시간", result["invalid_reason"])

    def test_returns_structured_llm_result(self):
        expected = PreValidationResult(
            is_valid=True,
            normalized_schedule={
                "title": "발표 준비",
                "detail": "발표 자료를 준비한다.",
                "start_time": "2026-06-10T10:00:00+09:00",
                "end_time": "2026-06-10T11:00:00+09:00",
                "duration_minutes": 60,
            },
            invalid_reason="",
        )
        state = {
            "title": "발표 준비",
            "detail_with_context": "발표 자료를 준비한다.",
            "start_time": "2026-06-10T10:00:00+09:00",
            "end_time": "2026-06-10T11:00:00+09:00",
            "existing_schedules": [],
        }

        with patch(
            "app.schedule_agent.nodes.pre_validate.get_llm",
            return_value=FakeLlm(result=expected),
        ):
            result = pre_validate_schedule(state)

        self.assertEqual(result, expected.model_dump())

    def test_rejects_when_start_time_is_not_before_end_time(self):
        for start_time, end_time in [
            ("2026-06-10T17:00:00+09:00", "2026-06-10T16:00:00+09:00"),
            ("2026-06-10T15:00:00+09:00", "2026-06-10T15:00:00+09:00"),
        ]:
            with self.subTest(start_time=start_time, end_time=end_time):
                result = pre_validate_schedule(
                    {
                        "title": "보고서 작성",
                        "detail_with_context": "주간 성과 보고서를 작성한다.",
                        "start_time": start_time,
                        "end_time": end_time,
                        "existing_schedules": [],
                    }
                )

                self.assertFalse(result["is_valid"])
                self.assertEqual(result["normalized_schedule"], {})
                self.assertIn("시작 시간", result["invalid_reason"])

    def test_rejects_when_existing_schedule_overlaps(self):
        result = pre_validate_schedule(
            {
                "title": "면접 준비",
                "detail_with_context": "기술 면접 질문을 정리한다.",
                "start_time": "2026-06-12T10:30:00+09:00",
                "end_time": "2026-06-12T11:30:00+09:00",
                "existing_schedules": [
                    {
                        "title": "팀 회의",
                        "start_time": "2026-06-12T10:00:00+09:00",
                        "end_time": "2026-06-12T11:00:00+09:00",
                    }
                ],
            }
        )

        self.assertFalse(result["is_valid"])
        self.assertEqual(result["normalized_schedule"], {})
        self.assertIn("겹", result["invalid_reason"])
        self.assertIn("팀 회의", result["invalid_reason"])

    def test_allows_boundary_touching_schedule_to_reach_llm(self):
        expected = PreValidationResult(
            is_valid=True,
            normalized_schedule={"title": "코드 리뷰"},
            invalid_reason="",
        )
        state = {
            "title": "코드 리뷰",
            "detail_with_context": "결제 API 변경 사항을 검토한다.",
            "start_time": "2026-06-12T11:00:00+09:00",
            "end_time": "2026-06-12T12:00:00+09:00",
            "existing_schedules": [
                {
                    "title": "팀 회의",
                    "start_time": "2026-06-12T10:00:00+09:00",
                    "end_time": "2026-06-12T11:00:00+09:00",
                }
            ],
        }

        with patch(
            "app.schedule_agent.nodes.pre_validate.get_llm",
            return_value=FakeLlm(result=expected),
        ):
            result = pre_validate_schedule(state)

        self.assertTrue(result["is_valid"])

    def test_adds_reason_when_llm_returns_invalid_without_reason(self):
        expected = PreValidationResult(
            is_valid=False,
            normalized_schedule={},
            invalid_reason="",
        )
        state = {
            "title": "자료 조사",
            "detail_with_context": "시장 동향 자료를 조사한다.",
            "start_time": "나중에",
            "end_time": "적당히 끝날 때",
            "existing_schedules": [],
        }

        with patch(
            "app.schedule_agent.nodes.pre_validate.get_llm",
            return_value=FakeLlm(result=expected),
        ):
            result = pre_validate_schedule(state)

        self.assertFalse(result["is_valid"])
        self.assertTrue(result["invalid_reason"])

    def test_passes_location_to_llm_for_travel_feasibility_check(self):
        expected = PreValidationResult(
            is_valid=False,
            normalized_schedule={},
            invalid_reason="서울에서 부산으로 한 시간 안에 이동하기 어렵습니다.",
        )
        structured_llm = MagicMock()
        structured_llm.invoke.return_value = expected
        llm = MagicMock()
        llm.with_structured_output.return_value = structured_llm
        state = {
            "title": "부산 고객 미팅",
            "detail_with_context": "부산 고객사에서 대면으로 요구사항을 확인한다.",
            "location": "부산광역시",
            "start_time": "2026-06-15T11:00:00+09:00",
            "end_time": "2026-06-15T12:00:00+09:00",
            "existing_schedules": [
                {
                    "title": "서울 팀 회의",
                    "location": "서울특별시",
                    "start_time": "2026-06-15T09:00:00+09:00",
                    "end_time": "2026-06-15T10:00:00+09:00",
                }
            ],
        }

        with patch("app.schedule_agent.nodes.pre_validate.get_llm", return_value=llm):
            result = pre_validate_schedule(state)

        human_message = structured_llm.invoke.call_args.args[0][1]
        self.assertIn("location: 부산광역시", human_message.content)
        self.assertIn("'location': '서울특별시'", human_message.content)
        self.assertIn("'gap_minutes': 60", human_message.content)
        self.assertFalse(result["is_valid"])

    def test_rejects_when_llm_fails_in_operational_mode(self):
        state = {
            "title": "발표 준비",
            "detail_with_context": "발표 자료를 준비한다.",
            "start_time": "2026-06-10T10:00:00+09:00",
            "end_time": "2026-06-10T11:00:00+09:00",
            "existing_schedules": [{"title": "팀 회의"}],
        }

        with patch(
            "app.schedule_agent.nodes.pre_validate.get_llm",
            return_value=FakeLlm(error=RuntimeError("모델 호출 실패")),
        ):
            result = pre_validate_schedule(state)

        self.assertFalse(result["is_valid"])
        self.assertEqual(result["normalized_schedule"], {})
        self.assertIn("오류", result["invalid_reason"])

    def test_strict_mode_raises_when_llm_fails(self):
        state = {
            "title": "발표 준비",
            "detail_with_context": "발표 자료를 준비한다.",
            "start_time": "2026-06-10T10:00:00+09:00",
            "end_time": "2026-06-10T11:00:00+09:00",
            "existing_schedules": [],
        }

        with patch(
            "app.schedule_agent.nodes.pre_validate.get_llm",
            return_value=FakeLlm(error=RuntimeError("모델 호출 실패")),
        ):
            with self.assertRaisesRegex(RuntimeError, "모델 호출 실패"):
                pre_validate_schedule(state, strict=True)


if __name__ == "__main__":
    unittest.main()
