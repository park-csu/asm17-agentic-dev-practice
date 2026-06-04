import unittest
from unittest.mock import MagicMock, patch

from app.api import build_initial_state, build_response
from app.schedule_agent.nodes.ask_context import ask_context
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

    def test_api_state_and_response_preserve_question_state(self):
        request = ScheduleTaskRequest(
            pre_validation_retry=1,
            question_source="pre_validate",
            question="이 작업은 현장 도착이 필수인가요?",
        )

        state = build_initial_state(request)
        response = build_response({**state, "status": "needs_question"})

        self.assertEqual(state["pre_validation_retry"], 1)
        self.assertEqual(state["question_source"], "pre_validate")
        self.assertEqual(response.question, "이 작업은 현장 도착이 필수인가요?")

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

        self.assertEqual(result, {**expected.model_dump(), "question_source": ""})

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

    def test_returns_question_when_location_requirement_is_ambiguous(self):
        expected = PreValidationResult(
            is_valid=False,
            needs_question=True,
            question="이 문서 작업은 한국에 도착해야만 가능한가요?",
            normalized_schedule={},
            invalid_reason="",
        )
        state = {
            "title": "한국 보고서 작성",
            "detail_with_context": "한국 사업 보고서를 작성한다.",
            "location": "대한민국 서울",
            "start_time": "2026-06-15T13:00:00+09:00",
            "end_time": "2026-06-15T14:00:00+09:00",
            "existing_schedules": [
                {
                    "title": "영국 미팅",
                    "location": "영국 런던",
                    "start_time": "2026-06-15T08:00:00+09:00",
                    "end_time": "2026-06-15T10:00:00+09:00",
                }
            ],
            "pre_validation_retry": 0,
            "max_retry": 2,
        }

        with patch(
            "app.schedule_agent.nodes.pre_validate.get_llm",
            return_value=FakeLlm(result=expected),
        ):
            result = pre_validate_schedule(state)

        self.assertTrue(result["needs_question"])
        self.assertEqual(result["question_source"], "pre_validate")
        self.assertEqual(result["question"], "이 문서 작업은 한국에 도착해야만 가능한가요?")
        self.assertEqual(result["invalid_reason"], "")

    def test_forces_location_question_when_llm_returns_valid(self):
        expected = PreValidationResult(
            is_valid=True,
            needs_question=False,
            question="",
            normalized_schedule={"title": "한국 보고서 작성"},
            invalid_reason="",
        )
        state = {
            "title": "한국 보고서 작성",
            "detail_with_context": "한국 사업 보고서를 작성한다.",
            "location": "대한민국 서울",
            "start_time": "2026-06-15T13:00:00+09:00",
            "end_time": "2026-06-15T14:00:00+09:00",
            "existing_schedules": [
                {
                    "title": "영국 고객 미팅",
                    "location": "영국 런던",
                    "start_time": "2026-06-15T08:00:00+09:00",
                    "end_time": "2026-06-15T10:00:00+09:00",
                }
            ],
            "pre_validation_retry": 0,
            "max_retry": 2,
        }

        with patch(
            "app.schedule_agent.nodes.pre_validate.get_llm",
            return_value=FakeLlm(result=expected),
        ):
            result = pre_validate_schedule(state)

        self.assertTrue(result["needs_question"])
        self.assertEqual(result["question_source"], "pre_validate")
        self.assertEqual(result["invalid_reason"], "")

    def test_replaces_placeholder_location_question(self):
        expected = PreValidationResult(
            is_valid=True,
            needs_question=False,
            question="null string (empty string as per default value in schema)",
            normalized_schedule={},
            invalid_reason="",
        )
        state = {
            "title": "한국 보고서 작성",
            "detail_with_context": "한국 사업 보고서를 작성한다.",
            "location": "대한민국 서울",
            "start_time": "2026-06-15T13:00:00+09:00",
            "end_time": "2026-06-15T14:00:00+09:00",
            "existing_schedules": [
                {
                    "title": "영국 고객 미팅",
                    "location": "영국 런던",
                    "start_time": "2026-06-15T08:00:00+09:00",
                    "end_time": "2026-06-15T10:00:00+09:00",
                }
            ],
            "pre_validation_retry": 0,
            "max_retry": 2,
        }

        with patch(
            "app.schedule_agent.nodes.pre_validate.get_llm",
            return_value=FakeLlm(result=expected),
        ):
            result = pre_validate_schedule(state)

        self.assertTrue(result["needs_question"])
        self.assertIn("도착", result["question"])
        self.assertNotIn("null string", result["question"])

    def test_does_not_allow_non_location_validation_question(self):
        expected = PreValidationResult(
            is_valid=False,
            needs_question=True,
            question="구체적인 시간을 알려 주세요.",
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

        self.assertFalse(result["needs_question"])
        self.assertEqual(result["question"], "")
        self.assertIn("시간", result["invalid_reason"])

    def test_rejects_question_when_pre_validation_retry_is_exhausted(self):
        expected = PreValidationResult(
            is_valid=False,
            needs_question=True,
            question="이 작업은 현장 도착이 필수인가요?",
            normalized_schedule={},
            invalid_reason="",
        )
        state = {
            "title": "한국 보고서 작성",
            "detail_with_context": "한국 사업 보고서를 작성한다.",
            "location": "대한민국 서울",
            "start_time": "2026-06-15T13:00:00+09:00",
            "end_time": "2026-06-15T14:00:00+09:00",
            "existing_schedules": [
                {
                    "title": "영국 고객 미팅",
                    "location": "영국 런던",
                    "start_time": "2026-06-15T08:00:00+09:00",
                    "end_time": "2026-06-15T10:00:00+09:00",
                }
            ],
            "pre_validation_retry": 2,
            "max_retry": 2,
        }

        with patch(
            "app.schedule_agent.nodes.pre_validate.get_llm",
            return_value=FakeLlm(result=expected),
        ):
            result = pre_validate_schedule(state)

        self.assertFalse(result["needs_question"])
        self.assertFalse(result["is_valid"])
        self.assertIn("위치 제약", result["invalid_reason"])

    def test_ask_context_increments_only_pre_validation_retry(self):
        result = ask_context(
            {
                "question_source": "pre_validate",
                "question": "이 작업은 현장 도착이 필수인가요?",
                "classification_retry": 1,
                "pre_validation_retry": 0,
            }
        )

        self.assertNotIn("classification_retry", result)
        self.assertEqual(result["pre_validation_retry"], 1)
        self.assertEqual(set(result), {"detail_with_context", "is_decomposable", "status", "pre_validation_retry"})

    def test_ask_context_increments_only_classification_retry(self):
        result = ask_context(
            {
                "question_source": "classification",
                "question": "완료 기준은 무엇인가요?",
                "classification_retry": 0,
                "pre_validation_retry": 1,
            }
        )

        self.assertEqual(result["classification_retry"], 1)
        self.assertNotIn("pre_validation_retry", result)

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
