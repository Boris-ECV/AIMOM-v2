"""SDLCAIP2-22 測試：AssemblyAI 轉錄成本估算。

涵蓋 4 個 Gherkin 情境：
1. 轉錄完成後記錄一筆轉錄成本（依 duration_sec 與費率估算，含 diarization add-on）
2. 診斷模型/add-on 組合尚未支援定價 -> pricing_unavailable=true，estimated_cost 不落地為 0
3. 管理者儀表板同時顯示 transcription 與 summarization 成本
4. duration_sec 缺失時不強行估算 -> 仍寫入紀錄但標記 pricing_unavailable=true

另外涵蓋：
- `finalize_claimed` 併發收尾鎖的冪等行為
- `user_id` 於上傳時（而非輪詢時）寫入 job
- `assemblyai_model`/`assemblyai_diarization_enabled` 於 /transcribe 送出時釘住，
  舊 job 缺欄位時退回讀取目前 config.*
"""
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import app
import config
import jobstore
import usage

client = TestClient(app)


def _completed_transcript():
    import assemblyai as aai

    mock_transcript = MagicMock()
    mock_transcript.utterances = None
    mock_transcript.words = []
    mock_transcript.text = "hello world"
    mock_transcript.status = aai.TranscriptStatus.completed
    return mock_transcript


def _transcription_items_for(job_id: str) -> list[dict]:
    return [i for i in usage._table().scan()["Items"] if i.get("meeting_id") == job_id]


# ─── Scenario 1: 轉錄完成後記錄一筆轉錄成本 ─────────────────────────


def test_transcription_completion_records_transcription_cost():
    job_id = "cost-job-001"
    jobstore.create_job(
        job_id, stage="transcribing", progress=20, message="等待中",
        assemblyai_transcript_id="aai-1", duration_sec=3600.0,
        assemblyai_model="universal-2", assemblyai_diarization_enabled=False,
        user_id="user@example.com",
    )

    with patch("progress._fetch_transcript_status_once", return_value=_completed_transcript()):
        response = client.get(f"/api/status/{job_id}")

    assert response.status_code == 200
    items = _transcription_items_for(job_id)
    assert len(items) == 1
    item = items[0]
    assert item["service"] == "transcription"
    assert float(item["duration_sec"]) == 3600.0
    assert float(item["estimated_cost"]) == pytest.approx(0.15)
    assert item["pricing_unavailable"] is False
    assert item["user_id"] == "user@example.com"
    assert item["engine"] == "assemblyai"
    assert item["model"] == "universal-2"
    assert item["input_tokens"] == 0
    assert item["output_tokens"] == 0


def test_transcription_cost_includes_diarization_addon_rate():
    job_id = "cost-job-diarization"
    jobstore.create_job(
        job_id, stage="transcribing", progress=20, message="等待中",
        assemblyai_transcript_id="aai-diar", duration_sec=3600.0,
        assemblyai_model="universal-2", assemblyai_diarization_enabled=True,
        user_id="user@example.com",
    )

    with patch("progress._fetch_transcript_status_once", return_value=_completed_transcript()):
        client.get(f"/api/status/{job_id}")

    items = _transcription_items_for(job_id)
    assert len(items) == 1
    assert float(items[0]["estimated_cost"]) == pytest.approx(0.17)


# ─── Scenario 2: 診斷模型/add-on 組合尚未支援定價 ─────────────────────


def test_unknown_model_combo_marks_pricing_unavailable_and_writes_record():
    job_id = "cost-job-002"
    jobstore.create_job(
        job_id, stage="transcribing", progress=20, message="等待中",
        assemblyai_transcript_id="aai-2", duration_sec=1800.0,
        assemblyai_model="unknown-model", assemblyai_diarization_enabled=True,
        user_id="user@example.com",
    )
    with patch("progress._fetch_transcript_status_once", return_value=_completed_transcript()):
        client.get(f"/api/status/{job_id}")

    items = _transcription_items_for(job_id)
    assert len(items) == 1
    assert items[0]["pricing_unavailable"] is True
    assert items[0]["estimated_cost"] is None


# ─── Scenario 3: 管理者儀表板同時顯示轉錄與摘要成本 ───────────────────


