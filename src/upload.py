import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException
from models import (
    UploadResponse,
    UploadPresignRequest,
    UploadPresignResponse,
    UploadCompleteRequest,
)
import config
import jobstore

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a"}
MAX_DURATION_SEC = config.MAX_DURATION_HOURS * 3600

CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
}


def _s3_client():
    import boto3
    return boto3.client("s3")


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


def _finalize_upload(job_id: str, job_dir: Path, audio_path: Path, filename: str, suffix: str, s3_key: str = None) -> UploadResponse:
    """驗證音檔長度、寫入 job 狀態（DynamoDB，見 TASK-016）。供 legacy 直傳與 presign 流程共用。"""
    size_bytes = audio_path.stat().st_size
    duration = get_audio_duration(audio_path)
    if duration > MAX_DURATION_SEC:
        import shutil
        shutil.rmtree(job_dir)
        raise HTTPException(status_code=400, detail=f"錄音超過 {config.MAX_DURATION_HOURS} 小時上限")

    jobstore.create_job(
        job_id,
        filename=filename,
        duration_sec=duration,
        size_bytes=size_bytes,
        created_at=datetime.utcnow().isoformat(),
        audio_path=str(audio_path),
        suffix=suffix,
        s3_key=s3_key,
    )

    return UploadResponse(
        job_id=job_id,
        filename=filename,
        duration_sec=duration,
        size_bytes=size_bytes,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    """既有的直傳端點：檔案先整包送進 Lambda，受 API Gateway/Lambda payload 上限（約 4-5MB）限制。

    保留供小檔案／本機開發使用；正式前端流程已改用 /upload/presign + /upload/complete
    （TASK-015），大檔案請走該流程以繞過此限制。
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支援的格式，請上傳 MP3/WAV/M4A")

    job_id = str(uuid.uuid4())
    job_dir = Path(config.TMP_DIR) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    audio_path = job_dir / f"audio{suffix}"
    content = await file.read()
    audio_path.write_bytes(content)

    return _finalize_upload(job_id, job_dir, audio_path, file.filename, suffix)


@router.post("/upload/presign", response_model=UploadPresignResponse)
async def presign_upload(req: UploadPresignRequest):
    """簽發 S3 Presigned PUT URL，讓瀏覽器直接上傳音檔到 S3，繞過 API Gateway/Lambda
    payload 上限（TASK-015）。"""
    suffix = Path(req.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支援的格式，請上傳 MP3/WAV/M4A")
    if not config.AUDIO_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="伺服器未設定 AUDIO_BUCKET_NAME，無法簽發上傳網址")

    job_id = str(uuid.uuid4())
    s3_key = f"{job_id}/audio{suffix}"
    content_type = CONTENT_TYPES.get(suffix, "application/octet-stream")

    try:
        upload_url = _s3_client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": config.AUDIO_BUCKET_NAME,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=config.AUDIO_PRESIGN_EXPIRES_SEC,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"簽發上傳網址失敗：{e}")

    return UploadPresignResponse(
        job_id=job_id,
        upload_url=upload_url,
        s3_key=s3_key,
        content_type=content_type,
    )


@router.post("/upload/complete", response_model=UploadResponse)
async def complete_upload(req: UploadCompleteRequest):
    """瀏覽器完成 S3 直傳後呼叫：從 S3 下載音檔到 /tmp、驗證長度、寫入 meta.json，
    後續 /transcribe 等端點不需變更，仍讀取本機暫存的音檔（TASK-015）。"""
    suffix = Path(req.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支援的格式，請上傳 MP3/WAV/M4A")
    if not config.AUDIO_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="伺服器未設定 AUDIO_BUCKET_NAME")

    try:
        job_uuid = uuid.UUID(req.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="job_id 格式不正確")

    # s3_key 必須是 presign 端點依 job_id 產生的既定命名（job_id/audioXXX），
    # 拒絕任何不符合此規則的值，避免呼叫端夾帶其他 job/使用者的 s3_key 或路徑跳脫字元
    expected_s3_key = f"{job_uuid}/audio{suffix}"
    if req.s3_key != expected_s3_key:
        raise HTTPException(status_code=400, detail="s3_key 與 job_id 不相符")

    job_dir = Path(config.TMP_DIR) / str(job_uuid)
    job_dir.mkdir(parents=True, exist_ok=True)
    audio_path = job_dir / f"audio{suffix}"

    try:
        _s3_client().download_file(config.AUDIO_BUCKET_NAME, req.s3_key, str(audio_path))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"找不到已上傳的音檔物件（{req.s3_key}）：{e}")

    # 注意：這裡故意不刪除 S3 物件 —— /transcribe 會用 presigned GET URL 讓
    # AssemblyAI 非同步去抓取這個物件（TASK-016），過早刪除會有競態風險。
    # 暫存物件的清除交給 bucket 既有的 1 天 lifecycle 規則，或使用者手動
    # /api/cleanup/{job_id} 時一併清除。
    return _finalize_upload(str(job_uuid), job_dir, audio_path, req.filename, suffix, s3_key=req.s3_key)
