import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from progress import update_progress

client = TestClient(app)


def test_status_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    response = client.get("/api/status/nonexistent-id")
    assert response.status_code == 404


def test_status_returns_progress(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    job_id = "progress-job-001"
    update_progress(job_id, "transcribing", 30, "AssemblyAI 處理中...")
    response = client.get(f"/api/status/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "transcribing"
    assert data["progress"] == 30


def test_cleanup_success(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    monkeypatch.setattr("config.ASSEMBLYAI_API_KEY", "test-key")
    job_id = "cleanup-job-001"
    job_dir = tmp_path / job_id
    job_dir.mkdir()
    (job_dir / "dummy.txt").write_text("hello")
    response = client.delete(f"/api/cleanup/{job_id}")
    assert response.status_code == 200
    assert not job_dir.exists()


def test_cleanup_calls_assemblyai_delete(tmp_path, monkeypatch):
    """Verify AssemblyAI transcript is deleted on cleanup (NFR-01 privacy)."""
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    monkeypatch.setattr("config.ASSEMBLYAI_API_KEY", "test-key")
    job_id = "cleanup-aai-job"
    job_dir = tmp_path / job_id
    job_dir.mkdir()
    meta = {"assemblyai_transcript_id": "aai-transcript-abc"}
    (job_dir / "meta.json").write_text(json.dumps(meta))

    with patch("progress.aai") as mock_aai:
        mock_aai.settings = MagicMock()
        mock_aai.Transcript = MagicMock()
        response = client.delete(f"/api/cleanup/{job_id}")

    assert response.status_code == 200
    mock_aai.Transcript.delete.assert_called_once_with("aai-transcript-abc")


def test_cleanup_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    response = client.delete("/api/cleanup/nonexistent-id")
    assert response.status_code == 404
