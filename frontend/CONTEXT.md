# frontend 패키지 컨텍스트

`frontend`는 TaskPilot 캘린더 앱 UI를 담당하는 React + Vite + TypeScript 패키지입니다.

현재 목표는 백엔드 API 계약을 변경하지 않고, 실제 저장된 일정 CRUD와 SSE 기반 task 생성/재생성 흐름을 사용하는 프론트엔드 앱 셸을 구현하는 것입니다.

## 책임

- Supabase Auth Google OAuth로 로그인하고 access token을 보관한다.
- 일정 API 요청에는 `Authorization: Bearer <access_token>` 헤더를 포함한다.
- 저장된 일정 목록을 `GET /api/v1/schedules`로 조회한다.
- 새 일정 추가 시 `POST /api/v1/schedules/stream`을 호출해 일정 저장과 task 생성을 동시에 실행한다.
- 기존 일정의 task 재생성은 `POST /api/v1/schedules/{id}/stream`을 사용한다.
- 일정 수정은 현재 API가 지원하는 `title`, `detail`, `location`만 저장한다.
- 일정 삭제는 세부정보 모달에서만 `DELETE /api/v1/schedules/{id}`로 수행한다.
- task 완료 여부는 `PATCH /api/v1/schedules/{id}/tasks/{task_id}`로 갱신한다.

## UI 방향

- 3열 앱 셸을 사용한다.
- 왼쪽은 일정 목록을 보여주며, 일정 항목 클릭은 선택만 수행한다.
- 왼쪽 일정 항목의 `수정`, `삭제` 액션으로 mock 상세 수정과 삭제를 수행한다.
- 가운데는 FullCalendar 기반 캘린더를 둔다.
- 오른쪽은 선택 일정 결과 패널이 아니라 날짜별 task 보드로 구성한다.
- `needs_question` 답변 폼은 선택된 일정에 이어가기 컨텍스트가 있을 때만 오른쪽 패널 상단에 표시한다.
- 모바일 또는 hover가 불안정한 환경에서는 이벤트 hover 팝오버를 비활성화한다.

## 현재 구현 단계

현재 프론트 UI는 실제 백엔드 API를 사용한다.

- 앱 진입 시 Supabase 세션을 확인하고, 로그인 전에는 일정 API를 호출하지 않는다.
- 앱 진입 시 `GET /api/v1/schedules`로 저장된 일정을 조회한다.
- 새 일정 추가는 `POST /api/v1/schedules/stream`을 호출하고, 완료 후 상세 조회로 저장된 상태와 task를 반영한다.
- 기존 일정 수정/삭제/task 재생성/task 완료 체크는 각각 백엔드 API를 호출한다.
- `src/calendar/mockData.ts`는 이전 UI 단계의 샘플 데이터로 남아 있으며 앱 진입 경로에서는 사용하지 않는다.
- UI 전용 타입과 모델 함수는 `src/calendar`가 소유한다.

## 선택 상태

초기 진입 시 선택 일정은 현재 브라우저 시간을 기준으로 정한다.

1. 진행 중인 일정 우선
2. 미래 일정 중 가장 가까운 일정
3. 후보가 없으면 가장 최근 과거 일정

일정 삭제 후에는 자동으로 다른 일정을 선택하지 않고 선택 없음 상태로 둔다.

## API 타입 경계

프론트 내부 일정 타입은 API 응답 타입과 분리한다.

- 인증 세션과 Supabase 클라이언트는 `src/auth/supabase.ts`가 소유한다.
- API 타입은 `src/api/types.ts`에서 백엔드 응답/요청 계약을 표현한다.
- UI 전용 타입은 이후 캘린더 구현에서 별도로 둔다.
- 현재 백엔드는 겹치는 기존 일정을 서버 DB에서 조회하므로, 프론트 요청 body에 `existing_schedules`를 포함하지 않는다.

## 인증 환경변수

프론트 로컬 실행에는 `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`가 필요하다. Docker Compose 실행 시에는 루트 `.env`의 `SUPABASE_URL`, `SUPABASE_ANON_KEY`를 프론트 컨테이너의 `VITE_*` 환경변수로 전달한다.

## 테스트

프론트 테스트는 Vitest를 사용한다.

기본 테스트는 실제 API 호출이 아니라 `fetch` mock으로 URL, method, body shape가 백엔드 계약과 맞는지 확인하는 요청 계약 단위 테스트다.

실제 백엔드 응답 확인은 `npm run test:api`로 분리한다. 이 테스트는 `VITE_API_BASE_URL`이 가리키는 실행 중인 API에 `GET` 요청만 보내며, 일정 생성/수정/삭제처럼 데이터를 변경하는 요청은 수행하지 않는다.
