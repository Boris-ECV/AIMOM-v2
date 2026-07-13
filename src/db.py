"""DynamoDB 存取層（TASK-009）。

封裝 Meetings 資料表的讀寫，供 history.py 使用。
本機/CI 測試以 moto 模擬，不需要真實 AWS 帳號。
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key

import config


def _resource():
    return boto3.resource("dynamodb", region_name=config.COGNITO_REGION)


def _table():
    return _resource().Table(config.DYNAMODB_MEETINGS_TABLE)


def ensure_meetings_table_exists() -> None:
    """建立 Meetings 表（若不存在）。正式環境由 IaC 管理，這裡主要供本機/測試使用。"""
    client = boto3.client("dynamodb", region_name=config.COGNITO_REGION)
    existing = client.list_tables().get("TableNames", [])
    if config.DYNAMODB_MEETINGS_TABLE in existing:
        return

    client.create_table(
        TableName=config.DYNAMODB_MEETINGS_TABLE,
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "meeting_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "meeting_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=config.DYNAMODB_MEETINGS_TABLE)
    try:
        client.update_time_to_live(
            TableName=config.DYNAMODB_MEETINGS_TABLE,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"},
        )
    except Exception:  # noqa: BLE001 — moto 部分版本不支援 TTL API，忽略即可
        pass


def put_meeting(
    user_id: str,
    title: str,
    transcript_text: str,
    minutes_json: str,
    retention_days: Optional[int] = None,
) -> dict:
    """寫入一筆保留的會議紀錄，回傳含 meeting_id / expires_at 的資料。"""
    ensure_meetings_table_exists()
    days = retention_days if retention_days is not None else config.MEETING_RETENTION_DAYS
    now = int(time.time())
    expires_at = now + days * 86400
    meeting_id = str(uuid.uuid4())

    item = {
        "user_id": user_id,
        "meeting_id": meeting_id,
        "title": title,
        "created_at": now,
        "transcript_text": transcript_text,
        "minutes_json": minutes_json,
        "expires_at": expires_at,
    }
    _table().put_item(Item=item)
    return item


def list_meetings(user_id: str) -> list[dict]:
    """列出目前使用者「尚未過期」的會議紀錄。"""
    ensure_meetings_table_exists()
    now = int(time.time())
    resp = _table().query(
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    items = resp.get("Items", [])
    return [i for i in items if i.get("expires_at", 0) > now]


def get_meeting(user_id: str, meeting_id: str) -> Optional[dict]:
    """取得單筆會議紀錄，若不存在或不屬於此使用者則回傳 None。"""
    ensure_meetings_table_exists()
    resp = _table().get_item(Key={"user_id": user_id, "meeting_id": meeting_id})
    item = resp.get("Item")
    if not item:
        return None
    if item.get("expires_at", 0) <= int(time.time()):
        return None
    return item


def delete_meeting(user_id: str, meeting_id: str) -> bool:
    """刪除一筆會議紀錄（使用者手動提前刪除）。回傳是否成功刪除既有項目。"""
    existing = get_meeting(user_id, meeting_id)
    if existing is None:
        return False
    _table().delete_item(Key={"user_id": user_id, "meeting_id": meeting_id})
    return True
