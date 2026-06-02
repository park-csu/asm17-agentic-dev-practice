# ADR-001: 일정 에이전트 LangGraph 노드 분리와 질문 처리 방식

## Status
Accepted

## Context
일정 서브태스크 생성은 분류, 추가 질문, 사전 검증, 계획 생성, 사후 검증, 최종 응답 단계가 필요합니다. 단일 LLM 호출로 처리하면 실패 지점과 재시도 조건을 분리하기 어렵습니다.

## Decision
- LangGraph를 사용해 각 단계를 별도 노드로 분리한다.
- 추가 질문은 v1에서 interrupt/checkpointer 대신 `status="needs_question"` 응답으로 처리한다.
- 일정 시간 입력은 단일 `time` 또는 마감일이 아니라 `start_time`/`end_time` 범위로 받는다.
- 서버 상태 저장이 없는 v1에서는 `classification_retry`, `plan_retry`, `detail_with_context`, `context_answer`를 요청/응답으로 전달해 LangGraph 상태를 이어간다.
- 캘린더/DB 연동 전에는 `existing_schedules`를 요청으로 받아 기존 일정 충돌 검증을 실험한다.
- DB 저장은 에이전트 노드가 아니라 API 또는 서비스 레이어에서 처리한다.

## Consequences
- 각 단계의 책임과 테스트 지점이 명확해진다.
- 재시도 분기를 LangGraph에서 표현할 수 있다.
- v1에서는 대화 상태를 API 요청/응답으로 이어받아야 한다.
- 정식 API/DB 연동 단계에서는 retry count와 누적 컨텍스트를 클라이언트 입력이 아니라 run/session 저장소에서 관리하도록 재설계해야 한다.
- 정식 캘린더/DB 연동 단계에서는 기존 일정을 클라이언트 입력이 아니라 서버 조회 결과로 구성해야 한다.
- 장기 대화 상태가 필요해지면 LangGraph checkpointer 도입을 다시 검토한다.
