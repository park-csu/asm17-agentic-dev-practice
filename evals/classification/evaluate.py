import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
CASES_PATH = Path(__file__).with_name("cases.jsonl")
RESULTS_DIR = Path(__file__).with_name("results")

sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from app.core.llm import MODEL  # noqa: E402
from app.schedule_agent.nodes.classification import classify_schedule  # noqa: E402


def load_cases(path: Path) -> list[dict]:
    """JSONL 평가 케이스를 읽는다."""
    cases = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number} JSON 형식이 올바르지 않습니다.") from error
    return cases


def evaluate_case(case: dict) -> dict:
    """단일 classification 케이스를 실제 LLM으로 평가한다."""
    started_at = perf_counter()
    try:
        result = classify_schedule(case["input"])
        error = ""
    except Exception as exception:
        result = {}
        error = f"{type(exception).__name__}: {exception}"
    elapsed_seconds = perf_counter() - started_at

    expected = case["expected"]
    question = result.get("question", "")
    detail_with_context = result.get("detail_with_context", "")
    question_keywords = expected.get("question_keywords_any", [])
    detail_keywords = expected.get("detail_keywords_any", [])

    checks = {
        "model_call_succeeded": not error,
        "is_decomposable_matches": result.get("is_decomposable") == expected["is_decomposable"],
        "needs_question_matches": result.get("needs_question", False) == expected["needs_question"],
        "question_source_matches": result.get("question_source", "") == expected.get("question_source", ""),
        "question_keyword": not question_keywords or any(keyword in question for keyword in question_keywords),
        "detail_keyword": not detail_keywords or any(keyword in detail_with_context for keyword in detail_keywords),
    }

    if not expected["needs_question"]:
        checks["question_empty"] = question == ""
    else:
        checks["question_exists"] = bool(question.strip())

    return {
        "id": case["id"],
        "description": case.get("description", ""),
        "passed": all(checks.values()),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "checks": checks,
        "expected": expected,
        "result": result,
        "error": error,
    }


def build_summary(case_results: list[dict]) -> dict:
    """전체 classification 평가 결과를 요약한다."""
    total = len(case_results)

    def ratio(passed: int, denominator: int) -> float:
        return round(passed / denominator, 4) if denominator else 0.0

    passed_cases = sum(result["passed"] for result in case_results)
    decomposable_matches = sum(result["checks"]["is_decomposable_matches"] for result in case_results)
    question_matches = sum(result["checks"]["needs_question_matches"] for result in case_results)
    source_matches = sum(result["checks"]["question_source_matches"] for result in case_results)
    model_errors = sum(not result["checks"]["model_call_succeeded"] for result in case_results)

    return {
        "total_cases": total,
        "passed_cases": passed_cases,
        "failed_cases": total - passed_cases,
        "case_pass_rate": ratio(passed_cases, total),
        "decomposable_accuracy": ratio(decomposable_matches, total),
        "question_accuracy": ratio(question_matches, total),
        "question_source_accuracy": ratio(source_matches, total),
        "model_errors": model_errors,
        "average_elapsed_seconds": round(
            sum(result["elapsed_seconds"] for result in case_results) / total,
            3,
        ) if total else 0.0,
        "failed_case_ids": [result["id"] for result in case_results if not result["passed"]],
    }


def build_stability_summary(run_results: list[dict], cases: list[dict]) -> dict:
    """반복 평가 결과에서 케이스별 안정성을 계산한다."""
    total_runs = len(run_results)
    case_stability = []
    for case in cases:
        case_id = case["id"]
        results = [
            result
            for run in run_results
            for result in run["case_results"]
            if result["id"] == case_id
        ]
        passed_runs = sum(result["passed"] for result in results)
        case_stability.append(
            {
                "id": case_id,
                "passed_runs": passed_runs,
                "total_runs": total_runs,
                "pass_rate": round(passed_runs / total_runs, 4) if total_runs else 0.0,
                "stable": passed_runs == total_runs,
            }
        )

    unstable_case_ids = [result["id"] for result in case_stability if not result["stable"]]
    return {
        "total_runs": total_runs,
        "all_cases_stable": not unstable_case_ids,
        "unstable_case_ids": unstable_case_ids,
        "case_stability": case_stability,
        "total_model_errors": sum(run["summary"]["model_errors"] for run in run_results),
    }


def save_report(report: dict) -> Path:
    """평가 리포트를 로컬 results 디렉터리에 저장한다."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result_path = RESULTS_DIR / f"classification_{timestamp}.json"
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return result_path


def print_summary(summary: dict, stability: dict, result_path: Path) -> None:
    """터미널에 평가 결과를 요약해 출력한다."""
    print("classification 실제 LLM 반복 평가 결과")
    print(f"- 모델: {MODEL}")
    print(f"- 반복 횟수: {stability['total_runs']}")
    print(f"- 전체 케이스: {summary['total_cases']}")
    print(f"- 마지막 실행 통과 케이스: {summary['passed_cases']}")
    print(f"- 마지막 실행 분해 필요 판단 정확도: {summary['decomposable_accuracy']:.1%}")
    print(f"- 마지막 실행 질문 필요 판단 정확도: {summary['question_accuracy']:.1%}")
    print(f"- 마지막 실행 질문 출처 정확도: {summary['question_source_accuracy']:.1%}")
    print(f"- 전체 모델 오류: {stability['total_model_errors']}")
    print(f"- 마지막 실행 평균 응답 시간: {summary['average_elapsed_seconds']:.3f}초")
    print(
        f"- {stability['total_runs']}/{stability['total_runs']} 안정성 통과: "
        f"{'예' if stability['all_cases_stable'] else '아니오'}"
    )
    print(f"- 불안정 케이스: {', '.join(stability['unstable_case_ids']) or '없음'}")
    print(f"- 결과 파일: {result_path}")


def parse_args() -> argparse.Namespace:
    """평가 실행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(description="classification 실제 LLM 성능 평가")
    parser.add_argument("--runs", type=int, default=5, help="전체 평가 반복 횟수 (기본값: 5)")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs는 1 이상이어야 합니다.")
    return args


def main() -> None:
    """classification 실제 LLM 반복 평가를 실행한다."""
    args = parse_args()
    cases = load_cases(CASES_PATH)
    run_results = []
    for run_index in range(1, args.runs + 1):
        print(f"[{run_index}/{args.runs}] 평가 실행 중...")
        case_results = [evaluate_case(case) for case in cases]
        summary = build_summary(case_results)
        print(f"[{run_index}/{args.runs}] 완료: {summary['passed_cases']}/{summary['total_cases']} 케이스 통과")
        run_results.append({"run": run_index, "summary": summary, "case_results": case_results})

    stability = build_stability_summary(run_results, cases)
    last_summary = run_results[-1]["summary"]
    report = {
        "model": MODEL,
        "cases_path": str(CASES_PATH),
        "runs": run_results,
        "stability": stability,
    }
    result_path = save_report(report)
    print_summary(last_summary, stability, result_path)


if __name__ == "__main__":
    main()
