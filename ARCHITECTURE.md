# ARCHITECTURE

이 문서는 AI Agent가 프로젝트 구조와 코드 배치 기준을 빠르게 이해하기 위한 안내서입니다.

## 프로젝트 목적

이 프로젝트는 Google Calendar 이벤트를 읽고, LangGraph Agent로 이벤트를 분석해 실행 가능한 Task를 만드는 로컬 Agentic Workflow 데모 서비스입니다.

기본 흐름은 다음과 같습니다.

```text
Google Login
→ Google Calendar Sync
→ Calendar Event 저장
→ LangGraph Agent 분석
→ 명확하면 Task 자동 생성
→ 애매하면 Slack clarification 질문
→ Slack 답변 수신
→ Agent 재실행
→ Task 생성
→ Slack Daily Digest / Done Action
```

## Monorepo 구조

```text
apps/        # 실행 가능한 애플리케이션과 워커
packages/    # 앱 간에 공유되는 도메인/인프라 패키지
docs/        # 제품, 아키텍처, API, 운영 문서
scripts/     # 개발/운영 보조 스크립트
```

## Apps

### `apps/web`

React, Vite, TypeScript 기반 프론트엔드 앱입니다.

예상 책임:

- 사용자 로그인/설정 화면
- Calendar 이벤트와 생성된 Task 상태 표시
- Slack clarification 상태 표시
- `apps/api` 호출

프론트엔드 전용 UI, hook, API client 코드는 이 앱 안에 둡니다.

### `apps/api`

Fastify 기반 HTTP API 서버입니다.

예상 책임:

- Web frontend용 API 제공
- Google OAuth callback 처리
- Slack 또는 Google webhook endpoint 제공
- 요청 검증과 응답 변환
- DB, Google, Slack, Agent worker로 이어지는 얇은 orchestration

route handler는 얇게 유지하고, 복잡한 비즈니스 로직은 각 패키지나 service module로 분리합니다.

### `apps/worker-calendar`

Google Calendar 동기화 워커입니다.

예상 책임:

- Google Calendar 이벤트 조회
- 변경된 이벤트 정규화
- Calendar event 저장
- Agent worker 실행 트리거

Calendar API 직접 호출 로직은 가능하면 `packages/google`에 두고, 이 워커는 동기화 흐름 조율에 집중합니다.

### `apps/worker-agent`

LangGraphTS 기반 Agent workflow 실행 워커입니다.

예상 책임:

- Calendar event를 Agent 입력으로 변환
- 이벤트를 실행 가능한 Task로 분해
- 모호한 이벤트에 대해 Slack clarification 요청 생성
- Slack 답변 이후 Agent workflow 재실행
- Google Tasks 생성 요청

LangGraph graph, node, tool adapter, state 정의는 이 앱 안에서 명확히 분리합니다.

권장 구조:

```text
apps/worker-agent/src/
  agents/
    state.ts
    graphs/
    nodes/
    tools/
  services/
  config/
```

### `apps/worker-notification`

알림과 사용자 응답 처리를 담당하는 워커입니다.

예상 책임:

- Slack 메시지 전송
- Slack clarification 응답 수신 후 처리
- Daily digest 전송
- Done action 처리
- 알림 재시도와 상태 관리

Slack API 세부 호출은 `packages/slack`에 두고, 이 워커는 알림 workflow를 담당합니다.

## Packages

### `packages/db`

DB 접근 계층입니다.

예상 책임:

- Prisma schema와 client
- repository 또는 query helper
- migration 관련 코드

앱과 워커는 DB에 직접 접근하기보다 이 패키지를 통해 접근하는 것을 권장합니다.

### `packages/config`

환경 변수와 런타임 설정을 관리합니다.

예상 책임:

- `.env` 값 로딩
- 필수 환경 변수 검증
- 앱별 config export
- client/server 노출 설정 분리

민감한 값은 frontend로 노출하지 않습니다.

### `packages/google`

Google API 연동 어댑터입니다.

예상 책임:

- Google OAuth helper
- Google Calendar client
- Google Tasks client
- Google API 응답을 내부 DTO로 변환

Google API 호출 세부사항은 이 패키지에 격리합니다.

### `packages/slack`

Slack API 연동 어댑터입니다.

예상 책임:

- Slack 메시지 전송
- Slack event/payload 검증 helper
- Slack interaction payload parsing
- Slack 응답을 내부 DTO로 변환

Slack token이나 signing secret은 로그에 남기지 않습니다.

### `packages/agent`

Agent workflow에서 재사용되는 자산을 관리합니다.

현재 권장 구조:

```text
packages/agent/src/
  prompts/    # reusable prompt templates
  schemas/    # Agent 입출력 Zod schema와 타입
  fixtures/   # 테스트/eval fixture
  evals/      # Agent 평가와 회귀 테스트 보조 코드
```

Agent 실행 자체는 `apps/worker-agent`에 두고, 여러 위치에서 재사용되는 prompt/schema/fixture만 이 패키지에 둡니다.

### `packages/notification`

알림 도메인 로직입니다.

예상 책임:

- notification 상태 모델
- digest 구성 로직
- clarification message 생성 규칙
- notification retry 정책

Slack 호출 자체는 `packages/slack`에 두고, 알림 도메인 판단은 이 패키지에 둡니다.

## 코드 배치 원칙

- 특정 앱에서만 쓰는 코드는 해당 `apps/*` 안에 둡니다.
- 외부 서비스 API 호출 세부사항은 전용 패키지에 둡니다.
  - Google 관련: `packages/google`
  - Slack 관련: `packages/slack`
- DB 접근은 `packages/db`로 모읍니다.
- 환경 변수 접근은 `packages/config`로 모읍니다.
- Agent prompt/schema/fixture는 `packages/agent`에 둡니다.
- 범용 `shared` 패키지는 현재 두지 않습니다. 실제 중복이 생기기 전까지 더 구체적인 패키지에 배치합니다.

## 의존 방향

권장 의존 방향:

```text
apps/*
  → packages/config
  → packages/db
  → packages/google
  → packages/slack
  → packages/agent
  → packages/notification
```

주의사항:

- `packages/*`가 `apps/*`에 의존하지 않게 합니다.
- 패키지 간 순환 의존을 만들지 않습니다.
- 외부 API SDK 사용은 가능하면 adapter package 내부로 제한합니다.
- UI 코드는 `apps/web` 밖으로 빼지 않습니다.

새 기능을 추가할 때는 먼저 책임이 어느 앱/패키지에 속하는지 판단한 뒤, 작은 단위로 구현합니다.
