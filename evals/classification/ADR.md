# ADR-001: classification 실제 LLM 성능 평가 방식

## Status
Accepted

## Context
classification 노드는 일정이 하위 task로 분해할 가치가 있는지와 분해에 필요한 맥락이 충분한지를 판단합니다. 단위 테스트는 LLM을 mock하므로 실제 모델이 단일 행동 일정, 분해 가능한 일정, 추가 질문이 필요한 일정을 일관되게 구분하는지 측정할 수 없습니다.

## Decision
- `classify_schedule`을 직접 호출하는 실제 LLM 평가를 그래프 테스트와 분리한다.
- 합성·익명화된 JSONL 케이스로 `is_decomposable`, `needs_question`, `question_source`, 질문 키워드, 누적 컨텍스트 보존 여부를 평가한다.
- 기본 5회 반복 실행하며, 모든 케이스가 모든 반복에서 통과해야 안정적이라고 판단한다.
- 평가 코드와 케이스는 커밋하고 `results` 디렉터리의 실행 결과는 커밋하지 않는다.
- 초기에는 점수를 리포트만 하고 CI 게이트로 사용하지 않는다.

## Consequences
- classification 노드 담당자가 그래프 전체나 plan 품질과 독립적으로 분류 판단 품질을 확인할 수 있다.
- 실제 LLM 평가에는 API 키, 비용, 네트워크 연결이 필요하다.
- 모델 응답 변동 때문에 질문 문구는 완전 일치가 아니라 핵심 키워드 포함 여부로 평가한다.
