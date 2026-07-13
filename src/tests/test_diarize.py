import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app

client = TestClient(app)

SAMPLE_SEGMENTS = [
    {"start": 0.0, "end": 5.0, "text": "大家好", "speaker": "SPEAKER_A"},
    {"start": 5.0, "end": 10.0, "text": "今天開會", "speaker": "SPEAKER_B"},
]


def _setup_job(tmp_path):
    job_id = "diarize-job-001"
    job_dir = tmp_path / job_id
    job_dir.mkdir(parents=True)
    # v2.0: transcript already contains speaker labels from AssemblyAI
    (job_dir / "transcript.json").write_text(json.dumps(SAMPLE_SEGMENTS))
    return job_id


def test_diarize_reads_existing_speakers(tmp_path, monkeypatch):
    """v2.0: diarize reads AssemblyAI results from transcript.json directly."""
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    job_id = _setup_job(tmp_path)

    response = client.post("/api/diarize", json={"job_id": job_id})
    assert response.status_code == 200
    data = response.json()
    assert set(data["speakers"]) == {"SPEAKER_A", "SPEAKER_B"}
    assert all(s["speaker"] in ("SPEAKER_A", "SPEAKER_B") for s in data["segments"])


def test_diarize_no_transcript(tmp_path, monkeypatch):
    monkeypatch.setattr("config.TMP_DIR", str(tmp_path))
    job_id = "no-transcript-job"
    (tmp_path / job_id).mkdir()

    response = client.post("/api/diarize", json={"job_id": job_id})
    assert response.status_code == 400
