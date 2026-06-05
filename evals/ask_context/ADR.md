# ADR-001: ask_context 상태 전이 평가 방식

## Status
Accepted

## Context
ask_context 노드는 LLM 호출 없이 추가 질문을 반환하거나 사용자 답변을 `detail_with_context`에 누적합니다. 기능 자체는 단위 테스트로 검증할 수 있지만, evals 아래에 공유 케이스를 두면 API 상태 전달 규칙 변경 시 classification/pre_validate 후속 답변 흐름을 함께 점검할 수 있습니다.

## Decision
- `ask_context`를 직접 호출하는 결정적 평가를 그래프 테스트와 분리한다.
- 합성·익명화된 JSONL 케이스로 답변 누적, 질문 반환, retry 증가 대상, 불필요한 retry 미반환을 평가한다.
- 평가 코드와 케이스는 커밋하고 `results` 디렉터리의 실행 결과는 커밋하지 않는다.
- LLM 호출이 없으므로 기본 반복 횟수는 1회로 둔다.

## Consequences
- 질문 상태 필드가 바뀌어도 공유 케이스로 상태 전이 규칙을 빠르게 확인할 수 있다.
- 실제 LLM 비용 없이 실행할 수 있다.
- LLM 품질 평가는 아니므로 classification/pre_validate 평가와 목적을 구분해야 한다.
