import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
import jobstore

client = TestClient(app)


def test_upload_invalid_format(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", b"fake content", "text/plain")},
    )
    assert response.status_code == 400
    assert "不支援" in response.json()["detail"]


def test_upload_valid_file(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    # 使用最小合法的 WAV header（44 bytes）
    wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    with patch("upload.get_audio_duration", return_value=60.0):
        response = client.post(
            "/api/upload",
            files={"file": ("meeting.wav", wav_header, "audio/wav")},
        )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["filename"] == "meeting.wav"


def test_cleanup_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    response = client.delete("/api/cleanup/nonexistent-id")
    assert response.status_code == 404


# ─── TASK-015: presigned URL 直傳 ─────────────────────────

def test_presign_invalid_format(monkeypatch):
    monkeypatch.setattr("config.AUDIO_BUCKET_NAME", "test-audio-bucket")
    response = client.post("/api/upload/presign", json={"filename": "note.txt"})
    assert response.status_code == 400
    assert "不支援" in response.json()["detail"]


def test_presign_missing_bucket_config(monkeypatch):
    monkeypatch.setattr("config.AUDIO_BUCKET_NAME", "")
    response = client.post("/api/upload/presign", json={"filename": "meeting.wav"})
    assert response.status_code == 500


def test_presign_returns_upload_url(monkeypatch):
    monkeypatch.setattr("config.AUDIO_BUCKET_NAME", "test-audio-bucket")
    fake_s3 = MagicMock()
    fake_s3.generate_presigned_url.return_value = "https://test-audio-bucket.s3.amazonaws.com/fake-signed-url"
    with patch("upload._s3_client", return_value=fake_s3):
        response = client.post("/api/upload/presign", json={"filename": "meeting.wav"})

    assert response.status_code == 200
    data = response.json()
    assert data["upload_url"] == "https://test-audio-bucket.s3.amazonaws.com/fake-signed-url"
    assert data["s3_key"].endswith("/audio.wav")
    assert data["content_type"] == "audio/wav"
    assert data["job_id"] in data["s3_key"]

    # 確認有把 bucket/key/content-type 正確傳給 boto3
    _, kwargs = fake_s3.generate_presigned_url.call_args
    assert kwargs["Params"]["Bucket"] == "test-audio-bucket"
    assert kwargs["Params"]["ContentType"] == "audio/wav"


def test_complete_upload_downloads_from_s3_and_creates_job(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    monkeypatch.setattr("config.AUDIO_BUCKET_NAME", "test-audio-bucket")

    wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    job_id = "11111111-1111-1111-1111-111111111111"

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
    data = response.json()
    assert data["job_id"] == job_id
    assert data["duration_sec"] == 42.0
    fake_s3.download_file.assert_called_once_with("test-audio-bucket", f"{job_id}/audio.wav", str(tmp_path / job_id / "audio.wav"))
    # TASK-016: S3 物件不再於此立即刪除（/transcribe 之後才由 AssemblyAI 非同步抓取），
    # 只依賴 bucket 既有的 1 天 lifecycle 規則或 /api/cleanup 手動清除
    fake_s3.delete_object.assert_not_called()

    job = jobstore.get_job(job_id)
    assert job["s3_key"] == f"{job_id}/audio.wav"


def test_complete_upload_missing_s3_object_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    monkeypatch.setattr("config.AUDIO_BUCKET_NAME", "test-audio-bucket")

    job_id = "22222222-2222-2222-2222-222222222222"
    fake_s3 = MagicMock()
    fake_s3.download_file.side_effect = Exception("NoSuchKey")

    with patch("upload._s3_client", return_value=fake_s3):
        response = client.post(
            "/api/upload/complete",
            json={"job_id": job_id, "s3_key": f"{job_id}/audio.wav", "filename": "meeting.wav"},
        )

    assert response.status_code == 404


def test_complete_upload_rejects_invalid_job_id(monkeypatch):
    monkeypatch.setattr("config.AUDIO_BUCKET_NAME", "test-audio-bucket")
    response = client.post(
        "/api/upload/complete",
        json={"job_id": "not-a-uuid", "s3_key": "not-a-uuid/audio.wav", "filename": "meeting.wav"},
    )
    assert response.status_code == 400


def test_complete_upload_rejects_mismatched_s3_key(monkeypatch):
    monkeypatch.setattr("config.AUDIO_BUCKET_NAME", "test-audio-bucket")
    job_id = "33333333-3333-3333-3333-333333333333"
    other_job_id = "44444444-4444-4444-4444-444444444444"
    response = client.post(
        "/api/upload/complete",
        json={"job_id": job_id, "s3_key": f"{other_job_id}/audio.wav", "filename": "meeting.wav"},
    )
    assert response.status_code == 400
