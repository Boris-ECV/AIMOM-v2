"""音檔轉錄（TASK-005，v2 起改為非同步送出，見 TASK-016）。

`/transcribe` 只負責把音檔送交 AssemblyAI（`Transcriber.submit()`，非阻塞、
立即回傳），實際完成的判斷與逐字稿組裝挪到 `/api/status` 輪詢時處理
（見 `progress.py`），避免卡在 API Gateway HTTP API 30 秒的硬性 timeout。
"""
import asyncio
from fastapi import APIRouter, HTTPException
from models import TranscribeRequest, StatusResponse, TranscriptResultResponse, Segment
import config
import jobstore
from progress import update_progress
from transcript_utils import build_transcription_config

router = APIRouter()


def _submit_to_assemblyai(job: dict) -> str:
    """送出轉錄工作給 AssemblyAI，回傳 transcript_id。非阻塞（poll=False），
    送出後立即拿到 id，不等待轉錄完成。"""
    import assemblyai as aai

    aai.settings.api_key = config.ASSEMBLYAI_API_KEY
    aai_config = build_transcription_config()
    transcriber = aai.Transcriber()

    s3_key = job.get("s3_key")
    if s3_key and config.AUDIO_BUCKET_NAME:
        # S3 直傳流程（TASK-015）：簽發 presigned GET URL，讓 AssemblyAI 自行
        # 從 S3 非同步抓取音檔，Lambda 不需要下載/搬移音檔位元組
        import boto3
        audio_source = boto3.client("s3").generate_presigned_url(
            "get_object",
            Params={"Bucket": config.AUDIO_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=config.AUDIO_PRESIGN_EXPIRES_SEC,
        )
    else:
        # legacy 直傳流程：音檔仍在本機 /tmp（僅適用於同一 container 內處理，
        # 為已知限制，見 TASK-016 說明）
        audio_source = job.get("audio_path")
        if not audio_source:
            raise RuntimeError("找不到音檔來源，無法送交轉錄")

    transcript = transcriber.submit(audio_source, aai_config)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI 送出失敗：{transcript.error}")

    return transcript.id


@router.post("/transcribe", response_model=StatusResponse)
async def transcribe(req: TranscribeRequest):
    job_id = req.job_id
    job = jobstore.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_id 不存在")

    update_progress(job_id, "transcribing", 15, "準備送交 AssemblyAI...")

    try:
        loop = asyncio.get_event_loop()
        transcript_id = await loop.run_in_executor(None, _submit_to_assemblyai, job)
    except RuntimeError as e:
        update_progress(job_id, "error", job.get("progress", 15), str(e))
        raise HTTPException(status_code=500, detail=str(e))

    job = jobstore.update_job(
        job_id,
        stage="transcribing",
        progress=20,
        message="已送交 AssemblyAI，等待轉錄完成...",
        assemblyai_transcript_id=transcript_id,
    )

    return StatusResponse(job_id=job_id, stage=job["stage"], progress=job["progress"], message=job["message"])


@router.get("/transcript/{job_id}", response_model=TranscriptResultResponse)
async def get_transcript(job_id: str):
    """取得已完成的逐字稿結果（TASK-016）。轉錄是否完成由 /api/status 輪詢時
    向 AssemblyAI 查詢並寫回 job 狀態，這裡只單純讀取已組好的結果。"""
    job = jobstore.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_id 不存在")

    if job.get("stage") in ("uploaded", "transcribing"):
        raise HTTPException(status_code=409, detail="轉錄尚未完成，請稍後再試")

    segments = job.get("segments")
    if segments is None:
        raise HTTPException(status_code=404, detail="找不到逐字稿結果")

    return TranscriptResultResponse(
        job_id=job_id,
        stage=job["stage"],
        segments=[Segment(**s) for s in segments],
        full_text=job.get("full_text", ""),
    )
