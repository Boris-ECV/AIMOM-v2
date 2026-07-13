import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app

client = TestClient(app)

SAMPLE_SEGMENTS = [
    {"start": 0.0, "end": 5.0, "text": "今天的議題是技術選型", "speaker": "SPEAKER_00"},
    {"start": 5.0, "end": 10.0, "text": "我們決定使用 FastAPI", "speaker": "SPEAKER_01"},
]

MOCK_LLM_RESPONSE = json.dumps({
    "summary": "本次會議討論了技術選型，決定使用 FastAPI 框架。",
    "action_items": [{"owner": "王小明", "task": "建立 FastAPI 專案", "due": "下週五"}],
    "decisions": ["使用 FastAPI 框架"],
    "topics": [{"title": "技術選型", "content": "比較了 Flask 和 FastAPI"}],
})


def _setup_job(tmp_path):
    job_id = "summarize-job-001"
    job_dir = tmp_path / job_id
    job_dir.mkdir(parents=True)
    (job_dir / "transcript.json").write_text(json.dumps(SAMPLE_SEGMENTS))
    return job_id


def test_summarize_success(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    job_id = _setup_job(tmp_path)

    mock_message = MagicMock()
    mock_message.content = MOCK_LLM_RESPONSE
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("config.get_llm_client", return_value=mock_client):
        response = client.post("/api/summarize", json={"job_id": job_id})

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert len(data["action_items"]) == 1
    assert data["decisions"] == ["使用 FastAPI 框架"]


def test_summarize_no_transcript(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    job_id = "empty-job"
    (tmp_path / job_id).mkdir()
    response = client.post("/api/summarize", json={"job_id": job_id})
    assert response.status_code == 400
