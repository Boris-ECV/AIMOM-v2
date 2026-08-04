import os
from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

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
#   - "bedrock-proxy"：OpenAI 相容的 Bedrock proxy，使用 API key 與 base URL
LLM_ENGINE = _env("LLM_ENGINE", "bedrock-proxy")
LLM_MODEL = _env("LLM_MODEL")  # 空字串則依 LLM_ENGINE 使用預設模型
OPENAI_API_KEY = _env("OPENAI_API_KEY")
GITHUB_TOKEN = _env("GITHUB_TOKEN")
GITHUB_MODELS_BASE_URL = _env("GITHUB_MODELS_BASE_URL", "https://models.github.ai/inference")
GROQ_API_KEY = _env("GROQ_API_KEY")
GROQ_BASE_URL = _env("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GEMINI_API_KEY = _env("GEMINI_API_KEY")
GEMINI_BASE_URL = _env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
BEDROCK_PROXY_API_KEY = _env("BEDROCK_PROXY_API_KEY")
BEDROCK_PROXY_BASE_URL = _env("BEDROCK_PROXY_BASE_URL")

_DEFAULT_MODELS = {
    "github-models": "openai/gpt-4o",
    "openai-gpt4o": "gpt-4o",
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
    "bedrock-proxy": "mistral.mistral-large-3-675b-instruct",
}

# App limits
MAX_DURATION_HOURS = float(os.getenv("MAX_DURATION_HOURS", "2"))
TMP_DIR = os.getenv("TMP_DIR", "tmp")

# 音檔暫存 S3 bucket（TASK-015 — presigned URL 直傳，繞過 API Gateway/Lambda payload 上限）
AUDIO_BUCKET_NAME = os.getenv("AUDIO_BUCKET_NAME", "")
AUDIO_PRESIGN_EXPIRES_SEC = int(os.getenv("AUDIO_PRESIGN_EXPIRES_SEC", "600"))

# 登入與角色（TASK-008 — Cognito + Google 聯合登入）
COGNITO_REGION = os.getenv("COGNITO_REGION", "ap-northeast-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID", "")
ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "")  # 逗號分隔白名單，判定管理者角色

# DynamoDB（TASK-009/011/016）
DYNAMODB_MEETINGS_TABLE = os.getenv("DYNAMODB_MEETINGS_TABLE", "aimom-meetings")
DYNAMODB_LLM_USAGE_TABLE = os.getenv("DYNAMODB_LLM_USAGE_TABLE", "aimom-llm-usage")
DYNAMODB_JOBS_TABLE = os.getenv("DYNAMODB_JOBS_TABLE", "aimom-jobs")
MEETING_RETENTION_DAYS = int(os.getenv("MEETING_RETENTION_DAYS", "14"))


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
    if LLM_ENGINE == "bedrock-proxy":
        if not BEDROCK_PROXY_BASE_URL:
            raise ValueError("LLM_ENGINE=bedrock-proxy 需要設定 BEDROCK_PROXY_BASE_URL")
        if not BEDROCK_PROXY_API_KEY:
            raise ValueError("LLM_ENGINE=bedrock-proxy 需要設定 BEDROCK_PROXY_API_KEY")
        return openai.OpenAI(base_url=BEDROCK_PROXY_BASE_URL, api_key=BEDROCK_PROXY_API_KEY)
    raise ValueError(f"Unsupported LLM_ENGINE: {LLM_ENGINE}")


def get_llm_model() -> str:
    """回傳目前 LLM_ENGINE 應使用的模型名稱，可用 LLM_MODEL 覆寫。"""
    return LLM_MODEL or _DEFAULT_MODELS.get(LLM_ENGINE, "gpt-4o")
