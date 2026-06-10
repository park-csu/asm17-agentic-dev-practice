# backend 패키지 컨텍스트

`backend`는 FastAPI 기반 REST API 서버 패키지입니다.

`app/schedule_agent`의 LangGraph 에이전트를 호출하고, 결과를 PostgreSQL(Supabase)에 저장하며, 클라이언트에 SSE 스트리밍으로 응답합니다.

## 구조

- `backend/main.py`: FastAPI 앱 진입점, CORS 미들웨어, lifespan(DB 초기화)
- `backend/core/config.py`: `DATABASE_URL`, `CORS_ORIGINS`, `SUPABASE_URL` 환경변수
- `backend/core/auth.py`: Supabase JWKS 기반 JWT 검증 미들웨어 (`get_current_user_id`)
- `backend/db/models.py`: SQLModel 테이블 정의 (`User`, `Schedule`, `Task`)
- `backend/db/session.py`: async 엔진, 세션 팩토리, `init_db`, `get_session`
- `backend/api/__init__.py`: 라우터 등록
- `backend/api/schedules.py`: 일정 CRUD + 스트리밍 엔드포인트

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/schedules/stream` | 일정 생성 + 에이전트 실행 (SSE) |
| `GET` | `/api/v1/schedules` | 일정 목록 조회 |
| `GET` | `/api/v1/schedules/{id}` | 일정 상세 조회 |
| `PATCH` | `/api/v1/schedules/{id}` | 일정 수정 |
| `DELETE` | `/api/v1/schedules/{id}` | 일정 삭제 |
| `PATCH` | `/api/v1/schedules/{id}/tasks/{task_id}` | 태스크 수정/완료 처리 |
| `DELETE` | `/api/v1/schedules/{id}/tasks/{task_id}` | 태스크 삭제 |
| `POST` | `/api/v1/schedules/{id}/stream` | 태스크 재생성 (SSE) |

## 주요 설계 결정

- `existing_schedules`는 클라이언트가 넘기지 않고, 서버가 DB에서 시간 충돌 또는 위치 이동 검증에 필요한 주변 일정을 직접 조회해 에이전트에 주입한다.
- SSE `done` 이벤트 전에 DB 저장을 완료하여 `schedule_id`를 즉시 반환한다.
- 에이전트 플로우는 `app/schedule_agent`가 소유하며, `backend`는 호출과 저장만 담당한다.
- 인증은 Supabase Auth + Google OAuth. 백엔드는 JWKS로 JWT를 검증하고 `user_id`로 데이터를 격리한다.
- 일정 생성 시 Supabase JWT의 `sub`에 해당하는 `users` row가 없으면 개발/초기 가입 흐름을 위해 placeholder 사용자 row를 생성한다.
- 캘린더 연동은 이 패키지의 현재 범위가 아니다.
