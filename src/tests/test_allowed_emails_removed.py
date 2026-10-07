"""SDLCAIP2-67: 靜態驗證 ALLOWED_EMAILS 環境變數/Terraform 變數/CI secret 已完全移除。

登入白名單改讀 DynamoDB allowed-users 資料表（見 src/allowed_users.py）。
docs/ 下的歷史設計文件不在掃描範圍。
"""
from pathlib import Path
import re

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CI_YML_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"

SCANNED_FILES = [
    REPO_ROOT / "src" / "config.py",
    REPO_ROOT / "src" / "auth.py",
    REPO_ROOT / "infra" / "terraform.tfvars.example",
    CI_YML_PATH,
    *sorted((REPO_ROOT / "infra").glob("*.tf")),
]


@pytest.mark.parametrize("path", SCANNED_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_file_has_no_allowed_emails_reference(path):
    content = path.read_text(encoding="utf-8")
    # \b 使 auth.py 的 _load_allowed_emails（SDLCAIP2-67 新函式名）不被誤判
    assert not re.search(r"\ballowed_emails\b", content, re.IGNORECASE), f"{path} 仍含 ALLOWED_EMAILS/allowed_emails"
    assert "TF_VAR_allowed_emails" not in content


def test_infra_tf_files_were_scanned():
    assert any(p.suffix == ".tf" for p in SCANNED_FILES)


def test_ci_terraform_apply_env_has_no_tf_var_allowed_emails():
    with open(CI_YML_PATH, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
    for job in workflow.get("jobs", {}).values():
        for step in job.get("steps", []):
            assert "TF_VAR_allowed_emails" not in (step.get("env") or {})


def test_config_module_has_no_allowed_emails_attribute():
    import config

    assert not hasattr(config, "ALLOWED_EMAILS")


def test_auth_module_has_no_get_allowed_emails():
    import auth

    assert not hasattr(auth, "_get_allowed_emails")
