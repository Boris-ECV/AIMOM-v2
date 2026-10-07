"""管理者專屬 API（TASK-011）。"""
from __future__ import annotations

import re

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, field_validator

import allowed_users
from auth import CurrentUser, require_admin
import usage

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AllowedUserCreate(BaseModel):
    email: str

    @field_validator("email", mode="before")
    @classmethod
    def _normalize(cls, v):
        if isinstance(v, str):
            return allowed_users.normalize_email(v)
        return v

    @field_validator("email")
    @classmethod
    def _check_format(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("email 格式不正確")
        return v


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="白名單資料表暫時無法存取")


@router.get("/admin/usage")
async def get_usage_summary(user: CurrentUser = Depends(require_admin)):
    """僅管理者可存取：回傳依日期/使用者彙總的 LLM 用量與估算成本。"""
    return usage.summarize_usage()


@router.get("/admin/allowed-users")
async def list_allowed_users(user: CurrentUser = Depends(require_admin)):
    """僅管理者可存取：列出登入白名單（依 email 排序）。"""
    try:
        return allowed_users.list_users()
    except (ClientError, BotoCoreError):
        raise _unavailable()


@router.post("/admin/allowed-users")
async def add_allowed_user(
    body: AllowedUserCreate,
    response: Response,
    user: CurrentUser = Depends(require_admin),
):
    """新增白名單 email：新增回 201；已存在回 200（冪等，不覆寫）。"""
    try:
        item, created = allowed_users.add_user(body.email)
    except (ClientError, BotoCoreError):
        raise _unavailable()
    response.status_code = 201 if created else 200
    return item


@router.delete("/admin/allowed-users/{email}", status_code=204)
async def delete_allowed_user(email: str, user: CurrentUser = Depends(require_admin)):
    """移除白名單 email；不在清單回 404。"""
    e = allowed_users.normalize_email(email)
    if not e:
        raise HTTPException(status_code=404, detail="找不到此 email")
    try:
        removed = allowed_users.remove_user(e)
    except (ClientError, BotoCoreError):
        raise _unavailable()
    if not removed:
        raise HTTPException(status_code=404, detail="找不到此 email")
    return Response(status_code=204)
