# TaskPilot

Agentic AI 기반 일정 실행 관리 서비스입니다.

사용자가 일정의 제목, 상세 내용, 시작 시간, 종료 시간을 입력하면 LangGraph 기반 에이전트가 실행 가능한 하위 작업으로 분해합니다.

이 저장소는 AI/SW Maestro 17기 Agentic Development 실습을 위한 TaskPilot 구현 저장소입니다.

## Features

- 일정 정보 충분성 판단
- 부족한 정보에 대한 추가 질문 생성
- 시작/종료 시간 기반 일정 검증
- 기존 일정과의 충돌 가능성 검토
- 실행 가능한 task 1~5개 생성
- 생성된 task 품질 검증

## Current Scope

현재 핵심 구현 범위는 일정 서브태스크 생성 에이전트와 이를 실행하기 위한 FastAPI API입니다. 백엔드와 에이전트 구현은 Python + FastAPI + LangGraph를 기준으로 계속 개발합니다.

현재 API와 요청/응답 모델은 에이전트 동작 검증을 위한 초기 인터페이스입니다. 정식 서비스 API 설계, 인증, 저장소 연동은 이후 단계에서 확정합니다.

React + Vite + TypeScript 프론트엔드는 API 테스트를 위한 초기 UI로 포함되어 있습니다. 정식 화면 설계, PostgreSQL 저장, 캘린더 연동, 인증은 이후 단계에서 개발할 예정입니다.

ChromaDB 기반 벡터 메모리 코드는 현재 핵심 실행 경로에서는 사용하지 않습니다. 향후 유사 일정 검색이나 개인화된 task 패턴 추천을 위한 확장 후보로 유지합니다.

협업과 확장 개발을 위해 `CHROMA_*` 환경변수와 Docker의 `chroma_data` 볼륨은 기본 설정에 포함되어 있습니다.

## Tech Stack

- Python 3.11+
- FastAPI
- Uvicorn
- React
- Vite
- TypeScript
- LangGraph
- LangChain Core
- Upstage Solar
- Pydantic
- uv

## Roadmap

- React + TypeScript 기반 정식 프론트엔드 개발
- PostgreSQL 기반 사용자, 일정, task, clarification 상태 저장
- Google OAuth2 로그인
- Google Calendar 일정 연동
- 유사 일정 검색과 개인화 task 패턴 추천 검토

## Quick Start

```bash
cp .env.example .env
```

`.env`에 API 키를 설정합니다.

```env
UPSTAGE_API_KEY=your_api_key
```

`CHROMA_*` 값은 현재 핵심 API 실행에는 필요하지 않지만, `app/schedule_memory` 확장 개발에서 ChromaDB 연결 방식을 지정할 때 사용합니다.

서버를 실행합니다.

```bash
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001
```

헬스 체크:

```bash
curl http://localhost:8001/health
```

로컬에서 FastAPI API만 실행하려면 다음 보조 스크립트를 사용할 수 있습니다. 이 스크립트는 React 프론트엔드를 실행하지 않습니다.

```bash
./start.sh
```

- API: `http://localhost:8001`

전체 앱을 확인할 때는 Docker Compose로 API와 초기 React UI를 함께 실행하는 방식을 권장합니다.

```bash
docker compose up --build
```

Docker Compose는 향후 ChromaDB 기반 일정 메모리 확장을 위해 `chroma_data` 볼륨을 함께 생성합니다.

- API: `http://localhost:8001`
- 초기 React UI: `http://localhost:5173`

프론트엔드를 Vercel에 배포할 때는 `VITE_API_BASE_URL`을 배포된 FastAPI API 주소로 설정합니다. 이 값은 브라우저에 노출되는 공개 설정이므로 API 키 같은 비밀값을 넣지 않습니다. FastAPI의 `CORS_ORIGINS`에는 Vercel 프론트엔드 도메인을 추가해야 합니다.

## Usage

```bash
curl -X POST http://localhost:8001/api/v1/schedules/tasks/sync \
  -H "Content-Type: application/json" \
  -d '{
    "title": "기말 발표 준비",
    "detail": "자료 조사하고 발표자료를 만들어야 함",
    "start_time": "2026-06-05 13:00",
    "end_time": "2026-06-05 15:00",
    "existing_schedules": [],
    "max_retry": 2
  }'
```

