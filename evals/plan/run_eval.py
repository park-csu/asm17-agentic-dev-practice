"""plan 노드(plan_tasks) LLM 분해 품질을 데이터셋 위에서 평가하는 러너.

규칙 기반 채점(결정적)과 LLM-as-judge 채점(주관 품질)을 함께 수행하고,
케이스별/전체 점수를 stdout 리포트와 results.jsonl로 남긴다.

실행: uv run python -m evals.plan.run_eval
"""

import json
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

# app 패키지 import 시 app/__init__.py가 load_dotenv()를 호출해 UPSTAGE_API_KEY를 로드한다.
from app.core.config import UPSTAGE_API_KEY
from app.core.llm import get_llm
from app.schedule_agent.nodes.plan import plan_tasks

# plan.py의 fallback plan_reason 문구. 이 문구가 보이면 LLM 생성이 실패한 케이스로 간주한다.
FALLBACK_MARKER = "LLM 계획 생성 실패"

DATASET_PATH = Path(__file__).parent / "dataset.jsonl"
RESULTS_PATH = Path(__file__).parent / "results.jsonl"

JUDGE_SYSTEM = """당신은 일정 task 분해 결과의 품질을 평가하는 평가자입니다.
주어진 일정(normalized_schedule)과 분해된 task 목록을 보고 아래 4개 기준을 각각 1~5점으로 채점하세요.

채점 기준 (1=매우 나쁨, 5=매우 좋음):
1. relevance: task들이 원 일정의 목적과 직접 연결되는가.
2. actionability: 각 task가 추상적 구호가 아니라 바로 실행 가능한 구체적 행동인가.
3. coverage: 일정을 완수하는 데 필요한 핵심 단계를 빠짐없이 담았는가.
4. ordering: order_index 순서가 실제 수행 순서로 합리적인가.

reasoning에는 점수를 그렇게 준 핵심 근거를 한국어로 간단히 적으세요.
반드시 지정된 구조화 출력 형식으로만 응답하세요."""


# LLM judge가 반환하는 평가 점수 스키마 (eval 전용, app 스키마와 분리)
class PlanJudgeResult(BaseModel):
    relevance: int = Field(ge=1, le=5, description="원 일정과의 관련성")
    actionability: int = Field(ge=1, le=5, description="각 task의 실행 구체성")
    coverage: int = Field(ge=1, le=5, description="필요한 핵심 단계의 포괄성")
    ordering: int = Field(ge=1, le=5, description="order_index 순서의 타당성")
    reasoning: str = Field(default="", description="점수 근거")


JUDGE_DIMENSIONS = ["relevance", "actionability", "coverage", "ordering"]


def load_dataset() -> list[dict]:
    """dataset.jsonl을 한 줄씩 읽어 케이스 목록으로 반환한다."""
    cases = []
    with DATASET_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def score_rules(tasks: list[dict]) -> dict:
    """LLM 없이 결정적으로 검증 가능한 구조 규칙을 채점한다."""
    titles = [str(t.get("title", "")).strip() for t in tasks]
    order_indexes = [t.get("order_index") for t in tasks]
    minutes = [t.get("estimated_minutes") for t in tasks]

    checks = {
        "count_in_range": 1 <= len(tasks) <= 5,
        "order_index_sequential": sorted(order_indexes) == list(range(1, len(tasks) + 1)),
        "minutes_positive_int": all(isinstance(m, int) and m > 0 for m in minutes),
        "titles_unique": len(titles) == len({t.lower() for t in titles}),
        "titles_nonempty": all(titles) and len(titles) == len(tasks),
    }
    passed = sum(1 for ok in checks.values() if ok)
    return {
        "checks": checks,
        "pass_rate": round(passed / len(checks) * 100, 1),
    }


def score_with_judge(normalized_schedule: dict, tasks: list[dict]) -> PlanJudgeResult:
    """LLM judge로 분해 결과의 주관 품질을 1~5점으로 채점한다."""
    llm = get_llm(temperature=0.0).with_structured_output(PlanJudgeResult)
    return llm.invoke(
        [
            SystemMessage(content=JUDGE_SYSTEM),
            HumanMessage(
                content=(
                    f"normalized_schedule: {json.dumps(normalized_schedule, ensure_ascii=False)}\n"
                    f"tasks: {json.dumps(tasks, ensure_ascii=False)}"
                )
            ),
        ]
    )


