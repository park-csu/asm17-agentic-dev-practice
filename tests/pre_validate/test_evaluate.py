import unittest
from pathlib import Path

from evals.pre_validate.evaluate import build_stability_summary, build_summary, load_cases


class PreValidateEvaluateTest(unittest.TestCase):
    def test_loads_committed_evaluation_cases(self):
        cases = load_cases(Path("evals/pre_validate/cases.jsonl"))

        self.assertGreaterEqual(len(cases), 10)
        self.assertTrue(all(case.get("id") for case in cases))
        self.assertTrue(all("input" in case for case in cases))
        self.assertTrue(all("expected" in case for case in cases))

    def test_builds_summary_with_failed_case_ids(self):
        case_results = [
            {
                "id": "valid-001",
                "passed": True,
                "elapsed_seconds": 1.0,
                "expected": {"is_valid": True},
                "checks": {
                    "model_call_succeeded": True,
                    "is_valid_matches": True,
                    "normalized_required_fields": True,
                    "normalized_expected_values": True,
                },
            },
            {
                "id": "invalid-001",
                "passed": False,
                "elapsed_seconds": 3.0,
                "expected": {"is_valid": False},
                "checks": {
                    "model_call_succeeded": False,
                    "is_valid_matches": False,
                    "invalid_reason_exists": False,
                    "invalid_reason_keyword": False,
                },
            },
        ]

        summary = build_summary(case_results)

        self.assertEqual(summary["total_cases"], 2)
        self.assertEqual(summary["passed_cases"], 1)
        self.assertEqual(summary["model_errors"], 1)
        self.assertEqual(summary["validity_accuracy"], 0.5)
        self.assertEqual(summary["average_elapsed_seconds"], 2.0)
        self.assertEqual(summary["failed_case_ids"], ["invalid-001"])

    def test_builds_stability_summary_for_repeated_runs(self):
        cases = [{"id": "valid-001"}, {"id": "invalid-001"}]
        run_results = [
            {
                "summary": {"model_errors": 0},
                "case_results": [
                    {"id": "valid-001", "passed": True},
                    {"id": "invalid-001", "passed": True},
                ],
            },
            {
                "summary": {"model_errors": 1},
                "case_results": [
                    {"id": "valid-001", "passed": True},
                    {"id": "invalid-001", "passed": False},
                ],
            },
        ]

        stability = build_stability_summary(run_results, cases)

        self.assertFalse(stability["all_cases_stable"])
        self.assertEqual(stability["unstable_case_ids"], ["invalid-001"])
        self.assertEqual(stability["total_model_errors"], 1)
        self.assertEqual(stability["case_stability"][0]["passed_runs"], 2)
        self.assertEqual(stability["case_stability"][1]["passed_runs"], 1)


if __name__ == "__main__":
    unittest.main()
