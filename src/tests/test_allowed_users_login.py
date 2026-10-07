"""SDLCAIP2-67 測試：DB 白名單登入、快取、last_login（AC1-AC11；AC12 見 test_allowed_emails_removed.py）。"""
import logging
import re
import time
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt
from jose.utils import long_to_base64

import allowed_users
import auth
import config
from app import app
from auth import CurrentUser, get_current_user

ADMIN_URL = "/api/admin/allowed-users"
DENIED = "此帳號未被授權使用本系統"
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@pytest.fixture(scope="module")
def _keys():
    pk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    n = pk.public_key().public_numbers()
    jwk = {
        "kty": "RSA", "kid": "k67", "alg": "RS256", "use": "sig",
        "n": long_to_base64(n.n).decode(), "e": long_to_base64(n.e).decode(),
    }
    pem = pk.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    return pem, jwk


@pytest.fixture
def login(_keys, monkeypatch):
    """回傳 call(email, path='/api/me') -> response，走真實 get_current_user / verify_token。"""
    pem, jwk = _keys
    monkeypatch.setattr(config, "COGNITO_APP_CLIENT_ID", "client-abc")
    monkeypatch.setattr(config, "ADMIN_EMAILS", "admin@example.com")
    monkeypatch.setitem(auth._JWKS_CACHE, "keys", {"keys": [jwk]})
    monkeypatch.setitem(auth._JWKS_CACHE, "fetched_at", time.time())
    app.dependency_overrides.pop(get_current_user, None)
    client = TestClient(app)

    def call(email, path="/api/me"):
        now = int(time.time())
        token = jwt.encode(
            {
                "email": email,
                "iss": f"https://cognito-idp.{config.COGNITO_REGION}.amazonaws.com/{config.COGNITO_USER_POOL_ID}",
                "aud": "client-abc", "exp": now + 3600, "iat": now - 20,
            },
            pem, algorithm="RS256", headers={"kid": "k67"},
        )
        return client.get(path, headers={"Authorization": f"Bearer {token}"})

    return call


def _rows():
    allowed_users.ensure_allowed_users_table_exists()
    return {i["email"]: i for i in allowed_users._table().scan()["Items"]}


def _boom(*a, **k):
    raise ClientError({"Error": {"Code": "InternalServerError", "Message": "boom"}}, "Op")