def test_admin_usage_shows_transcription_and_summarization_subtotals():
    from auth import CurrentUser, get_current_user

    usage.record_transcription_usage(
        model="universal-2", diarization_enabled=False, duration_sec=3600.0,
        user_id="a@example.com", meeting_id="job-t",
    )
    usage.record_llm_usage("groq", "llama-3.3-70b-versatile", 1000, 500, "a@example.com", "job-s")

    def _admin_user():
        return CurrentUser(email="admin@example.com", role="admin")

    app.dependency_overrides[get_current_user] = _admin_user
    try:
        resp = client.get("/api/admin/usage")
        assert resp.status_code == 200
        body = resp.json()
        assert body["by_service"]["transcription"]["calls"] == 1
        assert body["by_service"]["summarization"]["calls"] == 1
        assert body["by_service"]["transcription"]["estimated_cost"] == pytest.approx(0.15)
        assert body["total_estimated_cost"] == pytest.approx(
            body["by_service"]["transcription"]["estimated_cost"]
            + body["by_service"]["summarization"]["estimated_cost"]
        )
        # by_date/by_user 形狀不變，不拆分 service（設計範圍限制）
        assert "by_date" in body
        assert "by_user" in body
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_admin_usage_by_service_defaults_present_even_when_empty():
    from auth import CurrentUser, get_current_user

    def _admin_user():
        return CurrentUser(email="admin@example.com", role="admin")

    app.dependency_overrides[get_current_user] = _admin_user
    try:
        resp = client.get("/api/admin/usage")
        assert resp.status_code == 200
        body = resp.json()
        assert body["by_service"]["transcription"] == {"calls": 0, "estimated_cost": 0.0}
        assert body["by_service"]["summarization"] == {"calls": 0, "estimated_cost": 0.0}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ─── Scenario 4: duration_sec 缺失時不強行估算 ────────────────────────


def test_missing_duration_sec_marks_pricing_unavailable_but_still_writes_record():
    job_id = "cost-job-003"
    jobstore.create_job(
        job_id, stage="transcribing", progress=20, message="等待中",
        assemblyai_transcript_id="aai-3",
        assemblyai_model="universal-2", assemblyai_diarization_enabled=False,
        user_id="user@example.com",
    )
    # 故意不設 duration_sec，模擬舊資料/例外流程
    with patch("progress._fetch_transcript_status_once", return_value=_completed_transcript()):
        client.get(f"/api/status/{job_id}")

    items = _transcription_items_for(job_id)
    assert len(items) == 1
    assert items[0]["pricing_unavailable"] is True
    assert items[0]["estimated_cost"] is None
    assert items[0]["duration_sec"] is None


def test_estimate_transcription_cost_returns_none_when_duration_missing():
    assert usage.estimate_transcription_cost("universal-2", False, None) is None


def test_estimate_transcription_cost_returns_none_for_unknown_combo():
    assert usage.estimate_transcription_cost("unknown-model", False, 3600.0) is None


# ─── finalize_claimed 併發收尾鎖 ──────────────────────────────────────


def test_finalize_claim_lock_prevents_duplicate_claims():
    job_id = "cost-job-race"
    jobstore.create_job(
        job_id, stage="transcribing", progress=20, message="等待中",
        assemblyai_transcript_id="aai-race", duration_sec=3600.0,
        assemblyai_model="universal-2", assemblyai_diarization_enabled=False,
        user_id="user@example.com",
    )
    assert jobstore.claim_finalize(job_id) is True
    # 第二次搶鎖必須失敗（DynamoDB ConditionExpression 保證只有一個成功）
    assert jobstore.claim_finalize(job_id) is False


