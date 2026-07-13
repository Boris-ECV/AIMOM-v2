import os
from dotenv import load_dotenv

load_dotenv()

# AssemblyAI (v2.0 — replaces OpenAI Whisper + pyannote)
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
ASSEMBLYAI_MODEL = os.getenv("ASSEMBLYAI_MODEL", "universal-2")
ASSEMBLYAI_SPEAKER_DIARIZATION = os.getenv("ASSEMBLYAI_SPEAKER_DIARIZATION", "true").lower() == "true"

# LLM
# 可選值：
#   - "github-models"：透過 GitHub Models（OpenAI 相容端點），使用 GitHub PAT 呼叫，
#     適合已有 GitHub Copilot Business/Enterprise 訂閱的情境（較高 rate limit）
#   - "openai-gpt4o"：原本的 OpenAI 官方 API 做法，保留可切換
#   - "groq"：Groq（OpenAI 相容端點），成本低、速度快
#   - "gemini"：Google Gemini（OpenAI 相容端點），有免費額度
LLM_ENGINE = os.getenv("LLM_ENGINE", "github-models")
LLM_MODEL = os.getenv("LLM_MODEL", "")  # 空字串則依 LLM_ENGINE 使用預設模型
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_MODELS_BASE_URL = os.getenv("GITHUB_MODELS_BASE_URL", "https://models.github.ai/inference")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

_DEFAULT_MODELS = {
    "github-models": "openai/gpt-4o",
    "openai-gpt4o": "gpt-4o",
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
}

# App limits
MAX_DURATION_HOURS = float(os.getenv("MAX_DURATION_HOURS", "2"))
TMP_DIR = os.getenv("TMP_DIR", "tmp")


def get_llm_client():
    import openai

    if LLM_ENGINE == "github-models":
        if not GITHUB_TOKEN:
            raise ValueError("LLM_ENGINE=github-models 需要設定 GITHUB_TOKEN（需具備 models scope 的 PAT）")
        return openai.OpenAI(base_url=GITHUB_MODELS_BASE_URL, api_key=GITHUB_TOKEN)
    if LLM_ENGINE == "openai-gpt4o":
        return openai.OpenAI(api_key=OPENAI_API_KEY)
    if LLM_ENGINE == "groq":
        if not GROQ_API_KEY:
            raise ValueError("LLM_ENGINE=groq 需要設定 GROQ_API_KEY")
        return openai.OpenAI(base_url=GROQ_BASE_URL, api_key=GROQ_API_KEY)
    if LLM_ENGINE == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("LLM_ENGINE=gemini 需要設定 GEMINI_API_KEY")
        return openai.OpenAI(base_url=GEMINI_BASE_URL, api_key=GEMINI_API_KEY)
    raise ValueError(f"Unsupported LLM_ENGINE: {LLM_ENGINE}")


def get_llm_model() -> str:
    """回傳目前 LLM_ENGINE 應使用的模型名稱，可用 LLM_MODEL 覆寫。"""
    return LLM_MODEL or _DEFAULT_MODELS.get(LLM_ENGINE, "gpt-4o")