def evaluate_case(case: dict) -> dict:
    """단일 케이스에 대해 plan_tasks 실행 → 규칙 채점 → judge 채점을 수행한다."""
    case_id = case.get("id", "unknown")
    normalized_schedule = case.get("normalized_schedule", {})

    # 평가 대상 노드를 실제로 실행한다 (내부에서 실제 LLM 호출).
    plan_output = plan_tasks({"normalized_schedule": normalized_schedule})
    tasks = plan_output.get("tasks", [])
    plan_reason = plan_output.get("plan_reason", "")
    is_fallback = FALLBACK_MARKER in plan_reason

    rules = score_rules(tasks)

    record = {
        "id": case_id,
        "num_tasks": len(tasks),
        "is_fallback": is_fallback,
        "rules": rules,
        "tasks": tasks,
        "plan_reason": plan_reason,
    }

    try:
        judge = score_with_judge(normalized_schedule, tasks)
        judge_scores = {dim: getattr(judge, dim) for dim in JUDGE_DIMENSIONS}
        record["judge"] = {
            **judge_scores,
            "average": round(sum(judge_scores.values()) / len(JUDGE_DIMENSIONS), 2),
            "reasoning": judge.reasoning,
        }
    except Exception as e:  # judge 실패 시 케이스를 error로 기록하고 전체는 계속 진행
        record["judge"] = None
        record["error"] = f"judge 호출 실패: {e}"

    return record


def aggregate(records: list[dict]) -> dict:
    """케이스별 결과를 전체 지표로 집계한다."""
    judged = [r for r in records if r.get("judge")]
    summary = {
        "case_count": len(records),
        "fallback_count": sum(1 for r in records if r["is_fallback"]),
        "judge_error_count": sum(1 for r in records if r.get("error")),
        "avg_rule_pass_rate": round(sum(r["rules"]["pass_rate"] for r in records) / len(records), 1) if records else 0.0,
    }
    for dim in JUDGE_DIMENSIONS:
        summary[f"avg_{dim}"] = round(sum(r["judge"][dim] for r in judged) / len(judged), 2) if judged else None
    summary["avg_judge_overall"] = (
        round(sum(r["judge"]["average"] for r in judged) / len(judged), 2) if judged else None
    )
    return summary


def print_report(records: list[dict], summary: dict) -> None:
    """케이스별 점수와 전체 요약을 stdout에 출력한다."""
    print("\n=== plan 노드 Evaluation 리포트 ===\n")
    print(f"{'id':<26} {'tasks':>5} {'규칙%':>6} {'rel':>4} {'act':>4} {'cov':>4} {'ord':>4} {'평균':>5}  비고")
    print("-" * 88)
    for r in records:
        j = r.get("judge")
        if j:
            row = f"{r['id']:<26} {r['num_tasks']:>5} {r['rules']['pass_rate']:>6} {j['relevance']:>4} {j['actionability']:>4} {j['coverage']:>4} {j['ordering']:>4} {j['average']:>5}"
        else:
            row = f"{r['id']:<26} {r['num_tasks']:>5} {r['rules']['pass_rate']:>6} {'-':>4} {'-':>4} {'-':>4} {'-':>4} {'-':>5}"
        note = "FALLBACK" if r["is_fallback"] else ""
        if r.get("error"):
            note = (note + " " + r["error"]).strip()
        print(f"{row}  {note}")

    print("\n--- 전체 요약 ---")
    print(f"케이스 수            : {summary['case_count']}")
    print(f"규칙 통과율 평균     : {summary['avg_rule_pass_rate']}%")
    print(f"judge relevance 평균 : {summary['avg_relevance']}")
    print(f"judge actionability  : {summary['avg_actionability']}")
    print(f"judge coverage 평균  : {summary['avg_coverage']}")
    print(f"judge ordering 평균  : {summary['avg_ordering']}")
    print(f"judge 전체 평균      : {summary['avg_judge_overall']}")
    print(f"fallback 발생 수     : {summary['fallback_count']}")
    print(f"judge 오류 케이스 수 : {summary['judge_error_count']}")


def main() -> int:
    # stdout을 UTF-8로 재설정 (Windows 콘솔 한글 깨짐 완화, 가능한 경우에만)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not UPSTAGE_API_KEY:
        print("UPSTAGE_API_KEY가 설정되어 있지 않습니다. .env 또는 환경변수에 키를 넣고 다시 실행하세요.")
        return 1

    cases = load_dataset()
    print(f"{len(cases)}개 케이스를 평가합니다 (케이스당 생성 1회 + judge 1회, 실제 LLM 호출).")

    records = [evaluate_case(case) for case in cases]
    summary = aggregate(records)

    # 케이스별 상세를 results.jsonl로 기록하고, 마지막 줄에 summary를 남긴다.
    with RESULTS_PATH.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.write(json.dumps({"type": "summary", **summary}, ensure_ascii=False) + "\n")

    print_report(records, summary)
    print(f"\n상세 결과 저장: {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
