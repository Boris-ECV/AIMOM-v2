"""TASK-011 測試：管理者成本/用量儀表板。"""
import os

import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")

from app import app
from auth import CurrentUser, get_current_user
import usage


@pytest.fixture
def client():
    with mock_aws():
        yield TestClient(app)


def test_record_llm_usage_and_estimate_cost():
    with mock_aws():
        item = usage.record_llm_usage(
            engine="github-models",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            user_id="user@example.com",
            meeting_id="job-1",
        )
    assert item["estimated_cost"] == round((1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00, 6)


def test_estimate_cost_unknown_model_returns_none():
    assert usage.estimate_cost("unknown-engine", "unknown-model", 100, 100) is None


def test_summarize_usage_aggregates_by_date_and_user():
    with mock_aws():
        usage.record_llm_usage("groq", "llama-3.3-70b-versatile", 2000, 1000, "a@example.com", "job-a")
        usage.record_llm_usage("groq", "llama-3.3-70b-versatile", 1000, 500, "b@example.com", "job-b")

        summary = usage.summarize_usage()
    assert summary["total_calls"] == 2
    assert len(summary["by_user"]) == 2
    assert summary["total_estimated_cost"] > 0


def test_admin_usage_endpoint_requires_admin(client):
    def _regular_user() -> CurrentUser:
        return CurrentUser(email="user@example.com", role="user")

    app.dependency_overrides[get_current_user] = _regular_user
    try:
        resp = client.get("/api/admin/usage")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_admin_usage_endpoint_allows_admin(client):
    def _admin_user() -> CurrentUser:
        return CurrentUser(email="admin@example.com", role="admin")

    app.dependency_overrides[get_current_user] = _admin_user
    try:
        resp = client.get("/api/admin/usage")
        assert resp.status_code == 200
        body = resp.json()
        assert "by_date" in body
        assert "by_user" in body
        assert "total_calls" in body
    finally:
        app.dependency_overrides.pop(get_current_user, None)
