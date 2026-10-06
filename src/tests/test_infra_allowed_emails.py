"""SDLCAIP2-61: 靜態驗證 ALLOWED_EMAILS 登入白名單已正確串接至
Terraform infra，且不會被 CD 自動部署覆蓋。

無法在測試環境中實際執行 `terraform plan`（無 terraform CLI 也不應對
真實 infra 造成影響），因此以下測試改為解析 infra/variables.tf、
infra/lambda.tf、.github/workflows/ci.yml 的文字結構，對應規格書中
三個 Gherkin 情境：

1. Terraform 變數可設定 ALLOWED_EMAILS（variables.tf 定義 + lambda.tf 串接）
2. CD 自動部署不會清除此設定（ci.yml 的 terraform apply step 注入 TF_VAR_allowed_emails）
3. 白名單機制串接後實際生效（既有 src/tests/test_auth.py 的 403 邏輯仍存在且通過）
"""
from pathlib import Path
import re

import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VARIABLES_TF_PATH = REPO_ROOT / "infra" / "variables.tf"
LAMBDA_TF_PATH = REPO_ROOT / "infra" / "lambda.tf"
CI_YML_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
TEST_AUTH_PATH = REPO_ROOT / "src" / "tests" / "test_auth.py"


@pytest.fixture(scope="module")
def variables_tf_content():
    return VARIABLES_TF_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lambda_tf_content():
    return LAMBDA_TF_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def ci_workflow():
    with open(CI_YML_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# --- Scenario 1: Terraform 變數可設定 ALLOWED_EMAILS ---

def test_variables_tf_defines_allowed_emails_block(variables_tf_content):
    match = re.search(
        r'variable\s+"allowed_emails"\s*\{([^}]*)\}', variables_tf_content, re.DOTALL
    )
    assert match, "infra/variables.tf 缺少 variable \"allowed_emails\" 區塊"
    body = match.group(1)
    assert re.search(r"type\s*=\s*string", body), "allowed_emails 變數的 type 不是 string"
    assert re.search(r'default\s*=\s*""', body), "allowed_emails 變數的 default 不是空字串"
    assert re.search(r"sensitive\s*=\s*true", body), "allowed_emails 變數未標記為 sensitive = true"


def test_lambda_environment_maps_allowed_emails_to_var(lambda_tf_content):
    assert re.search(
        r"ALLOWED_EMAILS\s*=\s*var\.allowed_emails", lambda_tf_content
    ), "infra/lambda.tf 的 aws_lambda_function.api environment.variables 未將 ALLOWED_EMAILS 對應到 var.allowed_emails"


def test_lambda_function_block_contains_environment_variables(lambda_tf_content):
    """確認 ALLOWED_EMAILS 映射確實位於 aws_lambda_function "api" 的
    environment 區塊內，而非文件中其他無關位置。"""
    match = re.search(
        r'resource\s+"aws_lambda_function"\s+"api"\s*\{(.*)',
        lambda_tf_content,
        re.DOTALL,
    )
    assert match, "infra/lambda.tf 找不到 aws_lambda_function \"api\" 區塊"
    body = match.group(1)
    env_match = re.search(r"environment\s*\{(.*?variables\s*=\s*\{.*?\})\s*\}", body, re.DOTALL)
    assert env_match, "aws_lambda_function.api 找不到 environment.variables 區塊"
    assert "ALLOWED_EMAILS" in env_match.group(1)
    assert "var.allowed_emails" in env_match.group(1)


# --- Scenario 2: CD 自動部署不會清除此設定 ---

def test_ci_backend_apply_step_injects_tf_var_allowed_emails(ci_workflow):
    backend_job = ci_workflow["jobs"]["backend"]
    steps = backend_job.get("steps", [])
    apply_steps = [s for s in steps if "terraform apply" in (s.get("run") or "")]
    assert apply_steps, "找不到 terraform apply 步驟"
    env = apply_steps[0].get("env", {})
    assert "TF_VAR_allowed_emails" in env, (
        "terraform apply 步驟缺少 TF_VAR_allowed_emails，CD 部署時會把 "
        "allowed_emails 重設為預設空字串，清除白名單設定"
    )
    assert env["TF_VAR_allowed_emails"] == "${{ secrets.TF_VAR_allowed_emails }}", (
        f"TF_VAR_allowed_emails 的值不是來自 secrets.TF_VAR_allowed_emails: "
        f"{env['TF_VAR_allowed_emails']!r}"
    )


# --- Scenario 3: 白名單機制串接後實際生效 ---

def test_auth_whitelist_403_test_still_present():
    """確認既有 test_auth.py 中「email 不在白名單內回傳 403」的測試
    未被移除或弱化——這是 ALLOWED_EMAILS 串接後實際生效的應用層前提。"""
    content = TEST_AUTH_PATH.read_text(encoding="utf-8")
    assert "def test_get_current_user_email_not_in_allowlist_returns_403" in content
    assert "403" in content


def test_auth_whitelist_403_test_exercises_config_allowed_emails():
    """確認 403 測試確實透過 monkeypatch config.ALLOWED_EMAILS 來觸發情境，
    而非測試其他不相關邏輯——這樣 Terraform 注入的 ALLOWED_EMAILS 環境變數
    （經 src/config.py 讀取後）才會是這條測試實際驗證的同一個開關。"""
    content = TEST_AUTH_PATH.read_text(encoding="utf-8")
    func_match = re.search(
        r"def test_get_current_user_email_not_in_allowlist_returns_403\(.*?\n(?:.*\n)*?    assert resp\.status_code == 403",
        content,
    )
    assert func_match, "找不到完整的 403 測試函式本文"
    body = func_match.group(0)
    assert 'monkeypatch.setattr(config, "ALLOWED_EMAILS"' in body
    assert "assert resp.status_code == 403" in body
