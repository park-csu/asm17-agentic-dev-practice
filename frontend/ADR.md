# frontend ADR

## ADR-001: 실제 백엔드 CRUD와 SSE를 사용한다

프론트는 로컬 상태만으로 일정을 관리하지 않고 `backend`의 저장된 일정 CRUD API를 사용한다.

이유:
- 사용자는 실제 CRUD 사용을 요구했다.
- 백엔드에는 일정 목록, 상세, 수정, 삭제, task 완료 API가 이미 존재한다.
- task 생성 결과와 저장된 일정 상태가 분리되면 새로고침 후 UI와 서버 상태가 어긋난다.

## ADR-002: 새 일정 추가는 즉시 stream 생성으로 처리한다

현재 백엔드에는 순수 일정 생성용 `POST /api/v1/schedules` 엔드포인트가 없다. 새 일정을 저장할 수 있는 API는 `POST /api/v1/schedules/stream`이며, 이 엔드포인트는 일정 저장과 에이전트 실행을 함께 수행한다.

결정:
- 새 일정 모달의 `일정 추가`는 `/api/v1/schedules/stream`을 호출한다.
- 모달은 제출 직후 닫고, UI에는 생성 중 상태를 표시한다.
- `done.status === "fallback"`은 서버에 저장된 일정이므로 목록에 유지하고 빨간색으로 강조한다.
- 네트워크 실패나 스트림 파싱 실패처럼 서버 저장 전 실패한 경우 임시 일정은 제거하고 오른쪽 위 알림으로 표시한다.

## ADR-003: 기존 일정 task 생성 버튼은 task 재생성으로 명명한다

기존 일정은 이미 서버에 저장되어 있으므로 task 생성 액션은 `POST /api/v1/schedules/{id}/stream`을 호출하는 재생성 동작이다.

결정:
- 버튼 라벨은 `task 재생성`으로 둔다.
- `ok`, `fallback`, 일반 대기 상태에서는 활성화한다.
- `needs_question`이고 현재 세션의 이어가기 컨텍스트가 있으면 오른쪽 clarification 폼으로만 이어간다.
- 새로고침 후처럼 이어가기 컨텍스트가 없으면 `task 재생성`을 활성화해 새 요청으로 회복할 수 있게 한다.

## ADR-004: 시간 수정은 읽기 전용으로 둔다

`PATCH /api/v1/schedules/{id}`는 현재 `title`, `detail`, `location`만 수정한다. 시작/종료 시간을 모달에서 수정 가능하게 보이면 저장 후 새로고침 시 시간이 되돌아가는 문제가 생긴다.

결정:
- 기존 일정 세부정보 모달의 시작/종료 시간은 읽기 전용이다.
- 시간 수정 지원은 백엔드 API 확장 후 활성화한다.

## ADR-005: task는 완료 체크만 지원한다

백엔드는 task 수정과 삭제 API를 제공하지만, 이번 프론트 1차 범위에서는 날짜별 task 확인과 완료 체크에 집중한다.

결정:
- task 완료 체크는 낙관적 업데이트로 반영한다.
- 실패 시 이전 `is_done` 값으로 롤백하고 오른쪽 위 알림을 표시한다.
- task 제목/설명 수정과 삭제는 이번 범위에서 제외한다.

## ADR-006: API 요청 계약 테스트를 우선하고 실제 API 조회 테스트는 분리한다

프론트에는 기존 테스트 인프라가 없었다. FullCalendar 렌더링 테스트는 불안정성과 설정 비용이 크므로, 초기 테스트는 API 클라이언트 요청 계약에 집중한다.

결정:
- Vitest를 사용한다.
- 기본 `npm test`는 실제 API 호출을 하지 않는다.
- `fetch`를 mock해 URL, method, headers, body shape를 검증한다.
- 실제 백엔드 응답 확인은 `npm run test:api`로 분리한다.
- 실제 API 테스트는 현재 비파괴 `GET` 요청만 검증한다.

## ADR-007: FullCalendar 앱 셸은 mock data로 먼저 구성한다

실제 CRUD/SSE 연결은 사용자 데이터 변경과 LLM 실행을 동반한다. MVP 화면 구조와 캘린더 상호작용을 먼저 안정화하기 위해, 첫 UI 구현은 mock data 기반으로 진행한다.

결정:
- FullCalendar를 캘린더 렌더링과 월/주/일/목록 전환의 기준으로 사용한다.
- `src/calendar/mockData.ts`에 일정과 task 샘플을 둔다.
- `src/calendar/model.ts`에 선택 일정 계산과 날짜별 task 그룹핑 로직을 둔다.
- 실제 API 연결은 다음 커밋에서 API 클라이언트를 주입하는 방식으로 진행한다.

