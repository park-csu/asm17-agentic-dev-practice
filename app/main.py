from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from backend.core.config import CORS_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Schedule Task Agent API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1", tags=["schedule-agent"])


@app.get("/health")
def health():
    return {"status": "healthy"}
