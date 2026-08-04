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


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _normalize_action_items(raw_items) -> list[dict]:
    if not isinstance(raw_items, list):
        return []

    normalized: list[dict] = []
    for item in raw_items:
        if isinstance(item, dict):
            normalized.append(
                {
                    "owner": _text(item.get("owner")),
                    "task": _text(item.get("task")),
                    "due": _text(item.get("due")),
                }
            )
        elif isinstance(item, str) and item.strip():
            normalized.append({"owner": "", "task": item.strip(), "due": ""})
    return normalized


def _normalize_topics(raw_topics) -> list[dict]:
    if not isinstance(raw_topics, list):
        return []

    normalized: list[dict] = []
    for item in raw_topics:
        if isinstance(item, dict):
            normalized.append(
                {
                    "title": _text(item.get("title")),
                    "content": _text(item.get("content")),
                }
            )
        elif isinstance(item, str) and item.strip():
            normalized.append({"title": item.strip(), "content": ""})
    return normalized


def _normalize_decisions(raw_decisions) -> list[str]:
    if not isinstance(raw_decisions, list):
        return []
    return [_text(item) for item in raw_decisions if _text(item)]


def _format_llm_error(exc: Exception) -> str:
    status_code = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    response_text = ""
    if response is not None:
        response_text = getattr(response, "text", "") or ""
        if not response_text:
            content = getattr(response, "content", None)
            if content is not None:
                try:
                    response_text = content.decode("utf-8", errors="replace")
                except Exception:  # noqa: BLE001
                    response_text = str(content)
    detail = str(exc)
    if status_code:
        detail = f"HTTP {status_code} - {detail}"
    if response_text and response_text not in detail:
        detail = f"{detail} | response={response_text}"
    return detail


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
    model = config.get_llm_model()

    update_progress(job_id, "summarizing", 70, "正在 AI 整理會議紀錄...")
    try:
        client = config.get_llm_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"逐字稿如下：\n\n{transcript_text}"},
            ],
            temperature=0.3,
        )
    except ValueError as exc:
        jobstore.update_job(
            job_id,
            stage="error",
            progress=70,
            message=f"AI 摘要設定錯誤：{exc}",
        )
        raise HTTPException(status_code=500, detail=f"AI 摘要設定錯誤：{exc}") from exc
    except Exception as exc:  # noqa: BLE001 - 外部 LLM 服務失敗需明確回傳給前端
        detail = _format_llm_error(exc)
        jobstore.update_job(
            job_id,
            stage="error",
            progress=70,
            message=f"AI 摘要服務失敗：{detail}",
        )
        raise HTTPException(status_code=503, detail=f"AI 摘要服務暫時無法使用：{detail}") from exc

    raw = response.choices[0].message.content
    data = _parse_llm_response(raw)
    summary = _text(data.get("summary"))
    action_items = _normalize_action_items(data.get("action_items"))
    decisions = _normalize_decisions(data.get("decisions"))
    topics = _normalize_topics(data.get("topics"))

    try:
        usage_info = response.usage
        record_llm_usage(
            engine=config.LLM_ENGINE,
            model=model,
            input_tokens=getattr(usage_info, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage_info, "completion_tokens", 0) or 0,
            user_id=user.email,
            meeting_id=job_id,
        )
    except Exception:  # noqa: BLE001 — 用量記錄失敗不應阻擋摘要功能
        pass

    minutes = {
        "job_id": job_id,
        "summary": summary,
        "action_items": action_items,
        "decisions": decisions,
        "topics": topics,
    }
    jobstore.update_job(job_id, stage="done", progress=100, message="會議紀錄整理完成", minutes=minutes)

    return SummarizeResponse(
        job_id=job_id,
        summary=summary,
        action_items=[ActionItem(**a) for a in action_items],
        decisions=decisions,
        topics=[Topic(**t) for t in topics],
    )
