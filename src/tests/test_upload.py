import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app

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
