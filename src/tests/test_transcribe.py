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
    {"start": 0.0, "end": 5.0, "text": "今天的議題是技術選型", "speaker": "SPEAKER_A"},
    {"start": 5.0, "end": 10.0, "text": "決定使用 AssemblyAI", "speaker": "SPEAKER_B"},
]


def _setup_job(tmp_path):
    job_id = "transcribe-job-001"
    job_dir = tmp_path / job_id
    job_dir.mkdir(parents=True)
    meta = {
        "filename": "meeting.mp3",
        "duration_sec": 60.0,
        "size_bytes": 1024,
        "created_at": "2026-01-01T00:00:00",
        "audio_path": str(job_dir / "audio.mp3"),
        "suffix": ".mp3",
    }
    (job_dir / "meta.json").write_text(json.dumps(meta))
    (job_dir / "audio.mp3").write_bytes(b"\x00" * 100)
    return job_id


def _make_mock_transcript(segments):
    """Build a mock AssemblyAI transcript object."""
    mock_utt = []
    for s in segments:
        utt = MagicMock()
        utt.start = int(s["start"] * 1000)
        utt.end = int(s["end"] * 1000)
        utt.text = s["text"]
        utt.speaker = s["speaker"].replace("SPEAKER_", "")
        mock_utt.append(utt)

    mock_transcript = MagicMock()
    mock_transcript.status.name = "completed"
    mock_transcript.utterances = mock_utt
    mock_transcript.text = " ".join(s["text"] for s in segments)
    mock_transcript.id = "aai-transcript-001"

    import assemblyai as aai
    mock_transcript.status = aai.TranscriptStatus.completed
    return mock_transcript


def test_transcribe_no_job(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    response = client.post("/api/transcribe", json={"job_id": "nonexistent"})
    assert response.status_code == 404


def test_transcribe_success(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    monkeypatch.setattr("config.ASSEMBLYAI_API_KEY", "test-key")
    job_id = _setup_job(tmp_path)

    mock_transcript = _make_mock_transcript(SAMPLE_SEGMENTS)

    with patch("transcribe._run_assemblyai",
               return_value=([{"start": 0.0, "end": 5.0, "text": "今天的議題", "speaker": "SPEAKER_A"}],
                             "今天的議題", "aai-001")):
        response = client.post("/api/transcribe", json={"job_id": job_id})

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert len(data["segments"]) == 1
    assert data["segments"][0]["speaker"] == "SPEAKER_A"


def test_transcript_id_saved_to_meta(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    monkeypatch.setattr("config.ASSEMBLYAI_API_KEY", "test-key")
    job_id = _setup_job(tmp_path)

    with patch("transcribe._run_assemblyai",
               return_value=([{"start": 0.0, "end": 5.0, "text": "test", "speaker": "SPEAKER_A"}],
                             "test", "aai-transcript-xyz")):
        client.post("/api/transcribe", json={"job_id": job_id})

    meta = json.loads((tmp_path / job_id / "meta.json").read_text(encoding="utf-8"))
    assert meta.get("assemblyai_transcript_id") == "aai-transcript-xyz"