def test_concurrent_status_polls_only_record_cost_once():
    """模擬兩個併發 /api/status 請求都通過『stage==transcribing』檢查、且都判斷
    AssemblyAI 已完成的情境（風險註記 #3）：真正的併發窗口發生在兩個請求各自呼叫
    `claim_finalize` 的當下（DynamoDB ConditionExpression 保證只有一個成功），
    這裡直接模擬第二個請求搶鎖失敗，驗證它不會重複組裝 segments／記費，
    而是直接回傳（第一個請求寫入後的）目前狀態。"""
    job_id = "cost-job-concurrent"
    jobstore.create_job(
        job_id, stage="transcribing", progress=20, message="等待中",
        assemblyai_transcript_id="aai-concurrent", duration_sec=3600.0,
        assemblyai_model="universal-2", assemblyai_diarization_enabled=False,
        user_id="user@example.com",
    )

    import progress as progress_module

    job = jobstore.get_job(job_id)
    real_claim_finalize = jobstore.claim_finalize
    with patch("progress._fetch_transcript_status_once", return_value=_completed_transcript()), \
         patch("jobstore.claim_finalize", side_effect=[True, False]) as mock_claim:
        first = progress_module._finalize_if_transcription_done(job)
        # 第二個併發呼叫仍然看到 job.stage == "transcribing"（用同一份 job snapshot 模擬
        # 兩個請求幾乎同時讀到同一狀態），但這次 claim_finalize 搶鎖失敗
        second = progress_module._finalize_if_transcription_done(job)

    assert mock_claim.call_count == 2
    assert first["stage"] == "transcribed"
    assert second["stage"] == "transcribed"  # 讀到第一個呼叫已寫入的最終狀態
    items = _transcription_items_for(job_id)
    assert len(items) == 1  # 只記了一筆成本，沒有重複記帳

    # 額外確認底層 DynamoDB ConditionExpression 本身也具備這個保證（不只是本測試的 mock）
    jobstore.create_job(
        "cost-job-concurrent-real-lock", stage="transcribing", progress=20, message="等待中",
    )
    assert real_claim_finalize("cost-job-concurrent-real-lock") is True
    assert real_claim_finalize("cost-job-concurrent-real-lock") is False


# ─── user_id 於上傳時寫入；assemblyai_model/diarization 於送出時釘住 ──


def test_upload_captures_user_id_at_upload_time(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    wav_header = (
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    with patch("upload.get_audio_duration", return_value=60.0):
        response = client.post(
            "/api/upload",
            files={"file": ("meeting.wav", wav_header, "audio/wav")},
        )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    job = jobstore.get_job(job_id)
    assert job["user_id"] == "test-user@example.com"


def test_upload_complete_captures_user_id_at_upload_time(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    monkeypatch.setattr("config.AUDIO_BUCKET_NAME", "test-audio-bucket")

    wav_header = (
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    job_id = "55555555-5555-5555-5555-555555555555"

    def fake_download_file(bucket, key, local_path):
        Path(local_path).write_bytes(wav_header)

    fake_s3 = MagicMock()
    fake_s3.download_file.side_effect = fake_download_file

    with patch("upload._s3_client", return_value=fake_s3), \
         patch("upload.get_audio_duration", return_value=42.0):
        response = client.post(
            "/api/upload/complete",
            json={"job_id": job_id, "s3_key": f"{job_id}/audio.wav", "filename": "meeting.wav"},
        )

    assert response.status_code == 200
    job = jobstore.get_job(job_id)
    assert job["user_id"] == "test-user@example.com"


def test_transcribe_pins_model_and_diarization_at_submit_time():
    job_id = "pin-job-001"
    jobstore.create_job(
        job_id, filename="meeting.mp3", duration_sec=60.0,
        audio_path="/tmp/pin-job-001/audio.mp3",
    )

    with patch("transcribe._submit_to_assemblyai", return_value="aai-pin"):
        response = client.post("/api/transcribe", json={"job_id": job_id})

    assert response.status_code == 200
    job = jobstore.get_job(job_id)
    assert job["assemblyai_model"] == config.ASSEMBLYAI_MODEL
    assert job["assemblyai_diarization_enabled"] == config.ASSEMBLYAI_SPEAKER_DIARIZATION


def test_old_job_without_pinned_model_falls_back_to_current_config():
    """舊 job（本story上線前已在 transcribing、沒有 assemblyai_model/
    assemblyai_diarization_enabled 欄位）收尾時應退回讀取目前 config.*，
    而不是永遠 pricing_unavailable。"""
    job_id = "cost-job-legacy"
    jobstore.create_job(
        job_id, stage="transcribing", progress=20, message="等待中",
        assemblyai_transcript_id="aai-legacy", duration_sec=1800.0,
        user_id="user@example.com",
    )
    with patch("progress._fetch_transcript_status_once", return_value=_completed_transcript()):
        client.get(f"/api/status/{job_id}")

    items = _transcription_items_for(job_id)
    assert len(items) == 1
    assert items[0]["model"] == config.ASSEMBLYAI_MODEL
    assert items[0]["pricing_unavailable"] is False
