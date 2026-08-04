"""LLM engine 設定測試。"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch

import config


def test_get_llm_client_bedrock_proxy(monkeypatch):
    monkeypatch.setattr(config, "LLM_ENGINE", "bedrock-proxy")
    monkeypatch.setattr(config, "BEDROCK_PROXY_BASE_URL", "https://proxy.example/v1")
    monkeypatch.setattr(config, "BEDROCK_PROXY_API_KEY", "proxy-key")

    with patch("openai.OpenAI") as mock_openai:
        client = config.get_llm_client()

    mock_openai.assert_called_once_with(base_url="https://proxy.example/v1", api_key="proxy-key")
    assert client == mock_openai.return_value
