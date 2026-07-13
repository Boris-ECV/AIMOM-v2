"""LLM 用量/成本記錄與彙總（TASK-011）。

每次呼叫 LLM 後由 summarize.py 呼叫 record_llm_usage() 寫入一筆紀錄；
admin.py 呼叫 summarize_usage() 做管理者儀表板彙總查詢。
"""
from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Optional

import boto3

import config

# 每百萬 tokens 美元定價（engine, model）→ (input_price, output_price)
PRICING_PER_MILLION_TOKENS = {
    ("github-models", "gpt-4o"): (2.50, 10.00),
    ("openai", "gpt-4o"): (2.50, 10.00),
    ("groq", "llama-3.3-70b-versatile"): (0.59, 0.79),
    ("groq", "gpt-oss-120b"): (0.15, 0.60),
    ("groq", "llama-3.1-8b-instant"): (0.05, 0.08),
    ("gemini", "gemini-2.0-flash"): (0.25, 1.50),
    ("gemini", "gemini-1.5-pro"): (1.50, 9.00),
}


def _resource():
    return boto3.resource("dynamodb", region_name=config.COGNITO_REGION)


def _table():
    return _resource().Table(config.DYNAMODB_LLM_USAGE_TABLE)


def ensure_usage_table_exists() -> None:
    client = boto3.client("dynamodb", region_name=config.COGNITO_REGION)
    existing = client.list_tables().get("TableNames", [])
    if config.DYNAMODB_LLM_USAGE_TABLE in existing:
        return

    client.create_table(
        TableName=config.DYNAMODB_LLM_USAGE_TABLE,
        KeySchema=[
            {"AttributeName": "date", "KeyType": "HASH"},
            {"AttributeName": "usage_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "date", "AttributeType": "S"},
            {"AttributeName": "usage_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=config.DYNAMODB_LLM_USAGE_TABLE)


def estimate_cost(engine: str, model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """依定價表估算成本（美元）。找不到對應定價則回傳 None。"""
    prices = PRICING_PER_MILLION_TOKENS.get((engine, model))
    if prices is None:
        return None
    input_price, output_price = prices
    cost = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
    return round(cost, 6)


def record_llm_usage(
    engine: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    user_id: str,
    meeting_id: str,
) -> dict:
    """寫入一筆 LLM 用量紀錄至 DynamoDB。"""
    ensure_usage_table_exists()
    now = datetime.datetime.utcnow()
    cost = estimate_cost(engine, model, input_tokens, output_tokens)
    item = {
        "date": now.strftime("%Y-%m-%d"),
        "usage_id": str(uuid.uuid4()),
        "engine": engine,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost": cost,
        "user_id": user_id,
        "meeting_id": meeting_id,
        "created_at": now.isoformat(),
    }
    # DynamoDB 不支援原生 float，寫入時轉為 Decimal，回傳給呼叫端仍維持 float 方便運算
    dynamo_item = {**item, "estimated_cost": Decimal(str(cost)) if cost is not None else None}
    _table().put_item(Item=dynamo_item)
    return item


def summarize_usage() -> dict:
    """彙總所有用量紀錄：依日期、依使用者。"""
    ensure_usage_table_exists()
    resp = _table().scan()
    items = resp.get("Items", [])

    by_date: dict[str, dict] = {}
    by_user: dict[str, dict] = {}

    for i in items:
        cost = float(i.get("estimated_cost") or 0)
        date = i["date"]
        user_id = i["user_id"]

        d = by_date.setdefault(date, {"input_tokens": 0, "output_tokens": 0, "estimated_cost": 0.0, "calls": 0})
        d["input_tokens"] += i.get("input_tokens", 0)
        d["output_tokens"] += i.get("output_tokens", 0)
        d["estimated_cost"] += cost
        d["calls"] += 1

        u = by_user.setdefault(user_id, {"input_tokens": 0, "output_tokens": 0, "estimated_cost": 0.0, "calls": 0})
        u["input_tokens"] += i.get("input_tokens", 0)
        u["output_tokens"] += i.get("output_tokens", 0)
        u["estimated_cost"] += cost
        u["calls"] += 1

    return {
        "by_date": [{"date": k, **v} for k, v in sorted(by_date.items())],
        "by_user": [{"user_id": k, **v} for k, v in sorted(by_user.items())],
        "total_calls": len(items),
        "total_estimated_cost": round(sum(float(i.get("estimated_cost") or 0) for i in items), 6),
    }
