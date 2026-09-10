"""SDLCAIP2-20：轉錄後講者姓名對應 API（後端）測試。"""
import json
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
import jobstore

client = TestClient(app)

SAMPLE_SEGMENTS = [
    {"start": 0.0, "end": 5.0, "text": "大家好", "speaker": "SPEAKER_A"},
    {"start": 5.0, "end": 10.0, "text": "今天開會", "speaker": "SPEAKER_B"},
]


def _setup_job():
    job_id = "speaker-names-job-001"
    jobstore.create_job(job_id, stage="transcribed", progress=75, message="ok", segments=SAMPLE_SEGMENTS)
    return job_id


def test_speaker_names_updates_segments_for_mapped_speaker():
    """Scenario: 提交講者姓名對應後，job 的 segments 更新為指定姓名"""
    job_id = _setup_job()

    response = client.post(
        "/api/speaker-names",
        json={"job_id": job_id, "speaker_names": {"SPEAKER_A": "王小明"}},
    )

    assert response.status_code == 200
    data = response.json()
    speaker_a_segments = [s for s in data["segments"] if s["text"] == "大家好"]
    assert speaker_a_segments[0]["speaker"] == "王小明"

    job = jobstore.get_job(job_id)
    updated = [s for s in job["segments"] if s["text"] == "大家好"]
    assert updated[0]["speaker"] == "王小明"


def test_speaker_names_unmapped_speaker_keeps_original_label():
    """Scenario: 未命名的講者維持原始標籤"""
    job_id = _setup_job()

    response = client.post(
        "/api/speaker-names",
        json={"job_id": job_id, "speaker_names": {"SPEAKER_A": "王小明"}},
    )

    assert response.status_code == 200
    data = response.json()
    speaker_b_segments = [s for s in data["segments"] if s["text"] == "今天開會"]
    assert speaker_b_segments[0]["speaker"] == "SPEAKER_B"


def test_speaker_names_reflected_in_summarize():
    """Scenario: 重新呼叫 /summarize 後反映新姓名"""
    job_id = _setup_job()

    client.post(
        "/api/speaker-names",
        json={"job_id": job_id, "speaker_names": {"SPEAKER_A": "王小明", "SPEAKER_B": "李小華"}},
    )

    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "meeting_info": {"date": "", "time": "", "location": "", "participants": ["王小明", "李小華"]},
        "summary": "會議摘要",
        "action_items": [{"owner": "王小明", "task": "整理紀錄", "due": ""}],
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
    assert data["meeting_info"]["participants"] == ["王小明", "李小華"]
    assert data["action_items"][0]["owner"] == "王小明"


def test_speaker_names_job_not_transcribed_returns_400():
    """Scenario: job 尚未完成轉錄時呼叫此 API"""
    job_id = "not-transcribed-job"
    jobstore.create_job(job_id)

    response = client.post(
        "/api/speaker-names",
        json={"job_id": job_id, "speaker_names": {"SPEAKER_A": "王小明"}},
    )

    assert response.status_code == 400
    assert "轉錄" in response.json()["detail"]


def test_speaker_names_ignores_unknown_speaker_label():
    """Scenario: 提交的講者標籤與 job 內實際標籤不符"""
    job_id = _setup_job()

    response = client.post(
        "/api/speaker-names",
        json={"job_id": job_id, "speaker_names": {"SPEAKER_C": "陌生人"}},
    )

    assert response.status_code == 200
    data = response.json()
    speakers_present = {s["speaker"] for s in data["segments"]}
    assert speakers_present == {"SPEAKER_A", "SPEAKER_B"}
    assert "陌生人" not in speakers_present


def test_speaker_names_mixed_known_and_unknown_labels_applies_known_only():
    """Edge case: 混合已知與未知標籤時，已知的正常套用，未知的靜默忽略。"""
    job_id = _setup_job()

    response = client.post(
        "/api/speaker-names",
        json={"job_id": job_id, "speaker_names": {"SPEAKER_A": "王小明", "SPEAKER_C": "陌生人"}},
    )

    assert response.status_code == 200
    data = response.json()
    speakers_present = {s["speaker"] for s in data["segments"]}
    assert speakers_present == {"王小明", "SPEAKER_B"}


def test_speaker_names_empty_mapping_leaves_segments_unchanged():
    """Edge case: 提交空的對應字典，不應變更任何 segment。"""
    job_id = _setup_job()

    response = client.post(
        "/api/speaker-names",
        json={"job_id": job_id, "speaker_names": {}},
    )

    assert response.status_code == 200
    data = response.json()
    speakers_present = {s["speaker"] for s in data["segments"]}
    assert speakers_present == {"SPEAKER_A", "SPEAKER_B"}


def test_speaker_names_job_not_found_returns_400():
    """Edge case: job_id 不存在時，回傳 400 而非 500。"""
    response = client.post(
        "/api/speaker-names",
        json={"job_id": "does-not-exist", "speaker_names": {"SPEAKER_A": "王小明"}},
    )

    assert response.status_code == 400
