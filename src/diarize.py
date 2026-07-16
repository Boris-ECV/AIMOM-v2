from fastapi import APIRouter, HTTPException
from models import DiarizeRequest, DiarizeResponse, Segment
import jobstore
from progress import update_progress

router = APIRouter()


@router.post("/diarize", response_model=DiarizeResponse)
async def diarize(req: DiarizeRequest):
    """
    v2.0: AssemblyAI already provides speaker labels during /transcribe.
    This endpoint reads the already-stored job segments and returns speaker info.
    Kept for API backward compatibility.
    """
    job_id = req.job_id
    job = jobstore.get_job(job_id)
    if job is None or job.get("segments") is None:
        raise HTTPException(status_code=400, detail="請先執行 /transcribe 並等待轉錄完成")

    segments = job["segments"]
    speakers = sorted(set(
        s.get("speaker", "SPEAKER_A") for s in segments if s.get("speaker")
    ))

    update_progress(job_id, "diarized", 75, f"發言人識別完成，共 {len(speakers)} 位")

    return DiarizeResponse(
        job_id=job_id,
        speakers=speakers or ["SPEAKER_A"],
        segments=[Segment(**s) for s in segments],
    )
