# 프로젝트 컨텍스트 맵

## 현재 목표
- TaskPilot의 일정 서브태스크 생성 에이전트 MVP를 구현한다.
- 백엔드와 에이전트는 Python + FastAPI + LangGraph 기반으로 계속 개발한다.
- 이번 단계의 핵심 범위는 에이전트 구현과 API 실행이며, 정식 프론트엔드와 PostgreSQL 저장은 이후 단계에서 개발한다.

## 주요 패키지
- `app`: FastAPI 앱 진입점, API 라우터, LangGraph 생성 지점이 있는 백엔드 패키지.
- `app/schedule_agent`: 일정 서브태스크 생성 기능 패키지. LangGraph, 노드, 스키마, 프롬프트를 함께 소유한다.
- `app/schedule_memory`: 현재 핵심 실행 경로에서는 사용하지 않는 ChromaDB 기반 유사 일정 검색 확장 후보 패키지. 별도 `CONTEXT.md`와 `ADR.md`를 가진다.
- `app/core`: LLM, 설정 같은 공통 기반 기능 패키지.
- `evals`: 실제 LLM을 사용하는 노드별 성능 평가 코드와 합성·익명화 평가 케이스를 관리한다. 실행 결과는 로컬 산출물로 저장한다.

## 문서 읽는 순서
1. `CONTEXT-MAP.md`
2. 작업 대상 패키지의 `CONTEXT.md`
3. 작업 대상 패키지의 `ADR.md`가 있으면 확인
4. 실제 코드
