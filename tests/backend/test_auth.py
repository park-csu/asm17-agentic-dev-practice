from uuid import UUID

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from backend.core import auth


class FakeSigningKey:
    def __init__(self, key):
        self.key = key


class FakeJwksClient:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, token: str):
        return FakeSigningKey(self.key)


def test_verify_token_accepts_supabase_es256_jwt(monkeypatch):
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    token = jwt.encode(
        {"sub": str(user_id), "role": "authenticated"},
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )

    monkeypatch.setattr(auth, "get_jwks_client", lambda: FakeJwksClient(public_key))

    payload = auth.verify_token(token)

    assert payload["sub"] == str(user_id)
