# CONTEXT

이 문서는 현재 시점의 일시적인 프로젝트 상태와 작업 맥락을 기록합니다.

## 현재 구현 상태

현재 저장소는 초기 스켈레톤 단계입니다.

- 실제 React/Vite 앱 구현은 아직 없습니다.
- 실제 Fastify 서버 구현은 아직 없습니다.
- 실제 Prisma schema와 migration은 아직 없습니다.
- 실제 LangGraph workflow는 아직 없습니다.
- 실제 Google Calendar / Google Tasks 연동은 아직 없습니다.
- 실제 Slack 연동은 아직 없습니다.
- 각 app/package의 `test`, `lint`, `typecheck`, `format:check` script는 placeholder입니다.

## 현재 구조 관련 결정

- 범용 `packages/shared` 패키지는 두지 않습니다.
- 공통 코드가 필요해지기 전까지는 더 구체적인 패키지에 코드를 배치합니다.
  - Google 관련: `packages/google`
  - Slack 관련: `packages/slack`
  - Agent prompt/schema/fixture: `packages/agent`
  - 알림 도메인: `packages/notification`
  - DB 접근: `packages/db`
  - 환경 설정: `packages/config`

## 리뷰 시 주의할 점

- 현재 변경은 프로젝트 스켈레톤 생성이 중심입니다.
- 실제 기능 구현은 별도 변경으로 분리하는 것이 좋습니다.
- `README.md`, `AGENTS.md`, `docs/*`는 프로젝트 방향을 설명하기 위한 초기 문서입니다.
