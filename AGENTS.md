# AGENTS.md

This project is a Agentic Workflow demo service.
It reads Google Calendar events, uses a LangGraph Agent to decompose events into executable Tasks, asks Slack clarification questions when the event is ambiguous, then creates Google Tasks after the Slack answer.

## Project Overview

```txt
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

- Frontend: React, Vite, TypeScript
- Backend: Node.js, Fastify, Zod, Prisma
- Agentic capability: LangGraphTS, Vitest
- Keep changes small, focused, and easy to review.
- Prefer clear, maintainable code over clever abstractions.

## General Instructions

- Read relevant files before making changes.
- Do not introduce new dependencies unless necessary.
- If adding a dependency, explain why it is needed and use `pnpm` for JavaScript/TypeScript or `uv` for Python.
- Avoid unrelated refactors while completing a task.
- Keep user-facing behavior stable unless explicitly asked to change it.
- Do not expose secrets, API keys, tokens, or sensitive data in client-side code or logs.

## Language and Communication

- Respond to user questions in Korean.
- Write comments, pull requests, commit messages, and docs in Korean.
- Use English for code identifiers such as variable names, function names, class names, and file names.

## GitHub Workflow

- Never commit directly to main branches such as `main`, `master`, or `develop`.
- Create a feature branch before making changes. Use short, descriptive branch names such as `feat/calendar-sync` or `fix/slack-clarification`.
- Keep commits small and focused on one logical change.
- Write clear commit messages that explain the user-facing or technical intent of the change.
- Use a consistent commit prefix strategy:
  - `feat`: user-facing feature or capability
  - `fix`: bug fix or incorrect behavior correction
  - `docs`: documentation-only change
  - `test`: test additions or test-only changes
  - `refactor`: internal code restructuring without behavior change
  - `chore`: tooling, configuration, repository maintenance, or skeleton changes
  - `ci`: CI/CD workflow changes
  - `build`: build system or dependency changes
- Prefer the format `<prefix>: <short Korean summary>`, for example `docs: 아키텍처 문서 추가`.
- Open a pull request for review before merging into a protected branch.
- In pull requests, summarize what changed, why it changed, and how it was tested.
- Link related issues, tickets, or docs when applicable.
- Ensure relevant tests, lint, typecheck, and format checks pass before requesting review when practical.
- Do not commit secrets, generated artifacts, dependency folders, local environment files, or unrelated formatting churn.
- Do not rewrite shared branch history or force-push without explicit team agreement.

## Repository Conventions

Use this structure unless the project already has a different established layout:

```
.
├─ apps/
│  ├─ web/
│  ├─ api/
│  ├─ worker-calendar/
│  ├─ worker-agent/
│  └─ worker-notification/
│
├─ packages/
│  ├─ db/
│  ├─ config/
│  ├─ google/
│  ├─ slack/
│  ├─ agent/
│  │  └─ src/
│  │     ├─ prompts/
│  │     ├─ schemas/
│  │     ├─ fixtures/
│  │     └─ evals/
│  └─ notification/
│
├─ docs/
│
├─ scripts/
├─ docker-compose.yml
├─ pnpm-workspace.yaml
├─ package.json
├─ .env.example
├─ README.md
└─ AGENTS.md
```

## Coding Conventions

### TypeScript

- Use TypeScript for application code and keep types explicit at module boundaries.
- Prefer type inference inside functions, but define clear types for public APIs, DTOs, graph state, and package exports.
- Avoid `any`; use `unknown`, generics, discriminated unions, or validated schemas instead.
- Keep functions small and focused, with descriptive names that explain intent.
- Use `camelCase` for variables and functions, `PascalCase` for classes, types, interfaces, and React components, and `SCREAMING_SNAKE_CASE` for constants that are truly constant.
- Prefer named exports for reusable modules and keep imports organized by standard library, external packages, then local modules.
- Handle async errors explicitly and avoid unhandled promises.
- Validate external input at boundaries with Zod or established project schemas.
- Keep formatting consistent with the repository formatter and avoid unrelated style-only churn.

### Frontend: React

- Use functional components and hooks.
- Name components with `PascalCase` and hooks with `useCamelCase`.
- Keep components focused; extract reusable UI and logic when it improves readability.
- Handle loading, empty, and error states explicitly.
- Use semantic, accessible HTML and label interactive controls correctly.
- Avoid direct DOM manipulation unless there is a clear need.
- Keep API calls in a small client/service layer rather than scattering fetch logic through components.

### Backend: Fastify

- Keep route handlers thin; put business logic in service modules.
- Use Zod schemas for request validation and response contracts where practical.
- Register Fastify plugins for shared concerns such as auth, database access, configuration, and external clients.
- Return appropriate HTTP status codes and structured error responses for expected API errors.
- Avoid returning raw internal models when a response shape is more appropriate.
- Keep settings in environment variables and configuration modules; never hard-code secrets.
- Prefer async handlers when the code path performs I/O or uses async-compatible libraries.

### Agentic Workflows: LangGraphTS

- Use LangGraphTS for agentic workflows in the Node.js/TypeScript runtime.
- Keep graph state explicit and typed with TypeScript types, LangGraph annotations, and Zod schemas where appropriate.
- Separate graph construction from runtime invocation so graphs can be tested independently.
- Keep nodes small and focused on one responsibility.
- Put external side effects behind tools or service functions so they can be mocked in tests.
- Keep prompts versioned in code and review prompt changes like application logic.
- Use clear names for nodes, edges, conditional branches, tools, and state fields.
- Validate and sanitize user-provided inputs before passing them into tools or model calls.
- Do not log sensitive prompts, credentials, private user data, or raw model responses unless explicitly safe.
- Prefer deterministic logic outside of the LLM when rules can be implemented directly.
- Add recursion limits, timeouts, or safeguards for workflows that may loop or call tools repeatedly.
- Keep model/provider settings configurable through TypeScript configuration modules and environment variables.

Suggested layout:

```text
apps/worker-agent/
  src/
    agents/
      state.ts       # graph state definitions
      graphs/        # graph assembly and compiled graphs
      nodes/         # node functions
      tools/         # tool definitions and adapters
    services/        # worker orchestration and integration code
    config/          # worker configuration from environment variables
  tests/             # Vitest tests for worker and graph behavior

