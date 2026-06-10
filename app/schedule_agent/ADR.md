# ADR-001: 일정 에이전트 LangGraph 노드 분리와 질문 처리 방식

## Status
Accepted

## Context
일정 서브태스크 생성은 분류, 추가 질문, 사전 검증, 계획 생성, 사후 검증, 최종 응답 단계가 필요합니다. 단일 LLM 호출로 처리하면 실패 지점과 재시도 조건을 분리하기 어렵습니다.

## Decision
- LangGraph를 사용해 각 단계를 별도 노드로 분리한다.
- 추가 질문은 v1에서 interrupt/checkpointer 대신 `status="needs_question"` 응답으로 처리한다.
- 일정 시간 입력은 단일 `time` 또는 마감일이 아니라 `start_time`/`end_time` 범위로 받는다.
- 서버 상태 저장이 없는 v1에서는 `classification_retry`, `pre_validation_retry`, `plan_retry`, `detail_with_context`, `question`, `question_source`, `context_answer`를 요청/응답으로 전달해 LangGraph 상태를 이어간다.
- 캘린더/DB 연동 전에는 `existing_schedules`를 요청으로 받아 기존 일정 충돌과 위치 이동 가능성 검증을 실험한다.
- DB 저장은 에이전트 노드가 아니라 API 또는 서비스 레이어에서 처리한다.
- 스트리밍 API는 `stream_mode=["updates", "values"]`로 그래프를 한 번만 실행한다. `updates`는 노드 진행 이벤트에, 마지막 `values`는 최종 응답에 사용한다.
- 노드의 실제 LLM 성능 평가는 그래프 전체 테스트와 분리하고, 평가 대상 노드를 직접 호출한다.
- `pre_validate`는 운영 환경에서 LLM 호출 또는 구조화 출력 오류가 발생하면 invalid로 처리하고, 평가에서는 `strict=True`로 오류를 별도 집계한다.
- ISO 8601로 해석 가능한 시간 순서와 기존 일정 충돌은 LLM 호출 전에 코드로 결정적으로 검증한다.
- 요청 일정과 기존 일정에 위치가 명시된 경우, LLM은 일정 사이 이동 시간이 명백히 부족한지도 검증한다.
- 위치 이동 검증에 필요한 장소 제약이 불명확하면 `pre_validate`도 기존 질문 흐름을 사용한다.
- 분류 질문과 사전 검증 질문은 `question_source`, `classification_retry`, `pre_validation_retry`로 의미와 재시도 횟수를 분리한다.
- 분류 노드는 `is_decomposable`로 하위 task 분해 필요성을 판단한다. 분해 불필요 일정은 추가 질문하지 않지만 일정 유효성 검증은 거치며, 유효하면 `tasks=[]`인 성공 응답으로 종료한다.
- `context_answer`가 있는 후속 요청은 먼저 `ask_context`에서 답변을 `detail_with_context`에 누적한 뒤, 질문 출처에 따라 분류 또는 사전 검증 노드로 재진입한다.
- MVP 단계의 임시 fix로, 분류 질문 답변이 적용된 상태는 내부 플래그로 표시하고 분류가 완료되면 다시 사전 검증을 거쳐 최신 `normalized_schedule`을 만든 뒤 계획 단계로 이동한다. 현재 `pre_validate`가 유효성 검증과 계획 입력 정규화를 함께 담당하기 때문에 필요한 우회이며, 장기적으로는 `normalized_schedule` 생성을 별도 normalize/prepare 노드로 분리한다.

## Consequences
- 각 단계의 책임과 테스트 지점이 명확해진다.
- 재시도 분기를 LangGraph에서 표현할 수 있다.
- v1에서는 대화 상태를 API 요청/응답으로 이어받아야 한다.
- 정식 API/DB 연동 단계에서는 retry count와 누적 컨텍스트를 클라이언트 입력이 아니라 run/session 저장소에서 관리하도록 재설계해야 한다.
- 정식 캘린더/DB 연동 단계에서는 기존 일정을 클라이언트 입력이 아니라 서버 조회 결과로 구성하며, 시간 충돌뿐 아니라 요청 전후 위치 이동 검증에 필요한 일정도 포함해야 한다.
- 장기 대화 상태가 필요해지면 LangGraph checkpointer 도입을 다시 검토한다.
- 스트리밍 중계 결과와 최종 응답은 동일한 그래프 실행에서 생성되며, LLM 호출 비용과 지연이 중복되지 않는다.
- 합성·익명화 평가 케이스와 평가 코드는 저장소에서 공유하고, 실행 결과 파일은 로컬 산출물로 관리한다.
- 결정적으로 판단 가능한 시간 규칙은 모델 변동과 관계없이 동일한 결과를 반환한다.
- 위치가 없거나 이동 가능 여부가 불명확한 일정은 위치 정보만으로 거절하지 않는다.
- 검증 모델 오류가 발생한 일정은 계획 단계로 통과하지 않는다.
- 질문 출처별 재시도 횟수가 섞이지 않아 한 노드의 질문이 다른 노드의 질문 기회를 소모하지 않는다.
- 분해 불필요 일정은 실패가 아니므로 fallback이 아니라 정상 응답으로 표현된다.
- 분류 질문 답변 후에도 계획 노드는 빈 `normalized_schedule`이 아니라 최신 답변이 반영된 일정 컨텍스트를 받는다.
- 이 결정은 MVP 안정화를 위한 임시 결정이며, 최종 구조에서는 `pre_validate`를 재호출하지 않고 정규화 책임을 별도 노드로 옮기는 편이 더 적절하다.
