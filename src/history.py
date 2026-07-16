"""會議紀錄歷史 API（TASK-009）。

處理「保留/刪除」選擇、歷史清單查詢、手動刪除，皆以目前登入使用者（email）做資料隔離。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

import db
import jobstore
from auth import CurrentUser, get_current_user

router = APIRouter()


def _load_job_result(job_id: str) -> tuple[str, str, str]:
    """讀取指定 job 的逐字稿、會議紀錄與標題，找不到則丟 404。"""
    job = jobstore.get_job(job_id)
    if job is None or job.get("segments") is None or job.get("minutes") is None:
        raise HTTPException(status_code=404, detail="找不到會議紀錄，請先完成 /summarize")

    segments = job["segments"]
    minutes_json = json.dumps(job["minutes"], ensure_ascii=False)
    transcript_text = "\n".join(
        f"[{seg.get('speaker') or 'SPEAKER'}] {seg['text']}" for seg in segments
    )
    title = job.get("filename", job_id)

    return title, transcript_text, minutes_json


@router.post("/meetings/{job_id}/keep")
async def keep_meeting(job_id: str, user: CurrentUser = Depends(get_current_user)):
    """使用者選擇保留本次會議紀錄，寫入 DynamoDB 並設定 14 天 TTL。"""
    title, transcript_text, minutes_json = _load_job_result(job_id)
    item = db.put_meeting(
        user_id=user.email,
        title=title,
        transcript_text=transcript_text,
        minutes_json=minutes_json,
    )
    return {"meeting_id": item["meeting_id"], "expires_at": item["expires_at"]}


@router.post("/meetings/{job_id}/discard")
async def discard_meeting(job_id: str, user: CurrentUser = Depends(get_current_user)):
    """使用者選擇不保留，僅回應成功，不寫入歷史紀錄。"""
    return {"status": "discarded"}


@router.get("/meetings")
async def list_meetings(user: CurrentUser = Depends(get_current_user)):
    """列出目前登入使用者自己的（未過期）歷史紀錄。"""
    items = db.list_meetings(user_id=user.email)
    return {
        "meetings": [
            {
                "meeting_id": i["meeting_id"],
                "title": i["title"],
                "created_at": i["created_at"],
                "expires_at": i["expires_at"],
            }
            for i in items
        ]
    }


@router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str, user: CurrentUser = Depends(get_current_user)):
    """取得單筆會議紀錄完整內容。"""
    item = db.get_meeting(user_id=user.email, meeting_id=meeting_id)
    if item is None:
        raise HTTPException(status_code=404, detail="找不到此會議紀錄")
    return {
        "meeting_id": item["meeting_id"],
        "title": item["title"],
        "transcript_text": item["transcript_text"],
        "minutes": json.loads(item["minutes_json"]),
        "expires_at": item["expires_at"],
    }


@router.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: str, user: CurrentUser = Depends(get_current_user)):
    """使用者手動提前刪除自己的歷史紀錄。"""
    deleted = db.delete_meeting(user_id=user.email, meeting_id=meeting_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到此會議紀錄")
    return {"status": "deleted"}