packages/agent/
  src/
    prompts/         # reusable prompt templates shared by agent code
    schemas/         # shared Zod schemas and TypeScript types for graph inputs and outputs
    fixtures/        # reusable test and eval fixtures
    evals/           # LangGraphTS evaluations and regression helpers
```

## Testing Conventions

### Frontend Tests

- Prefer Vitest with React Testing Library for React component and hook tests.
- Test behavior from the user perspective rather than implementation details.
- Place tests next to the code as `*.test.ts(x)` or in a `__tests__/` folder, following the existing project convention.
- Mock network calls at the API-client boundary where practical.
- Cover loading, success, empty, and error states for data-driven UI.

Recommended checks when available:

```bash
pnpm test
pnpm lint
pnpm typecheck
pnpm format:check
```

Use `pnpm` for JavaScript and TypeScript package management and command execution.

### Backend Tests

- Prefer the existing Node.js test runner for Fastify backend tests, such as Vitest or Jest, following the package scripts already defined in the repo.
- Use Fastify's built-in `inject` testing API or the established HTTP test helper for API route tests.
- Place tests next to the code as `*.test.ts` or under each app/package test folder, following the existing project convention.
- Test API status codes, response bodies, Zod validation errors, and important service behavior.
- Mock database access, network calls, and other external integrations by default.
- Use fixtures for app instances, Prisma/database clients, reusable test data, and fake external services.
- Prefer deterministic tests that do not require live external services.

Recommended checks when available:

```bash
pnpm test
pnpm lint
pnpm typecheck
pnpm format:check
```

Use `pnpm` for JavaScript and TypeScript package management and command execution.

### LangGraphTS Tests

- Prefer Vitest for LangGraphTS tests, following the package scripts already defined in the repo.
- Place tests next to the agent code as `*.test.ts` or under each app/package test folder, following the existing project convention.
- Test LangGraph node functions, conditional routing, state updates, and graph-level happy/error paths.
- Mock LLM calls, tools, network calls, and other external integrations by default.
- Use fixtures for reusable test data, fake LLMs, fake tools, and graph inputs.
- Prefer deterministic tests that do not require live model providers or external services.

Recommended checks when available:

```bash
pnpm test
pnpm lint
pnpm typecheck
pnpm format:check
```

Use `pnpm` for LangGraphTS package management and command execution.

## Quality Before Finishing

- Run relevant checks before finishing when practical:
  - frontend tests/lint/typecheck
  - backend and LangGraphTS tests/lint/typecheck
  - formatting checks
- Add or update tests for meaningful behavior changes.
- If checks cannot be run, mention why.

## Git and Files

- Do not overwrite user changes without permission.
- Do not commit changes unless explicitly asked.
- Keep generated files, build artifacts, virtual environments, dependency folders, and secrets out of version control.

## Communication

- Summarize what changed and where.
- Mention any checks run and their results.
- Call out assumptions, tradeoffs, or follow-up work when relevant.
