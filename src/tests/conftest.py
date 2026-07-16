"""Pytest 共用設定：預設略過登入驗證（TASK-008），讓既有測試不需自組 JWT。

若某測試想驗證「未登入」或「管理者」情境，可在該測試內另外覆寫
app.dependency_overrides[get_current_user] / [require_admin]。

TASK-016 起，job 狀態（上傳/轉錄/摘要）改存於 DynamoDB（見 jobstore.py），
因此這裡全域啟用 moto 的 DynamoDB 模擬，所有測試都不需要真實 AWS 帳號。
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")

import pytest
from moto import mock_aws

from app import app
from auth import CurrentUser, get_current_user


def _fake_current_user() -> CurrentUser:
    return CurrentUser(email="test-user@example.com", role="user")


@pytest.fixture(autouse=True)
def _override_auth():
    app.dependency_overrides[get_current_user] = _fake_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _mock_dynamodb():
    with mock_aws():
        yield
