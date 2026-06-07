from typing import Optional
from uuid import UUID

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import SUPABASE_URL

bearer_scheme = HTTPBearer(auto_error=False)
SUPPORTED_JWT_ALGORITHMS = ["RS256", "ES256", "HS256"]

# JWKS 클라이언트 — 키를 자동으로 캐싱하고 갱신한다
_jwks_client: Optional[PyJWKClient] = None


def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def verify_token(token: str) -> dict:
    """Supabase JWKS로 JWT를 검증하고 페이로드를 반환한다."""
    try:
        client = get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=SUPPORTED_JWT_ALGORITHMS,
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰이 만료되었습니다.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다.")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Authorization 헤더에서 JWT를 검증하고 사용자 정보를 반환한다."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 토큰이 필요합니다.")
    return verify_token(credentials.credentials)


def get_current_user_id(user: dict = Depends(get_current_user)) -> UUID:
    """검증된 토큰에서 user_id(sub)를 반환한다."""
    sub = user.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자 정보를 찾을 수 없습니다.")
    return UUID(sub)
