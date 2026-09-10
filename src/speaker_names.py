from fastapi import APIRouter, HTTPException

import jobstore
from models import Segment, SpeakerNamesRequest, SpeakerNamesResponse

router = APIRouter()


@router.post("/speaker-names", response_model=SpeakerNamesResponse)
async def apply_speaker_names(req: SpeakerNamesRequest):
    """轉錄完成後，套用使用者提交的「講者標籤 → 姓名」對應（SDLCAIP2-20）。

    就地覆寫 segments 的 speaker 欄位：只有出現在目前 segments 中的標籤才會
    被套用，job 內不存在的標籤靜默忽略、不報錯（AC5）。
    """
    job_id = req.job_id
    job = jobstore.get_job(job_id)
    if job is None or job.get("segments") is None:
        raise HTTPException(status_code=400, detail="請先執行 /transcribe 並等待轉錄完成")

    segments = job["segments"]
    speaker_names = req.speaker_names

    updated_segments = [
        {**s, "speaker": speaker_names[s["speaker"]]}
        if s.get("speaker") in speaker_names
        else s
        for s in segments
    ]

    jobstore.update_job(job_id, segments=updated_segments)

    speakers = sorted({
        s.get("speaker") for s in updated_segments if s.get("speaker")
    })

    return SpeakerNamesResponse(
        job_id=job_id,
        speakers=speakers,
        segments=[Segment(**s) for s in updated_segments],
    )
