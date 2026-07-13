import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from models import StatusResponse, CleanupResponse
import assemblyai as aai
import config

router = APIRouter()


def update_progress(job_id: str, stage: str, progress: int, message: str):
    status_path = Path(config.TMP_DIR) / job_id / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps({
        "stage": stage,
        "progress": progress,
        "message": message,
        "updated_at": datetime.utcnow().isoformat()
    }, ensure_ascii=False), encoding="utf-8")


def read_status(job_id: str) -> dict:
    status_path = Path(config.TMP_DIR) / job_id / "status.json"
    if not status_path.exists():
        raise HTTPException(status_code=404, detail="job_id 不存在")
    return json.loads(status_path.read_text(encoding="utf-8"))


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    s = read_status(job_id)
    return StatusResponse(job_id=job_id, **s)


@router.delete("/cleanup/{job_id}", response_model=CleanupResponse)
async def cleanup(job_id: str):
    job_dir = Path(config.TMP_DIR) / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="job_id 不存在")

    # Delete AssemblyAI transcript for privacy (NFR-01)
    meta_path = job_dir / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            transcript_id = meta.get("assemblyai_transcript_id")
            if transcript_id and config.ASSEMBLYAI_API_KEY:
                aai.settings.api_key = config.ASSEMBLYAI_API_KEY
                aai.Transcript.delete(transcript_id)
        except Exception:
            pass  # Don't fail local cleanup if remote delete fails

    shutil.rmtree(job_dir)
    return CleanupResponse(deleted=True, job_id=job_id)
