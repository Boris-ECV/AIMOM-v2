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


def test_update_meeting_overwrites_minutes():
    _write_job_result("job-6")
    keep_resp = client.post("/api/meetings/job-6/keep").json()
    meeting_id = keep_resp["meeting_id"]

    new_minutes = {"summary": "更新後的摘要", "action_items": [{"task": "追蹤", "owner": "Alice"}]}
    resp = client.patch(f"/api/meetings/{meeting_id}", json=new_minutes)
    assert resp.status_code == 200
    body = resp.json()
    assert body["meeting_id"] == meeting_id
    assert body["minutes"] == new_minutes
    # title / expires_at 應維持不變（PATCH 只覆蓋 minutes）
    assert body["title"] == "weekly-sync.mp3"
    assert body["expires_at"] == keep_resp["expires_at"]

    # 再次 GET 確認已真的持久化，而非只回應而未寫入
    detail = client.get(f"/api/meetings/{meeting_id}").json()
    assert detail["minutes"] == new_minutes


def test_update_meeting_is_full_overwrite_not_partial_merge():
    _write_job_result("job-7")
    meeting_id = client.post("/api/meetings/job-7/keep").json()["meeting_id"]

    # 原始 minutes 有 summary + action_items，PATCH 只送一個較小的物件
    new_minutes = {"summary": "只剩摘要"}
    resp = client.patch(f"/api/meetings/{meeting_id}", json=new_minutes)
    assert resp.status_code == 200
    body = resp.json()
    # 整份覆蓋：不應該殘留原本的 action_items 欄位
    assert body["minutes"] == {"summary": "只剩摘要"}
    assert "action_items" not in body["minutes"]


def test_update_nonexistent_meeting_returns_404():
    resp = client.patch("/api/meetings/does-not-exist", json={"summary": "x"})
    assert resp.status_code == 404


def test_update_other_users_meeting_returns_404():
    _write_job_result("job-8")
    meeting_id = client.post("/api/meetings/job-8/keep").json()["meeting_id"]

    def _other_user() -> CurrentUser:
        return CurrentUser(email="other-user@example.com", role="user")

    def _owner_user() -> CurrentUser:
        return CurrentUser(email="test-user@example.com", role="user")

    app.dependency_overrides[get_current_user] = _other_user
    try:
        resp = client.patch(f"/api/meetings/{meeting_id}", json={"summary": "駭入"})
        assert resp.status_code == 404
    finally:
        # 恢復為本人身分（而非完全移除 override），避免後續請求因缺少
        # conftest.py autouse fixture 的預設身分而變成未登入。
        app.dependency_overrides[get_current_user] = _owner_user

    # 原始資料仍應維持不變（未被非本人竄改）
    original = client.get(f"/api/meetings/{meeting_id}").json()
    assert original["minutes"]["summary"] == "討論重點"


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
