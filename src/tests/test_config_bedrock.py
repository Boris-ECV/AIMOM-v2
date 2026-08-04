"""Bedrock proxy 設定測試。"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import config


def test_config_trims_env_values(monkeypatch):
    monkeypatch.setattr(config, "LLM_ENGINE", " bedrock-proxy ")
    monkeypatch.setattr(config, "LLM_MODEL", " mistral.mistral-large-3-675b-instruct ")
    monkeypatch.setattr(config, "BEDROCK_PROXY_BASE_URL", " https://example.com/v1 ")
    monkeypatch.setattr(config, "BEDROCK_PROXY_API_KEY", " key ")

    assert config.LLM_ENGINE.strip() == "bedrock-proxy"
    assert config.LLM_MODEL.strip() == "mistral.mistral-large-3-675b-instruct"
