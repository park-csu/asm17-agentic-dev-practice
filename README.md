# asm17-agentic-dev-practice

Google Calendar 이벤트를 읽고 LangGraph Agent로 실행 가능한 작업을 생성하는 로컬 Agentic Workflow 데모 서비스입니다.

## 개요

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

## 기술 스택

- Frontend: React, Vite, TypeScript
- Backend: Node.js, Fastify, Zod, Prisma
- Agentic Workflow: LangGraphTS
- Tests: Vitest
- Package Manager: pnpm

## 구조

```text
apps/
  web/
  api/
  worker-calendar/
  worker-agent/
  worker-notification/
packages/
  db/
  config/
  google/
  slack/
  agent/
  notification/
docs/
scripts/
```

## 시작하기

```bash
pnpm install
cp .env.example .env
docker compose up -d
```

현재는 프로젝트 스켈레톤 단계이며, 각 앱과 패키지의 실제 구현은 앞으로 추가될 예정입니다.

## 확인 명령

```bash
pnpm test
pnpm lint
pnpm typecheck
pnpm format:check
```

현재 위 명령들은 placeholder 스크립트를 실행합니다.