`classification_retry`, `plan_retry`, `detail_with_context`, `context_answer`는 서버 상태 저장이 없는 현재 프로토타입에서 LangGraph 상태를 이어가기 위한 필드입니다. 정식 API/DB 연동 단계에서는 run/session 저장소가 이 상태를 관리하고, 클라이언트는 사용자 입력과 보충 답변 중심으로 요청하도록 재설계할 예정입니다.

`existing_schedules`는 캘린더/DB 연동 전 충돌 검증을 실험하기 위한 임시 입력 필드입니다. 정식 API에서는 서버가 Google Calendar 또는 PostgreSQL에서 기존 일정을 조회하는 방식으로 변경할 예정입니다.

응답 예시:

```json
{
  "status": "ok",
  "title": "기말 발표 준비",
  "start_time": "2026-06-05 13:00",
  "end_time": "2026-06-05 15:00",
  "tasks": [
    {
      "title": "발표 주제와 목차 확정",
      "description": "발표에서 다룰 핵심 주제와 발표 순서를 정리한다.",
      "estimated_minutes": 20,
      "order_index": 1
    }
  ]
}
```

위 응답은 주요 필드만 보여주는 축약 예시입니다.

## Project Structure

```text
app/
  main.py
  api.py
  core/
    config.py
    llm.py
  schedule_agent/
    CONTEXT.md
    ADR.md
    graph.py
    schemas.py
    prompts.py
    nodes/
  schedule_memory/
    CONTEXT.md
    ADR.md
    chroma.py
    embedding.py
    vector_store.py
tests/
frontend/
  package.json
  src/
    App.tsx
    main.tsx
    styles.css
Dockerfile.api
Dockerfile.frontend
docker-compose.yml
start.sh
```

`frontend`는 API 테스트와 이후 화면 개발을 위한 React + Vite + TypeScript 초기 UI입니다. 핵심 에이전트 동작 검증은 FastAPI API와 Python 테스트를 기준으로 합니다.

## Development

의존성 잠금 파일:

- `uv.lock`: Python 백엔드/에이전트 의존성 버전을 고정합니다.
- `frontend/package-lock.json`: React 프론트엔드 의존성 버전을 고정합니다.

문법 검증:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/project_code_pycache python3 -m compileall app tests
```

프론트엔드 빌드 검증:

```bash
cd frontend
npm ci
npm run build
```

테스트:

```bash
uv run python -m unittest tests.test_schedule_agent
```

## Documentation

- [CONTEXT-MAP.md](CONTEXT-MAP.md)
- [app/schedule_agent/CONTEXT.md](app/schedule_agent/CONTEXT.md)
- [app/schedule_agent/ADR.md](app/schedule_agent/ADR.md)
- [app/schedule_memory/CONTEXT.md](app/schedule_memory/CONTEXT.md)
- [app/schedule_memory/ADR.md](app/schedule_memory/ADR.md)

## Collaborator Setup

처음 참여하는 팀원은 다음 순서로 프로젝트를 구성합니다.

1. 저장소를 클론합니다.

```bash
git clone <repository-url>
cd asm17-agentic-dev-practice
```

2. 환경변수 파일을 생성하고 API 키를 설정합니다.

```bash
cp .env.example .env
```

`.env`에서 최소한 `UPSTAGE_API_KEY`를 채웁니다. Vercel 등 외부 배포 환경에서는 `VITE_API_BASE_URL`과 `CORS_ORIGINS`를 배포 주소에 맞게 조정합니다.

3. 전체 앱은 Docker Compose로 실행합니다.

```bash
docker compose up --build
```

- API: `http://localhost:8001`
- Frontend: `http://localhost:5173`
- Health Check: `http://localhost:8001/health`

4. 로컬에서 직접 개발할 때는 의존성을 설치합니다.

```bash
uv sync
cd frontend
npm ci
```

5. 선택 사항: Docker 대신 로컬에서 직접 실행할 때는 API와 프론트엔드를 나누어 실행합니다.

```bash
./start.sh
```

```bash
cd frontend
npm run dev
```

`./start.sh`는 FastAPI API만 실행합니다. 프론트엔드는 `frontend` 디렉터리에서 별도로 실행합니다.

6. PR 전 검증 명령을 실행합니다.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/project_code_pycache python3 -m compileall app tests
uv run python -m unittest tests.test_schedule_agent
cd frontend
npm run build
```
