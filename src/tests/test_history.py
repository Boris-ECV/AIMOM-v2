"""TASK-009 測試：會議紀錄歷史（DynamoDB + 使用者隔離）。"""
from fastapi.testclient import TestClient

from app import app
from auth import CurrentUser, get_current_user
import jobstore

client = TestClient(app)


def _write_job_result(job_id: str):
    jobstore.create_job(
        job_id,
        stage="done",
        progress=100,
        message="done",
        filename="weekly-sync.mp3",
        segments=[{"speaker": "A", "text": "hello"}],
        minutes={"summary": "討論重點", "action_items": []},
    )


def test_keep_meeting_creates_history_item():
    _write_job_result("job-1")
    resp = client.post("/api/meetings/job-1/keep")
    assert resp.status_code == 200
    body = resp.json()
    assert "meeting_id" in body
    assert body["expires_at"] > 0


def test_discard_meeting_does_not_persist():
    _write_job_result("job-2")
    resp = client.post("/api/meetings/job-2/discard")
    assert resp.status_code == 200
    assert resp.json() == {"status": "discarded"}

    listing = client.get("/api/meetings").json()
    assert all(m["title"] != "job-2" for m in listing["meetings"])


def test_keep_missing_job_returns_404():
    resp = client.post("/api/meetings/does-not-exist/keep")
    assert resp.status_code == 404


def test_list_and_get_meeting():
    _write_job_result("job-3")
    keep_resp = client.post("/api/meetings/job-3/keep").json()
    meeting_id = keep_resp["meeting_id"]

    listing = client.get("/api/meetings").json()["meetings"]
    assert any(m["meeting_id"] == meeting_id for m in listing)

    detail = client.get(f"/api/meetings/{meeting_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "weekly-sync.mp3"
    assert body["minutes"]["summary"] == "討論重點"


def test_delete_meeting():
    _write_job_result("job-4")
    meeting_id = client.post("/api/meetings/job-4/keep").json()["meeting_id"]

    delete_resp = client.delete(f"/api/meetings/{meeting_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"status": "deleted"}

    get_resp = client.get(f"/api/meetings/{meeting_id}")
    assert get_resp.status_code == 404


def test_delete_nonexistent_meeting_returns_404():
    resp = client.delete("/api/meetings/does-not-exist")
    assert resp.status_code == 404


def test_user_isolation_cannot_see_other_users_meeting():
    _write_job_result("job-5")
    meeting_id = client.post("/api/meetings/job-5/keep").json()["meeting_id"]

    def _other_user() -> CurrentUser:
        return CurrentUser(email="other-user@example.com", role="user")

    app.dependency_overrides[get_current_user] = _other_user
    try:
        resp = client.get(f"/api/meetings/{meeting_id}")
        assert resp.status_code == 404

        listing = client.get("/api/meetings").json()["meetings"]
        assert all(m["meeting_id"] != meeting_id for m in listing)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
