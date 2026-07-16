"""任務進度查詢與清除（TASK-005，v2 起改用 DynamoDB 儲存狀態，見 TASK-016）。"""
from fastapi import APIRouter, HTTPException
from models import StatusResponse, CleanupResponse
import assemblyai as aai
import config
import jobstore
from transcript_utils import build_segments_from_transcript

router = APIRouter()


def update_progress(job_id: str, stage: str, progress: int, message: str):
    """更新 job 進度。維持既有函式簽名，內部改寫入 DynamoDB（TASK-016）。"""
    jobstore.update_job(job_id, stage=stage, progress=progress, message=message)


def read_status(job_id: str) -> dict:
    job = jobstore.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_id 不存在")
    return job


def _finalize_if_transcription_done(job: dict) -> dict:
    """輪詢 `/api/status` 時，若目前是 transcribing 階段，順便向 AssemblyAI
    查詢一次目前狀態（單次查詢，非阻塞）；完成的話在這裡才組出逐字稿、
    寫回 job 狀態（TASK-016：/api/transcribe 已改為非同步送出，實際完成的
    判斷與收尾動作挪到這裡，而不是留在原本會阻塞的 /transcribe 呼叫裡）。
    """
    if job.get("stage") != "transcribing":
        return job

    transcript_id = job.get("assemblyai_transcript_id")
    if not transcript_id:
        return job

    aai.settings.api_key = config.ASSEMBLYAI_API_KEY
    transcript = aai.Transcript.get_by_id(transcript_id)

    if transcript.status == aai.TranscriptStatus.error:
        return jobstore.update_job(
            job["job_id"], stage="error", progress=job.get("progress", 20),
            message=f"AssemblyAI 轉錄失敗：{transcript.error}",
        )

    if transcript.status != aai.TranscriptStatus.completed:
        # 仍在 AssemblyAI 佇列中或處理中，狀態不變，前端繼續輪詢即可
        return job

    segments, full_text = build_segments_from_transcript(transcript)
    unique_speakers = len(set(s["speaker"] for s in segments if s.get("speaker")))
    return jobstore.update_job(
        job["job_id"],
        stage="transcribed",
        progress=75,
        message=f"轉錄完成，共 {len(segments)} 段，{unique_speakers} 位說話者",
        segments=segments,
        full_text=full_text,
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    job = read_status(job_id)
    job = _finalize_if_transcription_done(job)
    return StatusResponse(job_id=job_id, stage=job["stage"], progress=job["progress"], message=job["message"])


@router.delete("/cleanup/{job_id}", response_model=CleanupResponse)
async def cleanup(job_id: str):
    job = jobstore.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_id 不存在")

    # Delete AssemblyAI transcript for privacy (NFR-01)
    transcript_id = job.get("assemblyai_transcript_id")
    if transcript_id and config.ASSEMBLYAI_API_KEY:
        try:
            aai.settings.api_key = config.ASSEMBLYAI_API_KEY
            aai.Transcript.delete_by_id(transcript_id)
        except Exception:
            pass  # Don't fail cleanup if remote delete fails

    # 刪除 S3 暫存音檔（若尚未被 1 天 lifecycle 清掉）
    s3_key = job.get("s3_key")
    if s3_key and config.AUDIO_BUCKET_NAME:
        try:
            import boto3
            boto3.client("s3").delete_object(Bucket=config.AUDIO_BUCKET_NAME, Key=s3_key)
        except Exception:
            pass

    jobstore.delete_job(job_id)
    return CleanupResponse(deleted=True, job_id=job_id)
