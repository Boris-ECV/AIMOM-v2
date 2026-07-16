import json
from fastapi import APIRouter, Depends, HTTPException
from models import SummarizeRequest, SummarizeResponse, ActionItem, Topic
import config
import jobstore
from progress import update_progress
from auth import CurrentUser, get_current_user
from usage import record_llm_usage

router = APIRouter()

SYSTEM_PROMPT = """你是專業的會議記錄助手。請根據以下逐字稿，輸出 JSON 格式的會議紀錄。
JSON 必須包含以下欄位：
- summary: 字串，100-200 字的摘要
- action_items: 陣列，每項含 owner（負責人）、task（工作事項）、due（截止時間）
- decisions: 字串陣列，列出本次會議做出的決定
- topics: 陣列，每項含 title（議題標題）、content（議題重點）

所有文字請使用繁體中文回應。只輸出 JSON，不要其他說明文字。"""


def _build_transcript_text(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        speaker = seg.get("speaker") or "SPEAKER"
        lines.append(f"[{speaker}] {seg['text']}")
    return "\n".join(lines)


def _parse_llm_response(content: str) -> dict:
    """Try to parse JSON from LLM response, fallback to minimal structure."""
    try:
        # 有時 LLM 會包在 ```json ... ``` 中
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception:
        return {
            "summary": content[:500],
            "action_items": [],
            "decisions": [],
            "topics": [],
        }


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest, user: CurrentUser = Depends(get_current_user)):
    job_id = req.job_id
    job = jobstore.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_id 不存在")

    segments = job.get("segments")
    if segments is None:
        raise HTTPException(status_code=400, detail="請先執行 /transcribe 並等待轉錄完成")

    transcript_text = _build_transcript_text(segments)

    update_progress(job_id, "summarizing", 70, "正在 AI 整理會議紀錄...")
    client = config.get_llm_client()

    response = client.chat.completions.create(
        model=config.get_llm_model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"逐字稿如下：\n\n{transcript_text}"},
        ],
        temperature=0.3,
    )

    raw = response.choices[0].message.content
    data = _parse_llm_response(raw)

    try:
        usage_info = response.usage
        record_llm_usage(
            engine=config.LLM_ENGINE,
            model=config.get_llm_model(),
            input_tokens=getattr(usage_info, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage_info, "completion_tokens", 0) or 0,
            user_id=user.email,
            meeting_id=job_id,
        )
    except Exception:  # noqa: BLE001 — 用量記錄失敗不應阻擋摘要功能
        pass

    minutes = {**data, "job_id": job_id}
    jobstore.update_job(job_id, stage="done", progress=100, message="會議紀錄整理完成", minutes=minutes)

    return SummarizeResponse(
        job_id=job_id,
        summary=data.get("summary", ""),
        action_items=[ActionItem(**a) for a in data.get("action_items", [])],
        decisions=data.get("decisions", []),
        topics=[Topic(**t) for t in data.get("topics", [])],
    )
