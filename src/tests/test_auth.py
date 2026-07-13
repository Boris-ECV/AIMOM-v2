"""TASK-008 單元測試：登入與角色驗證。"""
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from jose import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jose.utils import long_to_base64

import config
import auth


@pytest.fixture
def rsa_key():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test-key-1",
        "alg": "RS256",
        "use": "sig",
        "n": long_to_base64(public_numbers.n).decode("utf-8"),
        "e": long_to_base64(public_numbers.e).decode("utf-8"),
    }
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem, jwk


def _make_token(pem, email="user@example.com", expired=False, issuer=None, audience=None):
    now = int(time.time())
    payload = {
        "email": email,
        "iss": issuer or f"https://cognito-idp.{config.COGNITO_REGION}.amazonaws.com/{config.COGNITO_USER_POOL_ID}",
        "aud": audience or config.COGNITO_APP_CLIENT_ID,
        "exp": now - 10 if expired else now + 3600,
        "iat": now - 20,
    }
    return jwt.encode(payload, pem, algorithm="RS256", headers={"kid": "test-key-1"})


def test_verify_token_success_regular_user(rsa_key, monkeypatch):
    pem, jwk = rsa_key
    monkeypatch.setattr(config, "ADMIN_EMAILS", "admin@example.com")
    monkeypatch.setattr(config, "COGNITO_APP_CLIENT_ID", "client-abc")
    token = _make_token(pem, email="user@example.com")

    user = auth.verify_token(token, jwks_provider=lambda: {"keys": [jwk]})

    assert user.email == "user@example.com"
    assert user.role == "user"


def test_verify_token_admin_whitelist(rsa_key, monkeypatch):
    pem, jwk = rsa_key
    monkeypatch.setattr(config, "ADMIN_EMAILS", "admin@example.com, boss@example.com")
    monkeypatch.setattr(config, "COGNITO_APP_CLIENT_ID", "client-abc")
    token = _make_token(pem, email="Admin@example.com")

    user = auth.verify_token(token, jwks_provider=lambda: {"keys": [jwk]})

    assert user.role == "admin"


def test_verify_token_expired_rejected(rsa_key, monkeypatch):
    pem, jwk = rsa_key
    monkeypatch.setattr(config, "COGNITO_APP_CLIENT_ID", "client-abc")
    token = _make_token(pem, expired=True)

    with pytest.raises(ValueError):
        auth.verify_token(token, jwks_provider=lambda: {"keys": [jwk]})


def test_verify_token_unknown_kid_rejected(rsa_key, monkeypatch):
    pem, jwk = rsa_key
    monkeypatch.setattr(config, "COGNITO_APP_CLIENT_ID", "client-abc")
    token = _make_token(pem)

    with pytest.raises(ValueError):
        auth.verify_token(token, jwks_provider=lambda: {"keys": []})


def test_get_current_user_missing_header_401():
    from fastapi.testclient import TestClient
    from app import app
    from auth import get_current_user

    app.dependency_overrides.pop(get_current_user, None)
    client = TestClient(app)
    resp = client.get("/api/me")
    assert resp.status_code == 401
