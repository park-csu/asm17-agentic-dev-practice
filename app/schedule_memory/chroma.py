import chromadb

from app.core.config import CHROMA_HOST, CHROMA_MODE, CHROMA_PORT

_client = None


def get_chroma_client() -> chromadb.ClientAPI:
    """향후 유사 일정 검색 확장에 사용할 ChromaDB 클라이언트를 생성한다."""
    global _client
    if _client is not None:
        return _client
    if CHROMA_MODE == "http":
        _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    else:
        _client = chromadb.PersistentClient(path="./chroma_data")
    return _client
