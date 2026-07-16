"""TASK-016 迴歸測試：ensure_*_table_exists() 在正式環境（Lambda 執行角色
沒有 dynamodb:ListTables/CreateTable 權限）下應該優雅略過，而不是讓整個
請求因為 AccessDeniedException 而 500。
"""
from unittest.mock import patch, MagicMock

from botocore.exceptions import ClientError

import jobstore


def _access_denied_error(operation: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "not authorized"}},
        operation,
    )


def test_ensure_jobs_table_exists_swallows_access_denied():
    fake_client = MagicMock()
    fake_client.list_tables.side_effect = _access_denied_error("ListTables")

    with patch("boto3.client", return_value=fake_client):
        jobstore.ensure_jobs_table_exists()  # 不應該丟出例外

    fake_client.create_table.assert_not_called()


def test_ensure_jobs_table_exists_reraises_other_errors():
    fake_client = MagicMock()
    fake_client.list_tables.side_effect = _access_denied_error("ListTables")
    fake_client.list_tables.side_effect = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "slow down"}},
        "ListTables",
    )

    with patch("boto3.client", return_value=fake_client):
        try:
            jobstore.ensure_jobs_table_exists()
            assert False, "應該要重新拋出非 AccessDenied 的錯誤"
        except ClientError as e:
            assert e.response["Error"]["Code"] == "ThrottlingException"
