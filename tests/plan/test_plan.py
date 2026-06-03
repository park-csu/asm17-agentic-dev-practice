import unittest
from unittest.mock import MagicMock, patch

from app.schedule_agent.nodes.plan import plan_tasks
from app.schedule_agent.schemas import PlanResult, ScheduleTask


# plan_tasks 노드의 정상 분해 경로와 LLM 실패 시 fallback 경로, plan_retry 누적을 검증한다.
class PlanTasksTest(unittest.TestCase):
    def _patch_llm(self, *, plan_result=None, error=None):
        """get_llm(...).with_structured_output(...).invoke(...) 호출 체인을 모킹한다."""
        patcher = patch("app.schedule_agent.nodes.plan.get_llm")
        mock_get_llm = patcher.start()
        self.addCleanup(patcher.stop)

        structured_llm = MagicMock()
        if error is not None:
            structured_llm.invoke.side_effect = error
        else:
            structured_llm.invoke.return_value = plan_result
        mock_get_llm.return_value.with_structured_output.return_value = structured_llm
        return mock_get_llm

    def test_plan_tasks_returns_llm_tasks_on_success(self):
        # LLM이 정상 응답하면 분해된 task와 plan_reason을 그대로 전달한다.
        plan_result = PlanResult(
            tasks=[
                ScheduleTask(title="자료 조사", description="발표 주제 자료를 모은다", estimated_minutes=40, order_index=1),
                ScheduleTask(title="슬라이드 작성", description="핵심 메시지를 슬라이드로 만든다", estimated_minutes=60, order_index=2),
                ScheduleTask(title="리허설", description="발표 흐름을 점검한다", estimated_minutes=30, order_index=3),
            ],
            plan_reason="발표 준비를 3단계로 분해했습니다.",
        )
        self._patch_llm(plan_result=plan_result)

        result = plan_tasks({"normalized_schedule": {"title": "발표 준비"}, "plan_retry": 0})

        self.assertEqual(len(result["tasks"]), 3)
        self.assertEqual(result["tasks"][0]["title"], "자료 조사")
        self.assertEqual(result["plan_reason"], "발표 준비를 3단계로 분해했습니다.")
        self.assertEqual(result["plan_retry"], 1)

    def test_plan_tasks_increments_existing_plan_retry(self):
        # 기존 plan_retry 값이 있으면 1만큼 증가시켜 반환한다.
        plan_result = PlanResult(
            tasks=[ScheduleTask(title="자료 조사", description="", estimated_minutes=30, order_index=1)],
            plan_reason="",
        )
        self._patch_llm(plan_result=plan_result)

        result = plan_tasks({"normalized_schedule": {"title": "발표 준비"}, "plan_retry": 1})

        self.assertEqual(result["plan_retry"], 2)

    def test_plan_tasks_falls_back_to_default_tasks_on_llm_error(self):
        # LLM 호출이 실패하면 기본 2단계 task와 실패 사유를 반환한다.
        self._patch_llm(error=RuntimeError("LLM 호출 실패"))

        result = plan_tasks({"normalized_schedule": {"title": "발표 준비"}, "plan_retry": 0})

        self.assertEqual(len(result["tasks"]), 2)
        self.assertTrue(result["tasks"][0]["title"].startswith("발표 준비"))
        self.assertIn("실패", result["plan_reason"])
        self.assertEqual(result["plan_retry"], 1)

    def test_plan_tasks_fallback_uses_default_title_when_schedule_missing(self):
        # normalized_schedule이 비어 있으면 기본 제목 "일정"으로 fallback task를 만든다.
        self._patch_llm(error=RuntimeError("LLM 호출 실패"))

        result = plan_tasks({})

        self.assertEqual(result["tasks"][0]["title"], "일정 준비하기")
        self.assertEqual(result["plan_retry"], 1)

    def test_plan_tasks_reindexes_order_index_sequentially(self):
        # LLM이 order_index를 전부 1로 채워도 리스트 순서대로 1..n으로 재부여한다.
        plan_result = PlanResult(
            tasks=[
                ScheduleTask(title="자료 조사", description="", estimated_minutes=40, order_index=1),
                ScheduleTask(title="슬라이드 작성", description="", estimated_minutes=60, order_index=1),
                ScheduleTask(title="리허설", description="", estimated_minutes=30, order_index=1),
            ],
            plan_reason="",
        )
        self._patch_llm(plan_result=plan_result)

        result = plan_tasks({"normalized_schedule": {"title": "발표 준비"}, "plan_retry": 0})

        self.assertEqual([task["order_index"] for task in result["tasks"]], [1, 2, 3])

    def test_plan_tasks_distributes_minutes_when_uniform_and_duration_known(self):
        # estimated_minutes가 전부 동일하고 duration_minutes를 알면 합이 일정 길이와 맞도록 균등 분배한다.
        plan_result = PlanResult(
            tasks=[
                ScheduleTask(title="A", description="", estimated_minutes=30, order_index=1),
                ScheduleTask(title="B", description="", estimated_minutes=30, order_index=2),
                ScheduleTask(title="C", description="", estimated_minutes=30, order_index=3),
            ],
            plan_reason="",
        )
        self._patch_llm(plan_result=plan_result)

        result = plan_tasks({"normalized_schedule": {"title": "발표 준비", "duration_minutes": 100}, "plan_retry": 0})

        minutes = [task["estimated_minutes"] for task in result["tasks"]]
        self.assertEqual(sum(minutes), 100)
        self.assertEqual(minutes, [34, 33, 33])

    def test_plan_tasks_keeps_varied_minutes(self):
        # LLM이 estimated_minutes를 다양하게 채운 경우에는 보정하지 않고 그대로 둔다.
        plan_result = PlanResult(
            tasks=[
                ScheduleTask(title="A", description="", estimated_minutes=40, order_index=1),
                ScheduleTask(title="B", description="", estimated_minutes=60, order_index=2),
                ScheduleTask(title="C", description="", estimated_minutes=30, order_index=3),
            ],
            plan_reason="",
        )
        self._patch_llm(plan_result=plan_result)

        result = plan_tasks({"normalized_schedule": {"title": "발표 준비", "duration_minutes": 130}, "plan_retry": 0})

        self.assertEqual([task["estimated_minutes"] for task in result["tasks"]], [40, 60, 30])

    def test_plan_tasks_skips_minute_distribution_without_duration(self):
        # duration_minutes가 없으면 estimated_minutes를 보정하지 않는다.
        plan_result = PlanResult(
            tasks=[
                ScheduleTask(title="A", description="", estimated_minutes=30, order_index=1),
                ScheduleTask(title="B", description="", estimated_minutes=30, order_index=2),
            ],
            plan_reason="",
        )
        self._patch_llm(plan_result=plan_result)

        result = plan_tasks({"normalized_schedule": {"title": "발표 준비"}, "plan_retry": 0})

        self.assertEqual([task["estimated_minutes"] for task in result["tasks"]], [30, 30])


if __name__ == "__main__":
    unittest.main()