## ADR-008: 일정 항목 액션 아이콘은 Font Awesome 웹폰트를 사용한다

왼쪽 일정 목록은 조밀한 업무 도구 UI로 유지한다. 텍스트 버튼은 항목 높이와 정보 밀도를 늘리므로, 수정/삭제 액션은 Font Awesome 아이콘으로 표현한다.

결정:
- React 아이콘 패키지를 앱 번들에 포함하지 않고 Font Awesome CSS 웹폰트를 로드한다.
- 일정 항목 클릭은 선택만 수행한다.
- 수정/삭제 아이콘은 캘린더 이벤트 클릭 팝오버 헤더에 배치한다 (ADR-011 참고).

## ADR-011: 수정·삭제·task 목록은 캘린더 이벤트 팝오버로 통합한다

왼쪽 사이드바에 있던 수정·삭제 버튼과 별도 패널의 task 목록을 하나의 팝오버로 통합한다.

이유:
- 사이드바에 수정/삭제를 두면 캘린더 이벤트와 동작 위치가 분리되어 직관성이 떨어진다.
- 팝오버는 클릭한 이벤트 옆에 바로 열려 컨텍스트가 명확하다.

결정:
- 캘린더 이벤트 클릭 시 이벤트 DOM 요소 오른쪽에 팝오버를 열어 제목, 시간, 위치, 수정/삭제 버튼, task 목록(체크박스 포함)을 표시한다.
- 팝오버 좌표는 `eventDidMount`에서 `data-schedule-id` 속성으로 DOM을 찾아 `getBoundingClientRect()`로 계산한다.
- task가 모두 완료된 경우 에이전트 진행 단계 목록 대신 task 체크박스 목록을 표시한다.

## ADR-012: 사이드바는 토글로 접을 수 있으며 기본값은 펼침이다

사이드바 없이 캘린더만 보면 레이아웃이 허전하지만, 항상 열려 있으면 캘린더 공간을 침범한다.

결정:
- `isSidebarOpen` 상태로 `.app-shell`의 CSS grid 첫 번째 컬럼을 `280px` ↔ `0px` 전환한다.
- `transition: grid-template-columns 0.22s ease`로 부드럽게 애니메이션한다.
- 토글 버튼은 박스 없이 `<<` / `>>` 텍스트 또는 아이콘만 표시한다.
- 사이드바 `+` 버튼은 Font Awesome `fa-solid fa-plus` 아이콘을 사용해 픽셀 정렬을 맞춘다.
- 탑바의 `+` 버튼은 디자인 일관성을 위해 제거한다.

## ADR-013: 캘린더는 자정부터 24시간 전체를 표시한다

기본 `slotMinTime="07:00:00"`은 새벽 일정을 숨긴다.

결정:
- `slotMinTime="00:00:00"`, `slotMaxTime="24:00:00"`으로 설정해 24시간 전체를 표시한다.

## ADR-009: 앱 상태는 서버 조회 결과를 기준으로 갱신한다

mock UI 단계 이후 실제 CRUD/SSE를 연결할 때, stream 응답의 `done` 이벤트만으로 화면 상태를 직접 조립하지 않는다. 백엔드는 stream 처리 중 일정 상태와 task를 DB에 저장하므로, 프론트는 완료 후 상세 조회를 다시 수행해 저장된 데이터를 기준으로 화면을 갱신한다.

결정:
- 초기 일정 목록은 `GET /api/v1/schedules` 응답을 UI 타입으로 변환한다.
- 새 일정 생성과 task 재생성은 SSE 완료 후 `GET /api/v1/schedules/{id}`를 호출한다.
- task 완료 체크는 낙관적으로 반영하되 실패하면 이전 체크 상태로 롤백한다.
- 새 일정 생성 중에는 모달을 닫고 사이드바/알림에 생성 중 상태를 표시한다.

## ADR-010: Supabase Google OAuth 세션으로 API 인증을 처리한다

백엔드 일정 API는 Supabase JWT를 검증하고 `sub`를 `user_id`로 사용한다. 프론트가 인증 없이 API를 호출하면 모든 일정 엔드포인트가 401을 반환한다.

결정:
- 프론트는 `@supabase/supabase-js`로 Google OAuth 로그인을 수행한다.
- 로그인 전에는 일정 API를 호출하지 않는다.
- Supabase 세션의 `access_token`을 모든 일정 CRUD/SSE 요청의 `Authorization: Bearer <token>` 헤더에 포함한다.
- Supabase 클라이언트 생성과 로그인/로그아웃 함수는 `src/auth/supabase.ts`가 소유한다.
- 로컬 Docker Compose는 루트 `.env`의 `SUPABASE_URL`, `SUPABASE_ANON_KEY`를 프론트 `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`로 전달한다.
