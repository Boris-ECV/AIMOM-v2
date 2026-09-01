# src/tests/e2e_server.py
"""standalone launcher for e2e tests，非 pytest 測試檔（檔名不含 test_ 前綴）。

於同一行程內完成三件事後才呼叫 uvicorn.run(...)：
1. 設定 moto 用的 AWS dummy 環境變數
2. 覆寫 get_current_user dependency 跳過真實 Cognito 登入
3. 用 mock_aws() context 包住整個 uvicorn.run(...) 呼叫（阻塞呼叫，行程存
   活期間 = mock 存活期間）

與 conftest.py 的差異只在於：這裡是啟動一個常駐 server 行程，而非
pytest fixture 包住每個測試，效果等價。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # 與 conftest.py 相同手法

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")

import uvicorn
from moto import mock_aws

from app import app
from auth import CurrentUser, get_current_user


def _fake_current_user() -> CurrentUser:
    return CurrentUser(email="e2e-user@example.com", role="user")


if __name__ == "__main__":
    app.dependency_overrides[get_current_user] = _fake_current_user
    with mock_aws():
        uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
