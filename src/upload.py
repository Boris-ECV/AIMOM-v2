import json
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException
from models import UploadResponse
import config

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a"}
MAX_DURATION_SEC = config.MAX_DURATION_HOURS * 3600


def get_audio_duration(file_path: Path) -> float:
    """Return duration in seconds using mutagen, fallback to 0."""
    try:
        from mutagen import File as MutaFile
        audio = MutaFile(str(file_path))
        if audio and audio.info:
            return float(audio.info.length)
    except Exception:
        pass
    return 0.0


@router.post("/upload", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支援的格式，請上傳 MP3/WAV/M4A")

    job_id = str(uuid.uuid4())
    job_dir = Path(config.TMP_DIR) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    audio_path = job_dir / f"audio{suffix}"
    content = await file.read()
    audio_path.write_bytes(content)

    duration = get_audio_duration(audio_path)
    if duration > MAX_DURATION_SEC:
        import shutil
        shutil.rmtree(job_dir)
        raise HTTPException(status_code=400, detail=f"錄音超過 {config.MAX_DURATION_HOURS} 小時上限")

    meta = {
        "filename": file.filename,
        "duration_sec": duration,
        "size_bytes": len(content),
        "created_at": datetime.utcnow().isoformat(),
        "audio_path": str(audio_path),
        "suffix": suffix,
    }
    (job_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    from progress import update_progress
    update_progress(job_id, "uploaded", 10, "上傳完成，等待轉錄")

    return UploadResponse(
        job_id=job_id,
        filename=file.filename,
        duration_sec=duration,
        size_bytes=len(content),
    )
