"""Pytest 共用設定：預設略過登入驗證（TASK-008），讓既有測試不需自組 JWT。

若某測試想驗證「未登入」或「管理者」情境，可在該測試內另外覆寫
app.dependency_overrides[get_current_user] / [require_admin]。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import app
from auth import CurrentUser, get_current_user


def _fake_current_user() -> CurrentUser:
    return CurrentUser(email="test-user@example.com", role="user")


@pytest.fixture(autouse=True)
def _override_auth():
    app.dependency_overrides[get_current_user] = _fake_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
