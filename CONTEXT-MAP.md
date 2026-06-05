# 프로젝트 컨텍스트 맵

## 현재 목표
- TaskPilot의 일정 서브태스크 생성 에이전트를 구현하고, PostgreSQL 기반 REST API로 서빙한다.
- 백엔드와 에이전트는 Python + FastAPI + LangGraph 기반으로 계속 개발한다.
- 현재 단계: 에이전트 구현 + PostgreSQL API 서버 완료. 정식 프론트엔드, 인증, 캘린더 연동은 이후 단계.

## 주요 패키지
- `backend`: FastAPI 앱 진입점, REST API 라우터, DB 모델(SQLModel), CRUD 로직이 있는 API 서버 패키지. `CONTEXT.md`, `ADR.md`를 가진다.
- `app/schedule_agent`: 일정 서브태스크 생성 기능 패키지. LangGraph 워크플로우, 노드, 스키마, 프롬프트를 함께 소유한다. `CONTEXT.md`, `ADR.md`를 가진다.
- `app/schedule_memory`: 현재 핵심 실행 경로에서는 사용하지 않는 ChromaDB 기반 유사 일정 검색 확장 후보 패키지. 별도 `CONTEXT.md`와 `ADR.md`를 가진다.
- `app/core`: LLM, 설정 같은 에이전트 공통 기반 기능 패키지.
- `evals`: 실제 LLM을 사용하는 노드별 성능 평가 코드와 합성·익명화 평가 케이스를 관리한다. 실행 결과는 로컬 산출물로 저장한다.

## 패키지 의존 방향
```
backend → app/schedule_agent (에이전트 호출)
backend → backend/db (DB 저장)
app/schedule_agent → app/core (LLM)
```
`app/schedule_agent`는 `backend`를 임포트하지 않는다.

## 문서 읽는 순서
1. `CONTEXT-MAP.md`
2. 작업 대상 패키지의 `CONTEXT.md`
3. 작업 대상 패키지의 `ADR.md`가 있으면 확인
4. 실제 코드
