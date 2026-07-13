import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from models import DiarizeRequest, DiarizeResponse, Segment
import config
from progress import update_progress

router = APIRouter()


@router.post("/diarize", response_model=DiarizeResponse)
async def diarize(req: DiarizeRequest):
    """
    v2.0: AssemblyAI already provides speaker labels during /transcribe.
    This endpoint reads the existing transcript.json and returns speaker info.
    Kept for API backward compatibility.
    """
    job_id = req.job_id
    job_dir = Path(config.TMP_DIR) / job_id
    transcript_path = job_dir / "transcript.json"

    if not transcript_path.exists():
        raise HTTPException(status_code=400, detail="請先執行 /transcribe")

    segments = json.loads(transcript_path.read_text(encoding="utf-8"))
    speakers = sorted(set(
        s.get("speaker", "SPEAKER_A") for s in segments if s.get("speaker")
    ))

    update_progress(job_id, "diarized", 75, f"發言人識別完成，共 {len(speakers)} 位")

    return DiarizeResponse(
        job_id=job_id,
        speakers=speakers or ["SPEAKER_A"],
        segments=[Segment(**s) for s in segments],
    )
