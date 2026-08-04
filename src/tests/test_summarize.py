import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
import jobstore

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


def _setup_job():
    job_id = "summarize-job-001"
    jobstore.create_job(job_id, stage="transcribed", progress=75, message="ok", segments=SAMPLE_SEGMENTS)
    return job_id


def test_summarize_success():
    job_id = _setup_job()

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


def test_summarize_no_transcript():
    job_id = "empty-job"
    jobstore.create_job(job_id)
    response = client.post("/api/summarize", json={"job_id": job_id})
    assert response.status_code == 400


def test_summarize_normalizes_malformed_llm_payload():
    job_id = _setup_job()

    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "summary": "  摘要內容  ",
        "action_items": ["建立 FastAPI 專案", {"owner": None, "task": "整理文件", "due": None}],
        "decisions": ["  採用 FastAPI  ", None],
        "topics": ["技術選型", {"title": None, "content": "比較 Flask 與 FastAPI"}],
    })
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
    assert data["summary"] == "摘要內容"
    assert data["action_items"][0] == {"owner": "", "task": "建立 FastAPI 專案", "due": ""}
    assert data["decisions"] == ["採用 FastAPI"]
    assert data["topics"][0] == {"title": "技術選型", "content": ""}


def test_summarize_llm_client_failure_sets_error_state():
    job_id = _setup_job()

    with patch("config.get_llm_client", side_effect=RuntimeError("boom")):
        response = client.post("/api/summarize", json={"job_id": job_id})

    assert response.status_code == 503
    body = response.json()
    assert "AI 摘要服務暫時無法使用" in body["detail"]

    job = jobstore.get_job(job_id)
    assert job["stage"] == "error"


def test_summarize_llm_error_includes_status_and_response():
    job_id = _setup_job()

    class FakeResponse:
        text = '{"error":"model not found"}'

    class FakeError(Exception):
        status_code = 404
        response = FakeResponse()

    with patch("config.get_llm_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = FakeError("Not found")
        mock_client_factory.return_value = mock_client

        response = client.post("/api/summarize", json={"job_id": job_id})

    assert response.status_code == 503
    assert "HTTP 404" in response.json()["detail"]
    assert "model not found" in response.json()["detail"]
