"""Job 狀態共用儲存層（TASK-016）。

背景：把 `/api/transcribe` 改為非同步送出後，「送出轉錄」與後續
`/api/status` 輪詢幾乎必然發生在不同的 Lambda 執行環境（container），
因此不能再用本機 `/tmp` 檔案（原本的 meta.json/status.json/
transcript.json/minutes.json）當作 job 狀態的唯一來源 —— 那些檔案只存在
處理該次請求的那個 container 裡，其他 container 完全讀不到。

改用 DynamoDB（沿用專案既有的 db.py／moto 測試模式）集中儲存整個 job 的
狀態，任何 container 都能讀到最新進度。為了簡化實作、避免處理 DynamoDB
數值型別（Decimal）轉換的細節，job 的所有欄位打包成一個 JSON 字串存在
單一 `data` attribute 裡，讀寫都用一般的 Python dict／json 操作即可。
"""
from __future__ import annotations

import json
import time
from typing import Optional

import boto3

import config

_JOB_TTL_SECONDS = 6 * 3600  # 6 小時，足夠涵蓋長會議轉錄＋摘要＋匯出的作業時間


def _resource():
    return boto3.resource("dynamodb", region_name=config.COGNITO_REGION)


def _table():
    return _resource().Table(config.DYNAMODB_JOBS_TABLE)


def ensure_jobs_table_exists() -> None:
    """建立 Jobs 表（若不存在）。正式環境由 Terraform 建立（見 infra/dynamodb.tf），
    Lambda 執行角色刻意不授予 dynamodb:ListTables/CreateTable（最小權限原則），
    因此這裡若遇到權限不足，視為「已由 IaC 建好」直接略過，只在本機/測試環境
    （例如 moto 模擬、開發者自己的 AWS 帳號）真正發揮建表功能。
    """
    from botocore.exceptions import ClientError

    client = boto3.client("dynamodb", region_name=config.COGNITO_REGION)
    try:
        existing = client.list_tables().get("TableNames", [])
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "AccessDeniedException":
            return
        raise

    if config.DYNAMODB_JOBS_TABLE in existing:
        return

    client.create_table(
        TableName=config.DYNAMODB_JOBS_TABLE,
        KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=config.DYNAMODB_JOBS_TABLE)
    try:
        client.update_time_to_live(
            TableName=config.DYNAMODB_JOBS_TABLE,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"},
        )
    except Exception:  # noqa: BLE001 — moto 部分版本不支援 TTL API，忽略即可
        pass


def _put(job_id: str, data: dict) -> dict:
    ensure_jobs_table_exists()
    _table().put_item(Item={
        "job_id": job_id,
        "data": json.dumps(data, ensure_ascii=False),
        "expires_at": int(time.time()) + _JOB_TTL_SECONDS,
    })
    return data


def create_job(job_id: str, **fields) -> dict:
    """建立新 job，預設狀態為 uploaded。"""
    data = {
        "job_id": job_id,
        "stage": "uploaded",
        "progress": 10,
        "message": "上傳完成，等待轉錄",
    }
    data.update({k: v for k, v in fields.items() if v is not None})
    return _put(job_id, data)


def get_job(job_id: str) -> Optional[dict]:
    ensure_jobs_table_exists()
    resp = _table().get_item(Key={"job_id": job_id})
    item = resp.get("Item")
    if not item:
        return None
    return json.loads(item["data"])


def update_job(job_id: str, **fields) -> dict:
    """讀出現有 job、合併欄位後整筆寫回。找不到 job 則自動以這些欄位建立一筆。"""
    data = get_job(job_id) or {"job_id": job_id}
    data.update({k: v for k, v in fields.items() if v is not None})
    return _put(job_id, data)


def delete_job(job_id: str) -> bool:
    ensure_jobs_table_exists()
    existing = get_job(job_id)
    if existing is None:
        return False
    _table().delete_item(Key={"job_id": job_id})
    return True
