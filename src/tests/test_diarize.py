import pytest
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
    job_id = "diarize-job-001"
    # v2.0: transcript already contains speaker labels from AssemblyAI
    jobstore.create_job(job_id, stage="transcribed", progress=75, message="ok", segments=SAMPLE_SEGMENTS)
    return job_id


def test_diarize_reads_existing_speakers():
    """v2.0: diarize reads AssemblyAI results already stored in the job (TASK-016)."""
    job_id = _setup_job()

    response = client.post("/api/diarize", json={"job_id": job_id})
    assert response.status_code == 200
    data = response.json()
    assert set(data["speakers"]) == {"SPEAKER_A", "SPEAKER_B"}
    assert all(s["speaker"] in ("SPEAKER_A", "SPEAKER_B") for s in data["segments"])


def test_diarize_no_transcript():
    job_id = "no-transcript-job"
    jobstore.create_job(job_id)

    response = client.post("/api/diarize", json={"job_id": job_id})
    assert response.status_code == 400
