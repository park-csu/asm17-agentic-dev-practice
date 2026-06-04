# evals/plan 패키지 컨텍스트

`evals/plan`은 일정 에이전트의 **plan 노드(`plan_tasks`)가 LLM으로 생성한 task 분해 결과의 품질**을 데이터셋 위에서 측정하는 평가 패키지입니다.

## test와의 역할 구분

- 단위 테스트([tests/plan/test_plan.py](../../tests/plan/test_plan.py))는 LLM을 mock으로 대체해 **결정적 로직**(fallback 경로, `plan_retry` 누적, 반환 dict 구조)만 검증합니다. 통과/실패 이분법입니다.
- 이 eval은 **실제 LLM을 호출**해 생성된 task의 품질(관련성·실행 구체성·포괄성·순서 타당성)을 점수로 측정합니다. 출력이 비결정적이므로 통과/실패가 아니라 **점수 지표**로 판단합니다.

자세한 배경은 [app/schedule_agent/nodes/plan.py](../../app/schedule_agent/nodes/plan.py)와 [PlanResult 스키마](../../app/schedule_agent/schemas.py)를 참고하세요.

## 구성

- `dataset.jsonl`: 평가 케이스. 각 줄은 `plan_tasks`의 입력인 `normalized_schedule`을 그대로 담습니다(노드 입력과 1:1). `notes`는 사람이 읽는 기대치 메모이며 채점에는 직접 쓰지 않습니다.
  - **거부 후 교정(재생성) 케이스**: `invalid_reason`(post_validate 거부 사유)과 `rejected_tasks`(거부된 직전 task)를 추가로 담습니다. 이 두 필드가 있으면 `run_eval`이 `plan_tasks` 입력 state에 `invalid_reason` / `tasks` / `plan_retry=1`을 넣어, 운영 그래프가 post_validate 거부 후 plan에 재진입하는 상황을 모사합니다.
- `run_eval.py`: 데이터셋을 읽어 `plan_tasks`를 실제로 실행하고, 규칙 기반 채점과 LLM-as-judge 채점을 합산해 리포트합니다.
- `results.jsonl`: 실행 산출물. 케이스별 상세 + 마지막 줄에 전체 summary가 기록됩니다(.gitignore 대상).

## 채점 방식

1. **규칙 기반(결정적, LLM 불필요)**: task 개수 1~5, `order_index` 1..n 연속, `estimated_minutes` 양의 정수, 제목 중복 없음, 빈 제목 없음.
2. **LLM-as-judge(주관 품질)**: `relevance / actionability / coverage / ordering` 각 1~5점 + 근거. `get_llm().with_structured_output()` 패턴을 그대로 재사용합니다.
3. **교정 judge(재생성 케이스 한정)**: `invalid_reason`이 있는 케이스에 대해서만 추가 호출됩니다. `resolves_reason`(거부 사유 해소 정도) / `avoids_repeat`(거부된 task 반복 회피 정도)를 각 1~5점으로 채점해, `plan_tasks`가 거부 사유를 반영해 제대로 교정했는지를 측정합니다.

## 실행

```powershell
uv run python -m evals.plan.run_eval
```

`.env`의 `UPSTAGE_API_KEY`로 실제 Upstage(solar-pro2)를 호출하므로 **비용과 지연이 발생**합니다. 키가 없으면 안내 후 종료합니다.

## 범위 밖

저장소 연동, 프론트엔드, 그래프 전체 흐름 평가는 이 패키지의 책임이 아닙니다. 다른 노드의 eval이 필요해지면 `evals/<노드명>/` 형태로 같은 구조를 따릅니다.
