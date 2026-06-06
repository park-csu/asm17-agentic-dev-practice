# ADR-001: backend 패키지 분리 및 PostgreSQL 연동 설계

## Status
Accepted

## Context
에이전트 구현(`app/schedule_agent`)과 API 서버/DB 레이어를 같은 `app/` 패키지 안에 두면 책임 경계가 모호해진다. 프론트엔드가 아직 없는 상태에서 백엔드 API를 별도 패키지로 분리하고, 결과를 PostgreSQL에 저장하는 구조가 필요하다.

## Decision

**패키지 분리**
- `backend/`를 신설해 FastAPI 진입점, DB 모델, CRUD API를 소유한다.
- `app/schedule_agent`는 순수 에이전트 로직만 소유하고, `backend`가 이를 임포트해 실행한다.
- 임포트 방향은 단방향(`backend` → `app`)으로 고정한다. 에이전트가 `backend`를 임포트하지 않는다.

**ORM: SQLModel**
- FastAPI + Pydantic 기반 프로젝트이므로 SQLModel을 선택한다.
- DB 모델과 Pydantic 스키마를 하나의 클래스로 표현해 보일러플레이트를 최소화한다.
- 마이그레이션은 Alembic으로 관리한다.

**DB 스키마**
- `users`: 향후 Google OAuth2 연동을 위해 미리 생성. `user_id`는 nullable로 두어 인증 없이도 일정 저장 가능.
- `schedules`: 일정 입력값과 에이전트 결과 상태(`status`, `fallback_reason`, `is_decomposable`) 저장.
- `tasks`: 에이전트가 생성한 서브태스크. `is_done`으로 완료 여부 추적.

**existing_schedules 주입 방식**
- 기존 프로토타입에서 클라이언트가 `existing_schedules`를 직접 넘기던 방식을 제거한다.
- 서버가 DB에서 `start_time`/`end_time` 겹치는 `status=ok` 일정만 조회해 에이전트에 주입한다.

**SSE 저장 타이밍**
- `done` 이벤트 전에 DB 저장을 완료한다.
- 클라이언트는 `done` 이벤트에서 `schedule_id`를 받아 즉시 상세 조회(`GET /schedules/{id}`) 가능.

**인증: Supabase Auth + Google OAuth**
- 프론트엔드에서 Supabase Auth로 Google OAuth 로그인 후 JWT 발급.
- 백엔드는 JWT를 `PyJWT` + JWKS(`/auth/v1/.well-known/jwks.json`)로 검증한다.
- HS256/RS256 모두 지원하며, Supabase 키 교체 시 자동으로 갱신된다.
- JWT의 `sub` 클레임을 `user_id`로 사용해 일정 데이터를 사용자별로 격리한다.
- `SUPABASE_JWT_SECRET`(HS256 직접 검증) 방식 대신 JWKS 방식을 채택해 키 관리 부담을 없앤다.

**배포**
- FastAPI: Railway (`railway.toml` + `Dockerfile.api`)
- PostgreSQL: Supabase (Session pooler, `postgresql+asyncpg://`)
- 프론트엔드: Vercel (별도 배포)

## Consequences
- 에이전트와 API 레이어의 책임이 명확히 분리된다.
- `backend`에서 `app/schedule_agent`를 임포트하므로 Docker 이미지에 두 패키지 모두 포함해야 한다.
- `existing_schedules` 클라이언트 입력이 제거되어 API 계약이 단순해진다.
- Supabase Session pooler 사용 시 `asyncpg`는 `postgresql+asyncpg://` 연결 문자열을 사용한다.
- JWKS 방식으로 JWT 검증하므로 Railway 환경변수에 `SUPABASE_URL`만 추가하면 된다.
- 모든 일정 엔드포인트는 `user_id` 기반으로 데이터를 격리하므로 다른 사용자의 데이터에 접근할 수 없다.
