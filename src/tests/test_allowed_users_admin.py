"""SDLCAIP2-66 測試：管理者白名單資料表與管理 API。"""
import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

import allowed_users
from app import app
from auth import CurrentUser, get_current_user

URL = "/api/admin/allowed-users"


def _as(role):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        email="boss@example.com", role=role
    )


@pytest.fixture
def admin():
    _as("admin")
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def user_client():
    _as("user")
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def table():
    allowed_users.ensure_allowed_users_table_exists()
    return allowed_users._table()


def _scan(table):
    return {i["email"]: i for i in table.scan()["Items"]}


def _client_error():
    return ClientError({"Error": {"Code": "InternalServerError", "Message": "boom"}}, "Op")


# AC1
def test_ac1_list_sorted_and_shape(admin, table):
    table.put_item(Item={"email": "b@example.com"})
    table.put_item(Item={"email": "a@example.com", "last_login": "2026-10-01T00:00:00Z"})
    r = admin.get(URL)
    assert r.status_code == 200
    assert r.json() == [
        {"email": "a@example.com", "last_login": "2026-10-01T00:00:00Z"},
        {"email": "b@example.com", "last_login": None},
    ]


def test_ac1_list_empty(admin):
    r = admin.get(URL)
    assert r.status_code == 200
    assert r.json() == []


# AC2
def test_ac2_add_normalizes(admin, table):
    r = admin.post(URL, json={"email": "  C@Example.com "})
    assert r.status_code == 201
    assert r.json() == {"email": "c@example.com", "last_login": None}
    assert "c@example.com" in [i["email"] for i in admin.get(URL).json()]
    assert "c@example.com" in _scan(table)


# AC3
def test_ac3_duplicate_idempotent_keeps_last_login(admin, table):
    table.put_item(Item={"email": "c@example.com", "last_login": "2026-10-01T00:00:00Z"})
    r = admin.post(URL, json={"email": "c@example.com"})
    assert r.status_code == 200
    assert r.json()["last_login"] == "2026-10-01T00:00:00Z"
    assert _scan(table)["c@example.com"]["last_login"] == "2026-10-01T00:00:00Z"
    assert len(_scan(table)) == 1


def test_ac3_duplicate_without_last_login(admin):
    assert admin.post(URL, json={"email": "d@example.com"}).status_code == 201
    r = admin.post(URL, json={"email": "D@example.com"})
    assert r.status_code == 200
    assert r.json() == {"email": "d@example.com", "last_login": None}


# AC4
@pytest.mark.parametrize(
    "body",
    [
        {"email": "not-an-email"},
        {"email": ""},
        {"email": "   "},
        {"email": "a@b"},
        {"email": "a b@c.com"},
        {"email": "a@@c.com"},
        {},
        {"email": 123},
        {"email": None},
        {"email": ["a@b.com"]},
    ],
)
def test_ac4_invalid_email_rejected(admin, table, body):
    r = admin.post(URL, json=body)
    assert r.status_code == 422
    assert _scan(table) == {}


# AC5
def test_ac5_delete_existing(admin, table):
    table.put_item(Item={"email": "c@example.com"})
    r = admin.delete(f"{URL}/c@example.com")
    assert r.status_code == 204
    assert r.content == b""
    assert "c@example.com" not in [i["email"] for i in admin.get(URL).json()]
    assert _scan(table) == {}


@pytest.mark.parametrize(
    "seg", ["C@Example.com", "c%40example.com", "C%40EXAMPLE.COM", "%20c@example.com%20"]
)
def test_ac5_delete_normalizes(admin, table, seg):
    table.put_item(Item={"email": "c@example.com"})
    assert admin.delete(f"{URL}/{seg}").status_code == 204
    assert _scan(table) == {}


# AC6
def test_ac6_delete_missing_404(admin, table):
    table.put_item(Item={"email": "x@example.com"})
    assert admin.delete(f"{URL}/nobody@example.com").status_code == 404
    assert "x@example.com" in _scan(table)


@pytest.mark.parametrize("seg", ["%20", "%20%20", "%09"])
def test_ac6_delete_blank_segment_404(admin, seg):
    assert admin.delete(f"{URL}/{seg}").status_code == 404


