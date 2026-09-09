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
    "meeting_info": {
        "date": "2026-08-04",
        "time": "14:00",
        "location": "3樓會議室",
        "participants": ["王小明", "李小華"],
    },
    "summary": "本次會議討論了技術選型，決定使用 FastAPI 框架。",
    "action_items": [{"owner": "王小明", "task": "建立 FastAPI 專案", "due": "下週五"}],
    "decisions": ["使用 FastAPI 框架"],
    "sections": [{"title": "技術選型", "content": "比較了 Flask 和 FastAPI"}],
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
    assert data["template"] == "general"
    assert data["sections"] == [{"title": "技術選型", "content": "比較了 Flask 和 FastAPI"}]
    assert data["meeting_info"] == {
        "date": "2026-08-04",
        "time": "14:00",
        "location": "3樓會議室",
        "participants": ["王小明", "李小華"],
    }


def test_summarize_no_transcript():
    job_id = "empty-job"
    jobstore.create_job(job_id)
    response = client.post("/api/summarize", json={"job_id": job_id})
    assert response.status_code == 400


def test_summarize_normalizes_malformed_llm_payload():
    job_id = _setup_job()

    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "meeting_info": {"date": None, "time": "10:00", "location": None, "participants": ["王小明", None, "  "]},
        "summary": "  摘要內容  ",
        "action_items": ["建立 FastAPI 專案", {"owner": None, "task": "整理文件", "due": None}],
        "decisions": ["  採用 FastAPI  ", None],
        "sections": ["技術選型", {"title": None, "content": "比較 Flask 與 FastAPI"}],
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
    assert data["sections"][0] == {"title": "技術選型", "content": ""}
    assert data["meeting_info"] == {
        "date": "",
        "time": "10:00",
        "location": "",
        "participants": ["王小明"],
    }


def test_summarize_meeting_info_missing_defaults_to_unmentioned():
    """AI 未提供 meeting_info（例如逐字稿完全沒提到會議資訊）時，
    不應臆測填入任何值，全部欄位維持空字串/空陣列。"""
    job_id = _setup_job()

    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "summary": "簡短摘要",
        "action_items": [],
        "decisions": [],
        "sections": [],
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
    assert data["meeting_info"] == {
        "date": "",
        "time": "",
        "location": "",
        "participants": [],
    }


def test_summarize_action_item_due_left_blank_when_unmentioned():
    """action_items 的 owner/due 若逐字稿未明講，應維持空字串，不可被臆測填入日期或人名。"""
    job_id = _setup_job()

    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "meeting_info": {},
        "summary": "簡短摘要",
        "action_items": [{"owner": "", "task": "調查方案", "due": ""}],
        "decisions": [],
        "sections": [],
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
    assert data["action_items"][0] == {"owner": "", "task": "調查方案", "due": ""}


def test_summarize_llm_client_failure_sets_error_state():
    job_id = _setup_job()

    with patch("config.get_llm_client", side_effect=RuntimeError("boom")):
        response = client.post("/api/summarize", json={"job_id": job_id})

    assert response.status_code == 503
    body = response.json()
    assert "AI 摘要服務暫時無法使用" in body["detail"]

    job = jobstore.get_job(job_id)
    assert job["stage"] == "error"


def test_summarize_with_retro_template_returns_fixed_sections():
    """AC1: 選擇內建模板後，AI 產出對應結構的區塊（Keep/Problem/Try，順序定案）。"""
    job_id = _setup_job()

    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "meeting_info": {"date": "", "time": "", "location": "", "participants": []},
        "summary": "回顧會議摘要",
        "action_items": [],
        "decisions": [],
        "sections": [
            {"title": "Problem", "content": "部署流程太慢"},
            {"title": "Keep", "content": "每日站會維持"},
            # LLM 未提到 Try，_normalize_sections 應補上空字串
        ],
    })
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("config.get_llm_client", return_value=mock_client):
        response = client.post("/api/summarize", json={"job_id": job_id, "template": "retro"})

    assert response.status_code == 200
    data = response.json()
    assert data["template"] == "retro"
    assert [s["title"] for s in data["sections"]] == ["Keep", "Problem", "Try"]
    assert data["sections"] == [
        {"title": "Keep", "content": "每日站會維持"},
        {"title": "Problem", "content": "部署流程太慢"},
        {"title": "Try", "content": ""},
    ]
    for section in data["sections"]:
        assert "title" in section
        assert "content" in section


def test_summarize_without_template_defaults_to_general_and_stays_compatible():
    """AC2: 不指定模板時維持向下相容，套用預設「一般會議」，
    meeting_info、action_items 欄位不變。"""
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
    assert data["template"] == "general"
    assert data["meeting_info"] == {
        "date": "2026-08-04",
        "time": "14:00",
        "location": "3樓會議室",
        "participants": ["王小明", "李小華"],
    }
    assert data["action_items"] == [
        {"owner": "王小明", "task": "建立 FastAPI 專案", "due": "下週五"}
    ]
    assert data["sections"] == [{"title": "技術選型", "content": "比較了 Flask 和 FastAPI"}]


def test_summarize_with_null_template_also_defaults_to_general():
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
        response = client.post("/api/summarize", json={"job_id": job_id, "template": None})

    assert response.status_code == 200
    assert response.json()["template"] == "general"


def test_summarize_with_unknown_template_returns_400_before_calling_llm():
    """AC3: 指定不存在的模板代碼，回傳 400，訊息列出可用的模板代碼清單；
    驗證發生在呼叫 LLM 之前。"""
    job_id = _setup_job()

    mock_client = MagicMock()

    with patch("config.get_llm_client", return_value=mock_client) as mock_get_client:
        response = client.post("/api/summarize", json={"job_id": job_id, "template": "not_exist"})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "not_exist" in detail
    for code in ["brainstorm", "client_meeting", "general", "project_status", "retro"]:
        assert code in detail
    mock_get_client.assert_not_called()
    mock_client.chat.completions.create.assert_not_called()


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
