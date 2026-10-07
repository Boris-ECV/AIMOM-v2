"""管理者白名單（允許登入 email）資料存取層（SDLCAIP2-66）。

admin.py 只透過本模組存取 allowed-users 資料表。
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import boto3

import config

# 白名單記憶體快取（SDLCAIP2-67），仿 auth._JWKS_CACHE。
# 注意（跨 container 一致性）：Lambda 每個 container 各有獨立記憶體。add_user/remove_user
# 只會立即失效「處理該請求的那個 container」的快取；其他 container 不會被通知，
# 最多要等 CACHE_TTL_SECONDS（60 秒）TTL 過期後才會看到新增/移除。
CACHE_TTL_SECONDS = 60
_CACHE: dict = {"emails": None, "fetched_at": 0.0, "generation": 0}
_CACHE_LOCK = threading.Lock()


def normalize_email(raw: str) -> str:
    """strip + lowercase，與 auth.py 比對 email 的慣例一致。"""
    return raw.strip().lower()


def _resource():
    return boto3.resource("dynamodb", region_name=config.COGNITO_REGION)


def _table():
    return _resource().Table(config.DYNAMODB_ALLOWED_USERS_TABLE)


def ensure_allowed_users_table_exists() -> None:
    """建立 allowed-users 表（若不存在）。正式環境由 Terraform 建立（見 infra/dynamodb.tf），
    Lambda 角色不授予 ListTables/CreateTable，遇 AccessDeniedException 視為已由 IaC 建好。"""
    from botocore.exceptions import ClientError

    client = boto3.client("dynamodb", region_name=config.COGNITO_REGION)
    try:
        existing = client.list_tables().get("TableNames", [])
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "AccessDeniedException":
            return
        raise
    if config.DYNAMODB_ALLOWED_USERS_TABLE in existing:
        return

    client.create_table(
        TableName=config.DYNAMODB_ALLOWED_USERS_TABLE,
        KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=config.DYNAMODB_ALLOWED_USERS_TABLE)


def _is_conditional_failure(e) -> bool:
    return e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def list_users() -> list[dict]:
    """Scan（含分頁）全部白名單，依 email 升冪排序。"""
    ensure_allowed_users_table_exists()
    table = _table()
    items: list[dict] = []
    kwargs: dict = {}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return [
        {"email": i["email"], "last_login": i.get("last_login")}
        for i in sorted(items, key=lambda x: x["email"])
    ]


def get_all_emails() -> frozenset[str]:
    """回傳白名單 email 集合（小寫）。快取命中不碰 DynamoDB；查表失敗直接往上拋（不回傳過期快取）。"""
    with _CACHE_LOCK:
        if _CACHE["emails"] is not None and time.time() - _CACHE["fetched_at"] < CACHE_TTL_SECONDS:
            return _CACHE["emails"]
        generation = _CACHE["generation"]

    # I/O 在鎖外
    emails = frozenset(normalize_email(u["email"]) for u in list_users())

    with _CACHE_LOCK:
        if _CACHE["generation"] == generation:
            _CACHE["emails"] = emails
            _CACHE["fetched_at"] = time.time()
    return emails


def invalidate_cache() -> None:
    """立即清除本 container 的白名單快取。"""
    with _CACHE_LOCK:
        _CACHE["emails"] = None
        _CACHE["fetched_at"] = 0.0
        _CACHE["generation"] += 1


def touch_last_login(email: str, now: datetime | None = None) -> bool:
    """條件更新 last_login（僅限已在表中的 email，絕不建立列）。
    成功 True；不在表中 False；其他錯誤往上拋。"""
    from botocore.exceptions import ClientError

    ensure_allowed_users_table_exists()
    ts = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        _table().update_item(
            Key={"email": normalize_email(email)},
            UpdateExpression="SET last_login = :t",
            ConditionExpression="attribute_exists(email)",
            ExpressionAttributeValues={":t": ts},
        )
    except ClientError as err:
        if _is_conditional_failure(err):
            return False
        raise
    return True


def add_user(email: str) -> tuple[dict, bool]:
    """條件 put 新增；回 (item, created)。已存在時不覆寫，created=False 並帶既有 last_login。"""
    try:
        return _add_user(email)
    finally:
        invalidate_cache()


def _add_user(email: str) -> tuple[dict, bool]:
    from botocore.exceptions import ClientError

    ensure_allowed_users_table_exists()
    e = normalize_email(email)
    table = _table()
    try:
        table.put_item(Item={"email": e}, ConditionExpression="attribute_not_exists(email)")
    except ClientError as err:
        if not _is_conditional_failure(err):
            raise
        existing = table.get_item(Key={"email": e}).get("Item") or {}
        last_login: str | None = existing.get("last_login")
        return {"email": e, "last_login": last_login}, False
    return {"email": e, "last_login": None}, True


def remove_user(email: str) -> bool:
    """條件 delete；True=已刪除，False=原本不存在。"""
    try:
        return _remove_user(email)
    finally:
        invalidate_cache()


def _remove_user(email: str) -> bool:
    from botocore.exceptions import ClientError

    ensure_allowed_users_table_exists()
    e = normalize_email(email)
    if not e:
        return False
    try:
        _table().delete_item(Key={"email": e}, ConditionExpression="attribute_exists(email)")
    except ClientError as err:
        if _is_conditional_failure(err):
            return False
        raise
    return True
