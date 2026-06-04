import unittest
from unittest.mock import MagicMock, patch

from app.schedule_agent.nodes.post_validate import post_validate_tasks
from app.schedule_agent.schemas import PostValidationResult, ScheduleTask


def _make_task_dicts(n: int) -> list[dict]:
    """테스트용 task dict 목록을 n개 생성한다."""
    return [
        {
            "title": f"task {i}",
            "description": f"설명 {i}",
            "estimated_minutes": 30,
            "order_index": i,
        }
        for i in range(1, n + 1)
    ]


def _make_llm_mock(result: PostValidationResult) -> MagicMock:
    """post_validate_tasks가 기대하는 get_llm().with_structured_output().invoke() 체인 mock을 반환한다."""
    mock_llm_instance = MagicMock()
    mock_llm_instance.invoke.return_value = result
    mock_get_llm = MagicMock()
    mock_get_llm.return_value.with_structured_output.return_value = mock_llm_instance
    return mock_get_llm


class PostValidateTasksNodeTest(unittest.TestCase):
    """
    대상 노드: app/schedule_agent/nodes/post_validate.py :: post_validate_tasks

    이 노드는 plan 노드가 생성한 task 목록의 실행 가능성·원 일정 적합성을 검증한다.

    검증 범위:
    - task 개수(1~5) 선제 검사 — LLM 호출 없이 수행한다.
    - 개수 통과 시 LLM(PostValidationResult 구조화 출력)으로 품질을 검증한다.
    - LLM 예외 발생 시 fail-open(is_valid=True, 기존 tasks 유지)으로 처리한다.
    """

    # ── 개수 선제 검증 ──────────────────────────────────────────────────────────

    def test_empty_tasks_returns_invalid_without_llm(self):
        """task 0개: LLM을 호출하지 않고 is_valid=False를 반환해야 한다."""
        with patch("app.schedule_agent.nodes.post_validate.get_llm") as mock_get_llm:
            result = post_validate_tasks({"tasks": [], "normalized_schedule": {}})
            mock_get_llm.assert_not_called()

        self.assertFalse(result["is_valid"])
        self.assertIn("1~5", result["invalid_reason"])

    def test_six_tasks_returns_invalid_without_llm(self):
        """task 6개(초과): LLM을 호출하지 않고 is_valid=False를 반환해야 한다."""
        state = {"tasks": _make_task_dicts(6), "normalized_schedule": {}}

        with patch("app.schedule_agent.nodes.post_validate.get_llm") as mock_get_llm:
            result = post_validate_tasks(state)
            mock_get_llm.assert_not_called()

        self.assertFalse(result["is_valid"])
        self.assertIn("1~5", result["invalid_reason"])

    # ── 경계값: LLM 호출 여부 ──────────────────────────────────────────────────

    def test_one_task_passes_count_check_and_calls_llm(self):
        """task 1개(최솟값 경계): 개수 검사를 통과하고 LLM을 호출해야 한다."""
        tasks = _make_task_dicts(1)
        mock_result = PostValidationResult(
            is_valid=True, tasks=[ScheduleTask(**tasks[0])], invalid_reason=""
        )

        with patch("app.schedule_agent.nodes.post_validate.get_llm", _make_llm_mock(mock_result)):
            result = post_validate_tasks({"tasks": tasks, "normalized_schedule": {}})

        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["tasks"]), 1)

    def test_five_tasks_passes_count_check_and_calls_llm(self):
        """task 5개(최댓값 경계): 개수 검사를 통과하고 LLM을 호출해야 한다."""
        tasks = _make_task_dicts(5)
        schedule_tasks = [ScheduleTask(**t) for t in tasks]
        mock_result = PostValidationResult(
            is_valid=True, tasks=schedule_tasks, invalid_reason=""
        )

        with patch("app.schedule_agent.nodes.post_validate.get_llm", _make_llm_mock(mock_result)):
            result = post_validate_tasks({"tasks": tasks, "normalized_schedule": {}})

        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["tasks"]), 5)

    # ── LLM 정상 응답 ─────────────────────────────────────────────────────────

    def test_llm_valid_result_is_returned_correctly(self):
        """LLM이 is_valid=True를 반환하면 tasks와 빈 invalid_reason을 반환해야 한다."""
        tasks = _make_task_dicts(3)
        schedule_tasks = [ScheduleTask(**t) for t in tasks]
        mock_result = PostValidationResult(
            is_valid=True, tasks=schedule_tasks, invalid_reason=""
        )

        with patch("app.schedule_agent.nodes.post_validate.get_llm", _make_llm_mock(mock_result)):
            result = post_validate_tasks(
                {"tasks": tasks, "normalized_schedule": {"title": "발표 준비"}}
            )

        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["tasks"]), 3)
        self.assertEqual(result["invalid_reason"], "")

    def test_llm_invalid_result_propagates_reason(self):
        """LLM이 is_valid=False를 반환하면 invalid_reason이 결과에 포함되어야 한다."""
        tasks = _make_task_dicts(2)
        mock_result = PostValidationResult(
            is_valid=False,
            tasks=[],
            invalid_reason="task 제목이 추상적입니다.",
        )

        with patch("app.schedule_agent.nodes.post_validate.get_llm", _make_llm_mock(mock_result)):
            result = post_validate_tasks({"tasks": tasks, "normalized_schedule": {}})

        self.assertFalse(result["is_valid"])
        self.assertIn("추상적", result["invalid_reason"])

    # ── LLM 예외 처리: fail-open ───────────────────────────────────────────────

    def test_llm_invoke_exception_returns_fail_open(self):
        """LLM invoke 중 예외 발생: fail-open(is_valid=True, 기존 tasks)을 반환해야 한다."""
        tasks = _make_task_dicts(2)
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = RuntimeError("LLM 연결 오류")

        with patch("app.schedule_agent.nodes.post_validate.get_llm") as mock_get_llm:
            mock_get_llm.return_value.with_structured_output.return_value = mock_llm_instance
            result = post_validate_tasks({"tasks": tasks, "normalized_schedule": {}})

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["tasks"], tasks)
        self.assertEqual(result["invalid_reason"], "")

    def test_llm_timeout_returns_fail_open(self):
        """LLM 타임아웃: fail-open으로 기존 tasks를 반환해야 한다."""
        tasks = _make_task_dicts(3)
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = TimeoutError("응답 시간 초과")

        with patch("app.schedule_agent.nodes.post_validate.get_llm") as mock_get_llm:
            mock_get_llm.return_value.with_structured_output.return_value = mock_llm_instance
            result = post_validate_tasks({"tasks": tasks, "normalized_schedule": {}})

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["tasks"], tasks)

    def test_with_structured_output_exception_returns_fail_open(self):
        """with_structured_output 호출 중 예외 발생: fail-open을 반환해야 한다."""
        tasks = _make_task_dicts(2)

        with patch("app.schedule_agent.nodes.post_validate.get_llm") as mock_get_llm:
            mock_get_llm.return_value.with_structured_output.side_effect = ValueError("스키마 오류")
            result = post_validate_tasks({"tasks": tasks, "normalized_schedule": {}})

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["tasks"], tasks)
        self.assertEqual(result["invalid_reason"], "")

    # ── 반환 구조 ─────────────────────────────────────────────────────────────

    def test_result_always_contains_required_keys(self):
        """모든 경로에서 반환 dict에 is_valid, tasks, invalid_reason 키가 있어야 한다."""
        tasks = _make_task_dicts(2)
        schedule_tasks = [ScheduleTask(**t) for t in tasks]
        mock_result = PostValidationResult(
            is_valid=True, tasks=schedule_tasks, invalid_reason=""
        )

        with patch("app.schedule_agent.nodes.post_validate.get_llm", _make_llm_mock(mock_result)):
            result = post_validate_tasks({"tasks": tasks, "normalized_schedule": {}})

        for key in ("is_valid", "tasks", "invalid_reason"):
            self.assertIn(key, result, f"'{key}' 키가 반환 dict에 없습니다.")

    def test_invalid_count_result_contains_required_keys(self):
        """개수 초과로 조기 반환할 때도 is_valid, tasks, invalid_reason 키가 있어야 한다."""
        with patch("app.schedule_agent.nodes.post_validate.get_llm"):
            result = post_validate_tasks({"tasks": [], "normalized_schedule": {}})

        for key in ("is_valid", "tasks", "invalid_reason"):
            self.assertIn(key, result, f"'{key}' 키가 반환 dict에 없습니다.")


if __name__ == "__main__":
    unittest.main()
