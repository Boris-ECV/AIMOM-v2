import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from progress import update_progress
import jobstore

client = TestClient(app)


def test_status_not_found():
    response = client.get("/api/status/nonexistent-id")
    assert response.status_code == 404


def test_status_returns_progress():
    job_id = "progress-job-001"
    jobstore.create_job(job_id)
    update_progress(job_id, "transcribing", 30, "AssemblyAI 處理中...")
    response = client.get(f"/api/status/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "transcribing"
    assert data["progress"] == 30


def test_status_finalizes_transcription_when_assemblyai_done():
    """TASK-016：輪詢 /api/status 時，若 AssemblyAI 已完成，應自動組出逐字稿並把
    stage 更新為 transcribed，不需要另外呼叫 /api/transcribe 才能拿到結果。"""
    job_id = "progress-job-002"
    jobstore.create_job(job_id, stage="transcribing", progress=20,
                         message="等待中", assemblyai_transcript_id="aai-xyz")

    mock_transcript = MagicMock()
    mock_transcript.utterances = None
    mock_transcript.words = []
    mock_transcript.text = "hello world"

    import assemblyai as aai
    mock_transcript.status = aai.TranscriptStatus.completed

    with patch("progress._fetch_transcript_status_once", return_value=mock_transcript):
        response = client.get(f"/api/status/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "transcribed"
    assert data["progress"] == 75

    job = jobstore.get_job(job_id)
    assert job["full_text"] == "hello world"


def test_status_still_transcribing_when_assemblyai_not_done():
    job_id = "progress-job-003"
    jobstore.create_job(job_id, stage="transcribing", progress=20,
                         message="等待中", assemblyai_transcript_id="aai-abc")

    mock_transcript = MagicMock()
    import assemblyai as aai
    mock_transcript.status = aai.TranscriptStatus.processing

    with patch("progress._fetch_transcript_status_once", return_value=mock_transcript):
        response = client.get(f"/api/status/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "transcribing"


def test_status_survives_transient_assemblyai_query_error():
    """TASK-016 回歸測試：查詢 AssemblyAI 狀態本身失敗（例如網路暫時性錯誤）
    不應該讓整個 /api/status 500，應維持現有狀態讓前端下次輪詢重試。"""
    job_id = "progress-job-004"
    jobstore.create_job(job_id, stage="transcribing", progress=20,
                         message="等待中", assemblyai_transcript_id="aai-def")

    with patch("progress._fetch_transcript_status_once", side_effect=RuntimeError("boom")):
        response = client.get(f"/api/status/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "transcribing"


def test_cleanup_success():
    job_id = "cleanup-job-001"
    jobstore.create_job(job_id)
    response = client.delete(f"/api/cleanup/{job_id}")
    assert response.status_code == 200
    assert jobstore.get_job(job_id) is None


def test_cleanup_calls_assemblyai_delete(monkeypatch):
    """Verify AssemblyAI transcript is deleted on cleanup (NFR-01 privacy)."""
    monkeypatch.setattr("config.ASSEMBLYAI_API_KEY", "test-key")
    job_id = "cleanup-aai-job"
    jobstore.create_job(job_id, assemblyai_transcript_id="aai-transcript-abc")

    with patch("progress.aai") as mock_aai:
        mock_aai.settings = MagicMock()
        mock_aai.Transcript = MagicMock()
        response = client.delete(f"/api/cleanup/{job_id}")

    assert response.status_code == 200
    mock_aai.Transcript.delete_by_id.assert_called_once_with("aai-transcript-abc")


def test_cleanup_not_found():
    response = client.delete("/api/cleanup/nonexistent-id")
    assert response.status_code == 404
