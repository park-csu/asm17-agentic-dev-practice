import unittest

from app.schedule_agent.nodes.ask_context import ask_context


# ask_context 노드의 보충 답변 누적과 질문 출처별 retry 증가를 검증한다.
class AskContextNodeTest(unittest.TestCase):
    def test_ask_context_accumulates_context_answer_without_incrementing_retry(self):
        # 사용자가 보충 답변을 보낸 요청에서는 답변만 누적하고 질문 retry를 증가시키지 않는다.
        result = ask_context(
            {
                "detail_with_context": "발표 준비",
                "question_source": "classification",
                "question": "완료 기준은 무엇인가요?",
                "context_answer": "초안 슬라이드까지 만들면 됩니다.",
                "classification_retry": 1,
            }
        )

        self.assertIn("완료 기준은 무엇인가요?", result["detail_with_context"])
        self.assertIn("초안 슬라이드까지 만들면 됩니다.", result["detail_with_context"])
        self.assertNotIn("classification_retry", result)
        self.assertNotIn("status", result)

    def test_ask_context_accumulates_answer_without_question_text(self):
        # 이전 질문 문구가 전달되지 않아도 사용자 답변은 누적 컨텍스트에 보존한다.
        result = ask_context(
            {
                "detail_with_context": "자료 조사",
                "context_answer": "경쟁사 3곳을 비교하면 됩니다.",
            }
        )

        self.assertIn("사용자 답변: 경쟁사 3곳을 비교하면 됩니다.", result["detail_with_context"])
        self.assertNotIn("추가 질문:", result["detail_with_context"])
        self.assertNotIn("status", result)

    def test_ask_context_increments_only_pre_validation_retry(self):
        # pre_validate 질문을 반환할 때는 pre_validation_retry만 증가시키고 질문 문구를 보존한다.
        result = ask_context(
            {
                "question_source": "pre_validate",
                "question": "이 작업은 현장 도착이 필수인가요?",
                "classification_retry": 1,
                "pre_validation_retry": 0,
            }
        )

        self.assertEqual(result["status"], "needs_question")
        self.assertNotIn("classification_retry", result)
        self.assertEqual(result["pre_validation_retry"], 1)
        self.assertEqual(
            result["pre_validation_question"],
            "이 작업은 현장 도착이 필수인가요?",
        )

    def test_ask_context_increments_only_classification_retry(self):
        # classification 질문을 반환할 때는 classification_retry만 증가시킨다.
        result = ask_context(
            {
                "question_source": "classification",
                "question": "완료 기준은 무엇인가요?",
                "classification_retry": 0,
                "pre_validation_retry": 1,
            }
        )

        self.assertEqual(result["status"], "needs_question")
        self.assertEqual(result["classification_retry"], 1)
        self.assertNotIn("pre_validation_retry", result)

    def test_ask_context_preserves_is_decomposable_state(self):
        # 질문 반환 중에도 classification의 분해 필요성 판단 결과를 유지한다.
        result = ask_context(
            {
                "question_source": "classification",
                "question": "완료 기준은 무엇인가요?",
                "classification_retry": 0,
                "is_decomposable": False,
            }
        )

        self.assertFalse(result["is_decomposable"])


if __name__ == "__main__":
    unittest.main()