class _Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def time(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    c = _Clock()
    # 只替換 allowed_users 模組內的 time，避免影響 JWT exp / JWKS TTL
    monkeypatch.setattr(allowed_users, "time", SimpleNamespace(time=c.time))
    return c


def _admin_client():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(email="boss@example.com", role="admin")
    return TestClient(app)


def _count_list_users(monkeypatch):
    calls = {"n": 0}
    real = allowed_users.list_users

    def counting():
        calls["n"] += 1
        return real()

    monkeypatch.setattr(allowed_users, "list_users", counting)
    return calls


# AC1
def test_ac1_allowlisted_user_can_login(login):
    allowed_users.add_user("u@example.com")
    r = login("u@example.com")
    assert r.status_code == 200
    assert r.json() == {"email": "u@example.com", "role": "user"}


# AC2
def test_ac2_removed_user_rejected_same_container(login):
    allowed_users.add_user("u@example.com")
    assert login("u@example.com").status_code == 200
    allowed_users.remove_user("u@example.com")
    for path in ("/api/me", "/api/meetings"):
        r = login("u@example.com", path)
        assert r.status_code == 403
        assert r.json()["detail"] == DENIED


def test_ac2_removed_out_of_band_rejected_after_ttl(login, clock):
    allowed_users.add_user("u@example.com")
    assert login("u@example.com").status_code == 200
    allowed_users._table().delete_item(Key={"email": "u@example.com"})
    assert login("u@example.com").status_code == 200  # TTL 內仍快取
    clock.now += allowed_users.CACHE_TTL_SECONDS + 1
    r = login("u@example.com")
    assert r.status_code == 403 and r.json()["detail"] == DENIED


def test_ac2_not_in_table_rejected(login):
    allowed_users.add_user("other@example.com")
    r = login("stranger@example.com")
    assert r.status_code == 403 and r.json()["detail"] == DENIED


# AC3
def test_ac3_empty_table_rejects_non_admin(login):
    r = login("u@example.com")
    assert r.status_code == 403
    assert r.json()["detail"] == DENIED


# AC4
def test_ac4_admin_with_empty_table_ok_and_no_row(login):
    r = login("admin@example.com")
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    assert _rows() == {}


def test_ac4_admin_does_not_read_table(login, monkeypatch):
    monkeypatch.setattr(allowed_users, "get_all_emails", _boom)
    monkeypatch.setattr(allowed_users, "list_users", _boom)
    monkeypatch.setattr(allowed_users, "_table", _boom)
    r = login("Admin@Example.com")
    assert r.status_code == 200 and r.json()["role"] == "admin"


def test_ac4_verify_token_admin_never_calls_get_all_emails(_keys, monkeypatch):
    pem, jwk = _keys
    monkeypatch.setattr(config, "COGNITO_APP_CLIENT_ID", "client-abc")
    monkeypatch.setattr(config, "ADMIN_EMAILS", "admin@example.com")
    monkeypatch.setattr(allowed_users, "get_all_emails", _boom)
    now = int(time.time())
    tok = jwt.encode(
        {"email": "admin@example.com", "iss": auth._cognito_issuer(), "aud": "client-abc",
         "exp": now + 3600, "iat": now - 20},
        pem, algorithm="RS256", headers={"kid": "k67"},
    )
    assert auth.verify_token(tok, jwks_provider=lambda: {"keys": [jwk]}).role == "admin"


# AC5
def test_ac5_db_failure_no_cache_fails_closed(login, monkeypatch):
    allowed_users.add_user("u@example.com")
    monkeypatch.setattr(allowed_users, "list_users", _boom)
    r = login("u@example.com")
    assert r.status_code == 403 and r.json()["detail"] == DENIED
    assert login("admin@example.com").status_code == 200


def test_ac5_unexpired_cache_survives_broken_table(login, monkeypatch, clock):
    allowed_users.add_user("u@example.com")
    assert login("u@example.com").status_code == 200
    monkeypatch.setattr(allowed_users, "list_users", _boom)
    clock.now += allowed_users.CACHE_TTL_SECONDS - 1
    assert login("u@example.com").status_code == 200


def test_ac5_expired_cache_with_broken_table_denied(login, monkeypatch, clock):
    allowed_users.add_user("u@example.com")
    assert login("u@example.com").status_code == 200
    monkeypatch.setattr(allowed_users, "list_users", _boom)
    clock.now += allowed_users.CACHE_TTL_SECONDS + 1
    r = login("u@example.com")
    assert r.status_code == 403 and r.json()["detail"] == DENIED
    with pytest.raises(ClientError):
        allowed_users.get_all_emails()


# AC6
def test_ac6_ttl_constant():
    assert allowed_users.CACHE_TTL_SECONDS == 60


def test_ac6_second_call_within_ttl_no_db(login, monkeypatch, clock):
    allowed_users.add_user("u@example.com")
    calls = _count_list_users(monkeypatch)
    assert login("u@example.com").status_code == 200
    assert login("u@example.com").status_code == 200
    assert calls["n"] == 1
    allowed_users._table().put_item(Item={"email": "late@example.com"})  # 帶外變更
    assert login("late@example.com").status_code == 403  # TTL 內看不到
    assert calls["n"] == 1


def test_ac6_requery_after_ttl(login, monkeypatch, clock):
    allowed_users.add_user("u@example.com")
    calls = _count_list_users(monkeypatch)
    login("u@example.com")
    clock.now += allowed_users.CACHE_TTL_SECONDS + 1
    login("u@example.com")
    assert calls["n"] == 2


def test_ac6_empty_result_is_cached(login, monkeypatch, clock):
    calls = _count_list_users(monkeypatch)
    assert login("u@example.com").status_code == 403
    assert login("v@example.com").status_code == 403
    assert calls["n"] == 1
    assert allowed_users.get_all_emails() == frozenset()


# AC7
def test_ac7_post_invalidates_cache(login):
    assert login("n@example.com").status_code == 403  # 快取空集合
    c = _admin_client()
    assert c.post(ADMIN_URL, json={"email": "n@example.com"}).status_code in (200, 201)
    app.dependency_overrides.pop(get_current_user, None)
    assert login("n@example.com").status_code == 200


def test_ac7_delete_invalidates_cache(login):
    allowed_users.add_user("n@example.com")
    assert login("n@example.com").status_code == 200  # 暖快取
    c = _admin_client()
    r = c.delete(f"{ADMIN_URL}/n@example.com")
    assert r.status_code in (200, 204)
    app.dependency_overrides.pop(get_current_user, None)
    assert login("n@example.com").status_code == 403


@pytest.mark.parametrize("pre_existing", [False, True])
def test_ac7_add_user_invalidates(pre_existing):
    if pre_existing:
        allowed_users.add_user("a@example.com")
    allowed_users.get_all_emails()
    assert allowed_users._CACHE["emails"] is not None
    _, created = allowed_users.add_user("a@example.com")
    assert created is (not pre_existing)
    assert allowed_users._CACHE["emails"] is None
    assert "a@example.com" in allowed_users.get_all_emails()


@pytest.mark.parametrize("pre_existing", [True, False])
def test_ac7_remove_user_invalidates(pre_existing):
    if pre_existing:
        allowed_users.add_user("a@example.com")
    allowed_users.get_all_emails()
    assert allowed_users._CACHE["emails"] is not None
    assert allowed_users.remove_user("a@example.com") is pre_existing
    assert allowed_users._CACHE["emails"] is None
    assert "a@example.com" not in allowed_users.get_all_emails()


# AC8
def test_ac8_me_sets_last_login(login):
    allowed_users.add_user("u@example.com")
    assert _rows()["u@example.com"].get("last_login") is None
    assert login("u@example.com").status_code == 200
    assert TS_RE.match(_rows()["u@example.com"]["last_login"])


def test_ac8_email_case_same_row(login):
    allowed_users.add_user("u@example.com")
    assert login("U@Example.COM").status_code == 200
    rows = _rows()
    assert list(rows) == ["u@example.com"]
    assert TS_RE.match(rows["u@example.com"]["last_login"])


def test_ac8_table_key_uppercase_normalized_on_add():
    allowed_users.add_user("MiXed@Example.com")
    assert "mixed@example.com" in allowed_users.get_all_emails()


# AC9
def test_ac9_other_endpoints_do_not_touch_last_login(login):
    allowed_users.add_user("u@example.com")
    assert login("u@example.com", "/api/health-check-v2").status_code == 200
    assert _rows()["u@example.com"].get("last_login") is None
    r = login("u@example.com", "/api/meetings")
    assert r.status_code == 200
    assert _rows()["u@example.com"].get("last_login") is None
    assert login("u@example.com", ADMIN_URL).status_code == 403  # 非管理者
    assert _rows()["u@example.com"].get("last_login") is None


def test_ac9_admin_list_endpoint_does_not_touch(login):
    allowed_users.add_user("u@example.com")
    r = login("admin@example.com", ADMIN_URL)
    assert r.status_code == 200
    assert _rows()["u@example.com"].get("last_login") is None


# AC10
def test_ac10_admin_me_creates_no_row(login):
    assert login("admin@example.com").status_code == 200
    assert _rows() == {}
    allowed_users.add_user("u@example.com")
    assert login("admin@example.com").status_code == 200
    assert list(_rows()) == ["u@example.com"]


def test_ac10_touch_nonexistent_returns_false_no_row():
    assert allowed_users.touch_last_login("ghost@example.com") is False
    assert _rows() == {}


# AC11
def test_ac11_touch_failure_does_not_break_login(login, monkeypatch, caplog):
    allowed_users.add_user("u@example.com")
    monkeypatch.setattr(allowed_users, "touch_last_login", _boom)
    with caplog.at_level(logging.ERROR):
        r = login("u@example.com")
    assert r.status_code == 200
    assert any(rec.levelno >= logging.ERROR for rec in caplog.records)


def test_ac11_update_item_failure_does_not_break_login(login, monkeypatch, caplog):
    allowed_users.add_user("u@example.com")
    real_table = allowed_users._table

    class _T:
        def __getattr__(self, name):
            return getattr(real_table(), name)

        def update_item(self, *a, **k):
            _boom()

    monkeypatch.setattr(allowed_users, "_table", lambda: _T())
    with caplog.at_level(logging.ERROR):
        r = login("u@example.com")
    assert r.status_code == 200
    assert any(rec.levelno >= logging.ERROR for rec in caplog.records)


# 併發 / generation 防護
def test_generation_guard_invalidate_during_query_not_cached(monkeypatch):
    allowed_users.add_user("a@example.com")
    real = allowed_users.list_users
    state = {"n": 0}

    def racing():
        state["n"] += 1
        data = real()
        if state["n"] == 1:
            allowed_users.invalidate_cache()  # 查詢進行中被失效
        return data

    monkeypatch.setattr(allowed_users, "list_users", racing)
    allowed_users.get_all_emails()
    assert allowed_users._CACHE["emails"] is None
    allowed_users.get_all_emails()
    assert state["n"] == 2
    allowed_users.get_all_emails()
    assert state["n"] == 2  # 第二次結果已被快取
