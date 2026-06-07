# app/schedule_agent 패키지 컨텍스트

`app/schedule_agent`는 일정 서브태스크 생성 기능을 담당하는 기능 단위 패키지입니다.

이 패키지는 LangGraph 워크플로우, 에이전트 상태/응답 스키마, LLM 프롬프트, 노드 함수를 함께 소유합니다.

## Language

**분해 가능 일정**:
여러 실행 단계로 나누는 것이 사용자에게 실질적인 계획 가치를 주는 일정입니다.
_Avoid_: 모든 일정, 단순 일정

**분해 불필요 일정**:
이미 하나의 단순 행동으로 충분해 하위 task 목록을 만들지 않는 일정입니다.
_Avoid_: 실패한 일정, invalid 일정

## Relationships

- **분해 가능 일정**은 유효성 검증을 거쳐 하나 이상의 task로 계획됩니다.
- **분해 불필요 일정**은 유효성 검증을 거친 뒤 task를 생성하지 않고 정상 응답으로 종료됩니다.

현재 범위:
- 일정이 좋은 task 목록으로 분해될 필요와 충분한 맥락이 있는지 판단
- 추가 질문 필요 상태 반환
- 일정 유효성 검증
- task 1~5개 생성
- task 품질 검증
- 성공 또는 실패 결과 반환

일정 시간은 단일 마감값이 아니라 `start_time`과 `end_time` 범위로 받습니다. 시간 파싱과 충돌 검증도 이 범위를 기준으로 판단합니다.

에이전트는 무상태로 동작한다. `classification_retry`, `pre_validation_retry`, `plan_retry`, `detail_with_context`, `question`, `question_source`, `context_answer`는 추가 질문과 재시도 흐름을 요청/응답으로 이어가기 위한 상태 전달 필드다. `backend`가 이 필드들을 조립해 에이전트에 전달하고, 응답을 클라이언트로 중계한다.

분류 질문과 사전 검증 질문은 `question_source`로 출처를 구분한다. 추가 질문에 대한 사용자 답변은 응답에서 받은 `question`, `question_source`, retry 값과 함께 다음 요청의 `context_answer`로 전달한다. 유효성 검증 노드는 `question_source="pre_validate"`일 때만 `context_answer`를 사전 검증 질문의 답변으로 해석한다.

분류 질문에 대한 답변은 `ask_context`에서 `detail_with_context`에 누적된 뒤, `classification`을 거쳐 다시 `pre_validate`로 이동한다. 이 재검증 단계는 최신 컨텍스트 기반 `normalized_schedule`을 갱신하기 위한 MVP 단계의 임시 fix다. 이후 `pre_validate`가 성공하면 같은 답변 경로에서는 `classification`으로 되돌아가지 않고 바로 `plan`으로 이동한다. 장기적으로는 `normalized_schedule` 생성 책임을 별도 normalize/prepare 노드로 분리한다.

`existing_schedules`는 `backend`가 DB에서 시간 겹치는 일정을 조회해 주입한다. 에이전트는 클라이언트로부터 직접 받지 않는다.

`location`과 `existing_schedules`의 위치 정보는 일정 사이 이동 가능성을 검증하기 위한 입력이다. 위치가 명시되지 않았거나 이동 가능 여부가 불명확하면 위치만으로 일정을 거절하지 않는다.

위치가 지정된 작업이 실제 현장 도착을 요구하는지 불명확하면 `pre_validate`는 즉시 실패시키지 않고 사용자에게 확인 질문을 반환한다.

저장, 프론트엔드, 인증, 캘린더 연동은 이 패키지의 책임이 아니다.
