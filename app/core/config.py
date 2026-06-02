import os

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "")
CHROMA_MODE = os.getenv("CHROMA_MODE", "embedded")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
