from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import router
from backend.core.config import CORS_ORIGINS
from backend.db.session import init_db

DESCRIPTION = """
TaskPilot 일정 서브태스크 생성 API입니다.

사용자가 일정을 입력하면 LangGraph 기반 에이전트가 실행 가능한 서브태스크로 분해합니다.

## 에이전트 플로우

에이전트는 아래 순서로 노드를 실행하며, 각 노드의 진행 상황을 SSE로 스트리밍합니다.

```
pre_validate → classification → [ask_context] → plan → post_validate → output/fallback
```

## SSE 이벤트 형식

스트리밍 엔드포인트는 `text/event-stream` 형식으로 응답합니다.

```
data: {"event": "node", "node": "<노드명>", "data": "<JSON 문자열>"}

data: {"event": "done", "node": "", "data": "<JSON 문자열>"}
```

### node 이벤트 — 노드별 data 필드

| node | data 주요 필드 |
|------|---------------|
| `pre_validate` | `is_valid`, `needs_question`, `question`, `invalid_reason` |
| `classification` | `is_decomposable`, `needs_question`, `question`, `question_source` |
| `ask_context` | `detail_with_context`, `status`, `classification_retry` |
| `plan` | `tasks[]` (title, estimated_minutes, order_index) |
| `post_validate` | `is_valid`, `tasks[]` |
| `output` | `status`, `tasks[]`, `answer` |
| `fallback` | `status`, `fallback_reason` |

### done 이벤트 — data 필드

| 필드 | 설명 |
|------|------|
| `schedule_id` | 저장된 일정 UUID |
| `status` | `ok` / `needs_question` / `fallback` |
| `tasks` | 생성된 서브태스크 목록 |
| `question` | 추가 질문 (status가 needs_question일 때) |
| `question_source` | `classification` / `pre_validate` |
| `classification_retry` | 분류 재시도 횟수 |
| `pre_validation_retry` | 사전 검증 재시도 횟수 |
| `plan_retry` | 계획 재시도 횟수 |
| `detail_with_context` | 누적된 일정 상세 컨텍스트 |
| `fallback_reason` | 실패 이유 |

## 추가 질문 흐름

에이전트가 추가 정보가 필요할 때 `status: needs_question`과 함께 `question`을 반환합니다.
사용자 답변을 `context_answer`에 담아 동일 엔드포인트를 재호출하면 에이전트가 이어서 실행됩니다.

```json
// 1. 최초 요청 → needs_question 응답
{ "question": "발표 목적이 무엇인가요?", "question_source": "classification", "classification_retry": 1 }

// 2. 답변 포함 재요청
{ "context_answer": "팀 내부 공유용", "question": "...", "question_source": "classification", "classification_retry": 1 }
```
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="TaskPilot API",
    version="1.0.0",
    description=DESCRIPTION,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "schedules",
            "description": "일정 생성, 조회, 수정, 삭제 및 에이전트 실행",
        },
        {
            "name": "health",
            "description": "서버 상태 확인",
        },
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["health"], summary="서버 상태 확인")
def health():
    return {"status": "healthy"}
