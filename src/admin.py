"""管理者專屬 API（TASK-011）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from auth import CurrentUser, require_admin
import usage

router = APIRouter()


@router.get("/admin/usage")
async def get_usage_summary(user: CurrentUser = Depends(require_admin)):
    """僅管理者可存取：回傳依日期/使用者彙總的 LLM 用量與估算成本。"""
    return usage.summarize_usage()
