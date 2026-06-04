import unittest
from unittest.mock import MagicMock, patch

from app.schedule_agent.nodes.classification import classify_schedule
from app.schedule_agent.schemas import ClassificationResult


# classify_schedule 노드의 분해 필요성 판단, 질문 생성, LLM 실패 fallback 경로를 검증한다.
class ClassificationNodeTest(unittest.TestCase):
    def _patch_llm(self, *, classification_result=None, error=None):
        """get_llm(...).with_structured_output(...).invoke(...) 호출 체인을 모킹한다."""
        patcher = patch("app.schedule_agent.nodes.classification.get_llm")
        mock_get_llm = patcher.start()
        self.addCleanup(patcher.stop)

        structured_llm = MagicMock()
        if error is not None:
            structured_llm.invoke.side_effect = error
        else:
            structured_llm.invoke.return_value = classification_result
        mock_get_llm.return_value.with_structured_output.return_value = structured_llm
        return mock_get_llm

    def test_classify_schedule_returns_decomposable_structured_result(self):
        # LLM이 분해 가능한 일정이라고 판단하면 결과와 질문 출처를 그대로 반환한다.
        classification_result = ClassificationResult(
            is_decomposable=True,
            needs_question=False,
            question="",
            detail_with_context="발표 자료를 준비한다.",
        )
        self._patch_llm(classification_result=classification_result)

        result = classify_schedule(
            {
                "title": "발표 준비",
                "detail": "발표 자료를 준비한다.",
                "start_time": "2026-06-10T10:00:00+09:00",
                "end_time": "2026-06-10T12:00:00+09:00",
            }
        )

        self.assertTrue(result["is_decomposable"])
        self.assertFalse(result["needs_question"])
        self.assertEqual(result["question_source"], "")
        self.assertEqual(result["detail_with_context"], "발표 자료를 준비한다.")

    def test_classify_schedule_marks_classification_question_source(self):
        # 분해 가능한 일정이지만 맥락이 부족하면 classification 질문 출처를 표시한다.
        classification_result = ClassificationResult(
            is_decomposable=True,
            needs_question=True,
            question="발표의 완료 기준은 무엇인가요?",
            detail_with_context="발표 준비",
        )
        self._patch_llm(classification_result=classification_result)

        result = classify_schedule(
            {
                "title": "발표 준비",
                "detail": "",
                "start_time": "2026-06-10T10:00:00+09:00",
                "end_time": "2026-06-10T12:00:00+09:00",
            }
        )

        self.assertTrue(result["is_decomposable"])
        self.assertTrue(result["needs_question"])
        self.assertEqual(result["question_source"], "classification")
        self.assertEqual(result["question"], "발표의 완료 기준은 무엇인가요?")

    def test_classify_schedule_never_asks_when_schedule_is_not_decomposable(self):
        # LLM이 질문을 같이 반환해도 분해 불필요 일정이면 classification 질문을 만들지 않는다.
        classification_result = ClassificationResult(
            is_decomposable=False,
            needs_question=True,
            question="무엇을 완료하면 되나요?",
            detail_with_context="양치하기",
        )
        self._patch_llm(classification_result=classification_result)

        result = classify_schedule(
            {
                "title": "양치하기",
                "detail": "",
                "start_time": "2026-06-10T08:00:00+09:00",
                "end_time": "2026-06-10T08:05:00+09:00",
            }
        )

        self.assertFalse(result["is_decomposable"])
        self.assertFalse(result["needs_question"])
        self.assertEqual(result["question"], "")
        self.assertEqual(result["question_source"], "")

    def test_classify_schedule_stops_question_when_retry_is_exhausted(self):
        # classification_retry가 max_retry에 도달하면 LLM을 호출하지 않고 질문을 중단한다.
        mock_get_llm = self._patch_llm(error=AssertionError("재시도 소진 후에는 LLM을 호출하면 안 됩니다."))

        result = classify_schedule(
            {
                "title": "발표 준비",
                "detail": "자료 조사",
                "detail_with_context": "자료 조사",
                "classification_retry": 2,
                "max_retry": 2,
                "is_decomposable": True,
            }
        )

        mock_get_llm.assert_not_called()
        self.assertTrue(result["is_decomposable"])
        self.assertFalse(result["needs_question"])
        self.assertEqual(result["question_source"], "")

    def test_classify_schedule_falls_back_to_question_on_llm_error_with_sparse_input(self):
        # LLM 호출이 실패하고 시간 또는 상세 맥락이 부족하면 기본 classification 질문을 반환한다.
        self._patch_llm(error=RuntimeError("LLM 호출 실패"))

        result = classify_schedule(
            {
                "title": "회의",
                "detail": "",
                "detail_with_context": "",
                "start_time": "",
                "end_time": "",
            }
        )

        self.assertTrue(result["is_decomposable"])
        self.assertTrue(result["needs_question"])
        self.assertEqual(result["question_source"], "classification")
        self.assertIn("언제부터 언제까지", result["question"])


if __name__ == "__main__":
    unittest.main()
