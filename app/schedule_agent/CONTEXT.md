# app/schedule_agent 패키지 컨텍스트

`app/schedule_agent`는 일정 서브태스크 생성 기능을 담당하는 기능 단위 패키지입니다.

이 패키지는 LangGraph 워크플로우, 에이전트 상태/응답 스키마, LLM 프롬프트, 노드 함수를 함께 소유합니다.

현재 범위:
- 일정 정보 충분성 판단
- 추가 질문 필요 상태 반환
- 일정 유효성 검증
- task 1~5개 생성
- task 품질 검증
- 성공 또는 실패 결과 반환

일정 시간은 단일 마감값이 아니라 `start_time`과 `end_time` 범위로 받습니다. 시간 파싱과 충돌 검증도 이 범위를 기준으로 판단합니다.

현재 API 요청 모델의 `classification_retry`, `pre_validation_retry`, `plan_retry`, `detail_with_context`, `context_answer`는 정식 외부 API 계약이 아니라 LangGraph 프로토타입의 상태 전달 필드입니다. 서버 상태 저장이 아직 없기 때문에 추가 질문과 재시도 흐름을 요청/응답으로 이어가기 위해 유지합니다.

분류 질문과 사전 검증 질문은 `question_source`로 출처를 구분합니다. 사전 검증 질문의 사용자 답변은 응답에서 받은 `pre_validation_question`, `pre_validation_retry`와 함께 다음 요청의 `context_answer`로 전달합니다.

`existing_schedules`는 캘린더/DB 연동 전 기존 일정 충돌 검증을 테스트하기 위한 임시 입력입니다. 정식 API에서는 클라이언트가 직접 넘기기보다 서버가 Google Calendar 또는 PostgreSQL 저장소에서 조회합니다.

`location`과 `existing_schedules`의 위치 정보는 일정 사이 이동 가능성을 검증하기 위한 입력입니다. 위치가 명시되지 않았거나 이동 가능 여부가 불명확하면 위치만으로 일정을 거절하지 않습니다.

위치가 지정된 작업이 실제 현장 도착을 요구하는지 불명확하면 `pre_validate`는 즉시 실패시키지 않고 사용자에게 확인 질문을 반환합니다.

정식 API와 PostgreSQL 저장소가 도입되면 retry count와 누적 컨텍스트는 run/session 저장소에서 관리하고, 클라이언트 요청은 일정 입력과 보충 답변 중심으로 단순화합니다.

저장, 프론트엔드, 인증, 캘린더 연동은 이 패키지의 책임이 아닙니다.