def test_ac6_delete_empty_segment_not_500(admin):
    r = admin.delete(f"{URL}/")
    assert r.status_code < 500


# AC7
def test_ac7_non_admin_forbidden_and_table_unchanged(user_client, table):
    table.put_item(Item={"email": "keep@example.com", "last_login": "2026-10-01T00:00:00Z"})
    before = _scan(table)
    assert user_client.get(URL).status_code == 403
    assert user_client.post(URL, json={"email": "new@example.com"}).status_code == 403
    assert user_client.delete(f"{URL}/keep@example.com").status_code == 403
    assert _scan(table) == before


# AC8
def test_ac8_no_token_401():
    app.dependency_overrides.pop(get_current_user, None)
    c = TestClient(app)
    assert c.get(URL).status_code == 401
    assert c.post(URL, json={"email": "a@example.com"}).status_code == 401
    assert c.delete(f"{URL}/a@example.com").status_code == 401


# AC10
@pytest.mark.parametrize("method", ["get", "post", "delete"])
def test_ac10_dynamodb_error_is_5xx(admin, monkeypatch, method):
    allowed_users.ensure_allowed_users_table_exists()

    class Boom:
        def __getattr__(self, name):
            def f(*a, **k):
                raise _client_error()

            return f

    monkeypatch.setattr(allowed_users, "_table", lambda: Boom())
    if method == "get":
        r = admin.get(URL)
    elif method == "post":
        r = admin.post(URL, json={"email": "a@example.com"})
    else:
        r = admin.delete(f"{URL}/a@example.com")
    assert r.status_code >= 500
    body = r.json()
    assert not isinstance(body, list)
    assert "email" not in body


def test_ac10_ensure_table_error_is_5xx(admin, monkeypatch):
    def boom():
        raise _client_error()

    monkeypatch.setattr(allowed_users, "ensure_allowed_users_table_exists", boom)
    r = admin.get(URL)
    assert r.status_code >= 500


# data layer
def test_list_users_paginates(table, monkeypatch):
    for i in range(5):
        table.put_item(Item={"email": f"u{i}@example.com"})
    real = allowed_users._table()
    calls = []

    class Paged:
        def scan(self, **kw):
            calls.append(kw)
            items = real.scan()["Items"]
            if "ExclusiveStartKey" not in kw:
                return {"Items": items[:2], "LastEvaluatedKey": {"email": items[1]["email"]}}
            return {"Items": items[2:]}

    monkeypatch.setattr(allowed_users, "_table", lambda: Paged())
    assert [u["email"] for u in allowed_users.list_users()] == [
        f"u{i}@example.com" for i in range(5)
    ]
    assert len(calls) == 2


def test_ensure_table_access_denied_is_tolerated(monkeypatch):
    class C:
        def list_tables(self):
            raise ClientError({"Error": {"Code": "AccessDeniedException"}}, "ListTables")

    monkeypatch.setattr(allowed_users.boto3, "client", lambda *a, **k: C())
    allowed_users.ensure_allowed_users_table_exists()


def test_ensure_table_other_error_raises(monkeypatch):
    class C:
        def list_tables(self):
            raise _client_error()

    monkeypatch.setattr(allowed_users.boto3, "client", lambda *a, **k: C())
    with pytest.raises(ClientError):
        allowed_users.ensure_allowed_users_table_exists()


def test_remove_user_blank_false():
    assert allowed_users.remove_user("  ") is False


def test_add_user_non_conditional_error_raises(monkeypatch):
    class T:
        def put_item(self, **k):
            raise _client_error()

    monkeypatch.setattr(allowed_users, "_table", lambda: T())
    with pytest.raises(ClientError):
        allowed_users.add_user("a@example.com")


def test_remove_user_non_conditional_error_raises(monkeypatch):
    class T:
        def delete_item(self, **k):
            raise _client_error()

    monkeypatch.setattr(allowed_users, "_table", lambda: T())
    with pytest.raises(ClientError):
        allowed_users.remove_user("a@example.com")
