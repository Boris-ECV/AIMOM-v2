import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
import jobstore

client = TestClient(app)


def _setup_job(s3_key=None, audio_path=None):
    job_id = "transcribe-job-001"
    jobstore.create_job(
        job_id,
        filename="meeting.mp3",
        duration_sec=60.0,
        size_bytes=1024,
        s3_key=s3_key,
        audio_path=audio_path or "/tmp/transcribe-job-001/audio.mp3",
    )
    return job_id


def test_transcribe_no_job():
    response = client.post("/api/transcribe", json={"job_id": "nonexistent"})
    assert response.status_code == 404


def test_transcribe_submits_and_returns_ack(monkeypatch):
    """TASK-016: /transcribe 只送出工作並立即回應，不等待轉錄完成。"""
    monkeypatch.setattr("config.ASSEMBLYAI_API_KEY", "test-key")
    job_id = _setup_job()

    with patch("transcribe._submit_to_assemblyai", return_value="aai-transcript-xyz"):
        response = client.post("/api/transcribe", json={"job_id": job_id})

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["stage"] == "transcribing"

    job = jobstore.get_job(job_id)
    assert job["assemblyai_transcript_id"] == "aai-transcript-xyz"
    assert job["stage"] == "transcribing"


def test_transcribe_uses_presigned_s3_url_when_available(monkeypatch):
    """TASK-016: 若 job 有 s3_key，應簽發 presigned GET URL 讓 AssemblyAI 自行抓取，
    而不是把本機音檔路徑直接傳給 AssemblyAI。"""
    monkeypatch.setattr("config.ASSEMBLYAI_API_KEY", "test-key")
    monkeypatch.setattr("config.AUDIO_BUCKET_NAME", "test-audio-bucket")
    job_id = _setup_job(s3_key=f"{__name__}/audio.mp3")

    fake_s3 = MagicMock()
    fake_s3.generate_presigned_url.return_value = "https://example.com/presigned-get"

    mock_transcript = MagicMock()
    import assemblyai as aai
    mock_transcript.status = aai.TranscriptStatus.queued
    mock_transcript.id = "aai-transcript-s3"

    mock_transcriber = MagicMock()
    mock_transcriber.submit.return_value = mock_transcript

    with patch("boto3.client", return_value=fake_s3), \
         patch("assemblyai.Transcriber", return_value=mock_transcriber):
        response = client.post("/api/transcribe", json={"job_id": job_id})

    assert response.status_code == 200
    fake_s3.generate_presigned_url.assert_called_once()
    mock_transcriber.submit.assert_called_once()
    called_source = mock_transcriber.submit.call_args[0][0]
    assert called_source == "https://example.com/presigned-get"


def test_transcript_not_ready_returns_409():
    job_id = _setup_job()
    response = client.get(f"/api/transcript/{job_id}")
    assert response.status_code == 409


def test_transcript_returns_result_when_ready():
    job_id = "transcribe-job-ready"
    jobstore.create_job(
        job_id,
        stage="transcribed",
        progress=75,
        message="ok",
        segments=[{"start": 0.0, "end": 5.0, "text": "hello", "speaker": "SPEAKER_A"}],
        full_text="hello",
    )
    response = client.get(f"/api/transcript/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "transcribed"
    assert data["full_text"] == "hello"
    assert len(data["segments"]) == 1
