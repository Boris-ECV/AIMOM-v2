"""SDLCAIP2-66: 靜態驗證 allowed-users 資料表 infra、config 與登入檢查不變。"""
from pathlib import Path
import os
import re
import subprocess
import sys


SRC = Path(__file__).resolve().parent.parent
INFRA = SRC.parent / "infra"


def _read(p):
    return Path(p).read_text(encoding="utf-8")


# AC9
def test_dynamodb_tf_defines_allowed_users_table():
    m = re.search(
        r'resource\s+"aws_dynamodb_table"\s+"allowed_users"\s*\{(.*?)\n\}',
        _read(INFRA / "dynamodb.tf"),
        re.DOTALL,
    )
    assert m
    body = m.group(1)
    assert re.search(r'name\s*=\s*"\$\{local\.name_prefix\}-allowed-users"', body)
    assert re.search(r'hash_key\s*=\s*"email"', body)
    assert re.search(r'billing_mode\s*=\s*"PAY_PER_REQUEST"', body)
    assert re.search(r'attribute\s*\{\s*name\s*=\s*"email"\s*type\s*=\s*"S"\s*\}', body)


def test_iam_dynamodb_access_includes_allowed_users():
    m = re.search(
        r'sid\s*=\s*"DynamoDBAccess".*?resources\s*=\s*\[(.*?)\]',
        _read(INFRA / "iam.tf"),
        re.DOTALL,
    )
    assert m
    assert "aws_dynamodb_table.allowed_users.arn" in m.group(1)


def test_lambda_env_has_allowed_users_table():
    assert re.search(
        r"DYNAMODB_ALLOWED_USERS_TABLE\s*=\s*aws_dynamodb_table\.allowed_users\.name",
        _read(INFRA / "lambda.tf"),
    )


def _config_value(env_extra):
    env = {k: v for k, v in os.environ.items() if k != "DYNAMODB_ALLOWED_USERS_TABLE"}
    env.update(env_extra)
    out = subprocess.run(
        [sys.executable, "-c", "import config;print(config.DYNAMODB_ALLOWED_USERS_TABLE)"],
        cwd=SRC,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def test_config_default_table_name():
    assert _config_value({}) == "aimom-allowed-users"


def test_config_honors_env_var():
    assert _config_value({"DYNAMODB_ALLOWED_USERS_TABLE": "custom-t"}) == "custom-t"

