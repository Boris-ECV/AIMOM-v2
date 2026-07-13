"""登入與角色驗證模組（TASK-008）。

驗證 Amazon Cognito（聯合 Google 登入）簽發的 JWT，解析出使用者 email，
並依白名單環境變數 ADMIN_EMAILS 判定角色（user / admin）。
"""
from __future__ import annotations

import time
from typing import Callable, Literal, Optional

import requests
from fastapi import Depends, Header, HTTPException
from jose import jwt
from pydantic import BaseModel

import config

_JWKS_CACHE: dict = {"keys": None, "fetched_at": 0}
_JWKS_TTL_SECONDS = 3600


class CurrentUser(BaseModel):
    """已驗證的目前使用者。"""

    email: str
    role: Literal["user", "admin"]


def _cognito_issuer() -> str:
    return (
        f"https://cognito-idp.{config.COGNITO_REGION}.amazonaws.com/"
        f"{config.COGNITO_USER_POOL_ID}"
    )


def _default_jwks_provider() -> dict:
    """向 Cognito JWKS 端點取得公鑰，並做簡單快取（避免每次請求都打外部 API）。"""
    now = time.time()
    if _JWKS_CACHE["keys"] and now - _JWKS_CACHE["fetched_at"] < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]

    url = f"{_cognito_issuer()}/.well-known/jwks.json"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    keys = resp.json()
    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["fetched_at"] = now
    return keys


def _get_admin_emails() -> set[str]:
    raw = config.ADMIN_EMAILS or ""
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def verify_token(token: str, jwks_provider: Callable[[], dict] = _default_jwks_provider) -> CurrentUser:
    """驗證 JWT 並回傳 CurrentUser，任何失敗都拋出 ValueError（由呼叫端轉成 401）。"""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"無效的 token 格式: {exc}") from exc

    jwks = jwks_provider()
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == unverified_header.get("kid")), None)
    if key is None:
        raise ValueError("找不到對應的簽章金鑰")

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=config.COGNITO_APP_CLIENT_ID,
            issuer=_cognito_issuer(),
            options={"verify_aud": bool(config.COGNITO_APP_CLIENT_ID)},
        )
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"token 驗證失敗: {exc}") from exc

    email = payload.get("email")
    if not email:
        raise ValueError("token 缺少 email claim")

    role = "admin" if email.lower() in _get_admin_emails() else "user"
    return CurrentUser(email=email, role=role)


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> CurrentUser:
    """FastAPI dependency：解析並驗證 Authorization header，回傳目前使用者。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="未授權，請重新登入")

    token = authorization.split(" ", 1)[1].strip()
    try:
        return verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="未授權，請重新登入") from exc


async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """FastAPI dependency：確保目前使用者是管理者角色，否則回傳 403。"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="僅限管理者存取")
    return user
