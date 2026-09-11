"""SDLCAIP2-33：轉錄語言改用 AssemblyAI 自動偵測，取代寫死的中文。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from transcript_utils import build_transcription_config


def test_build_transcription_config_enables_language_detection():
    """啟用語言自動偵測：不寫死 language_code="zh"，language_detection 為 True，
    且不設定 language_confidence_threshold（避免 AssemblyAI 因低信心直接回傳錯誤）。"""
    cfg = build_transcription_config()

    assert getattr(cfg, "language_code", None) != "zh"
    assert cfg.language_detection is True
    assert getattr(cfg, "language_confidence_threshold", None) is None


def test_build_transcription_config_keeps_existing_settings():
    """既有設定不受影響：speech_models 與 speaker_labels 維持依 config.* 設定。"""
    cfg = build_transcription_config()

    assert cfg.speech_models == [config.ASSEMBLYAI_MODEL]
    assert cfg.speaker_labels == config.ASSEMBLYAI_SPEAKER_DIARIZATION
