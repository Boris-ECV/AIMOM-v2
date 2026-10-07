"""管理者白名單（允許登入 email）資料存取層（SDLCAIP2-66）。

admin.py 只透過本模組存取 allowed-users 資料表。
"""
from __future__ import annotations

import boto3

import config


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


def add_user(email: str) -> tuple[dict, bool]:
    """條件 put 新增；回 (item, created)。已存在時不覆寫，created=False 並帶既有 last_login。"""
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
