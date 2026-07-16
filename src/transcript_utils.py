"""AssemblyAI 轉錄結果的共用處理邏輯（TASK-016）。

抽出成獨立模組，供 `transcribe.py`（送出轉錄工作）與 `progress.py`
（輪詢 `/api/status` 時檢查 AssemblyAI 是否已完成、並組出逐字稿）共用，
避免兩者互相 import 造成循環匯入。
"""
from __future__ import annotations

import config


def build_transcription_config():
    """建立 AssemblyAI 轉錄設定，供 submit()/transcribe() 共用。

    AssemblyAI API 已棄用單一 speech_model 參數，改用 speech_models（字串清單）。
    見：https://www.assemblyai.com/docs/pre-recorded-audio/select-the-speech-model
    """
    import assemblyai as aai

    return aai.TranscriptionConfig(
        speech_models=[config.ASSEMBLYAI_MODEL],
        language_code="zh",
        speaker_labels=config.ASSEMBLYAI_SPEAKER_DIARIZATION,
    )


def build_segments_from_transcript(transcript) -> tuple[list[dict], str]:
    """把已完成的 AssemblyAI Transcript 物件轉成本專案慣用的 segments 格式。

    回傳 (segments, full_text)。
    """
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

    return segments, transcript.text or ""
