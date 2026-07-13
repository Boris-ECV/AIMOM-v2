import json
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException
from models import TranscribeRequest, TranscribeResponse, Segment
import config
from progress import update_progress

router = APIRouter()


def _run_assemblyai(audio_path: str, job_id: str) -> tuple[list[dict], str, str]:
    """Run AssemblyAI transcription synchronously. Returns (segments, full_text, transcript_id)."""
    import assemblyai as aai

    aai.settings.api_key = config.ASSEMBLYAI_API_KEY

    # AssemblyAI API 已棄用單一 speech_model 參數，改用 speech_models（字串清單）
    # 見：https://www.assemblyai.com/docs/pre-recorded-audio/select-the-speech-model
    aai_config = aai.TranscriptionConfig(
        speech_models=[config.ASSEMBLYAI_MODEL],
        language_code="zh",
        speaker_labels=config.ASSEMBLYAI_SPEAKER_DIARIZATION,
    )

    update_progress(job_id, "transcribing", 20, "音檔上傳至 AssemblyAI...")
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_path, aai_config)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI 轉錄失敗：{transcript.error}")

    update_progress(job_id, "transcribing", 65, "AssemblyAI 轉錄完成，整理結果...")

    segments = []
    if transcript.utterances:
        for utt in transcript.utterances:
            segments.append({
                "start": round(utt.start / 1000, 3),
                "end": round(utt.end / 1000, 3),
                "text": utt.text.strip(),
                "speaker": f"SPEAKER_{utt.speaker}",
            })
    elif transcript.words:
        # fallback: group words into segments without speaker labels
        for word in transcript.words:
            segments.append({
                "start": round(word.start / 1000, 3),
                "end": round(word.end / 1000, 3),
                "text": word.text,
                "speaker": "SPEAKER_A",
            })

    return segments, transcript.text or "", transcript.id


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(req: TranscribeRequest):
    job_id = req.job_id
    job_dir = Path(config.TMP_DIR) / job_id
    meta_path = job_dir / "meta.json"

    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="job_id 不存在")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    audio_path = meta["audio_path"]

    update_progress(job_id, "transcribing", 15, "準備送交 AssemblyAI...")

    try:
        loop = asyncio.get_event_loop()
        segments, full_text, transcript_id = await loop.run_in_executor(
            None, _run_assemblyai, audio_path, job_id
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Save transcript_id for cleanup (privacy)
    meta["assemblyai_transcript_id"] = transcript_id
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    # Save segments to disk
    (job_dir / "transcript.json").write_text(
        json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    unique_speakers = len(set(s["speaker"] for s in segments if s.get("speaker")))
    update_progress(job_id, "transcribed", 75,
                    f"轉錄完成，共 {len(segments)} 段，{unique_speakers} 位說話者")

    return TranscribeResponse(
        job_id=job_id,
        segments=[Segment(**s) for s in segments],
        full_text=full_text,
    )
