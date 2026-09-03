"""SDLCAIP2-11: 靜態驗證 .github/workflows/ci.yml 的 frontend job 結構，
以及 infra/outputs.tf 中 cloudfront_distribution_id 輸出的正確性。

無法在測試環境中實際觸發 aws s3 sync / cloudfront invalidation（無 AWS
憑證，也不應對真實 infra 造成影響），因此以下測試改為驗證 workflow YAML
的結構性正確性，對應規格書中四個 Gherkin 情境：

1. Terraform 輸出 cloudfront_distribution_id 供部署步驟使用
2. PR 合併到 main 後自動同步前端內容並清除快取
3. frontend job 依賴 backend job 成功，不會單獨搶跑
4. 部署失敗時清楚可見（無 continue-on-error 抑制失敗狀態）
"""
from pathlib import Path
import re

import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CI_YML_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
OUTPUTS_TF_PATH = REPO_ROOT / "infra" / "outputs.tf"
CLOUDFRONT_TF_PATH = REPO_ROOT / "infra" / "cloudfront.tf"


@pytest.fixture(scope="module")
def ci_workflow():
    with open(CI_YML_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def frontend_job(ci_workflow):
    jobs = ci_workflow.get("jobs", {})
    assert "frontend" in jobs, "workflow 缺少 frontend job"
    return jobs["frontend"]


# --- Scenario 1: Terraform 輸出 cloudfront_distribution_id 供部署步驟使用 ---

def test_outputs_tf_has_cloudfront_distribution_id():
    content = OUTPUTS_TF_PATH.read_text(encoding="utf-8")
    match = re.search(
        r'output\s+"cloudfront_distribution_id"\s*\{([^}]*)\}', content, re.DOTALL
    )
    assert match, "infra/outputs.tf 缺少 cloudfront_distribution_id output"
    assert "aws_cloudfront_distribution.frontend.id" in match.group(1)


def test_cloudfront_distribution_resource_name_matches_output():
    """確認輸出引用的資源名稱 (aws_cloudfront_distribution.frontend) 在
    infra/cloudfront.tf 中確實存在，避免輸出指到不存在的資源。"""
    content = CLOUDFRONT_TF_PATH.read_text(encoding="utf-8")
    assert re.search(
        r'resource\s+"aws_cloudfront_distribution"\s+"frontend"\s*\{', content
    ), "infra/cloudfront.tf 找不到 aws_cloudfront_distribution.frontend 資源"


def test_backend_job_exposes_cloudfront_distribution_id_output(ci_workflow):
    backend_job = ci_workflow["jobs"]["backend"]
    outputs = backend_job.get("outputs", {})
    assert "cloudfront_distribution_id" in outputs
    assert "tf_outputs" in outputs["cloudfront_distribution_id"]


# --- Scenario 2: PR 合併到 main 後自動同步前端內容並清除快取 ---

def test_frontend_job_s3_sync_step(frontend_job):
    steps = frontend_job.get("steps", [])
    sync_steps = [s for s in steps if "aws s3 sync" in (s.get("run") or "")]
    assert sync_steps, "找不到 aws s3 sync 步驟"
    run_cmd = sync_steps[0]["run"]
    assert "needs.backend.outputs.frontend_bucket_name" in run_cmd
    assert "src/frontend/" in run_cmd
    assert '--exclude ".DS_Store"' in run_cmd
    assert '--cache-control "no-cache, must-revalidate"' in run_cmd


def test_frontend_job_cloudfront_invalidation_step(frontend_job):
    steps = frontend_job.get("steps", [])
    invalidation_steps = [
        s for s in steps if "aws cloudfront create-invalidation" in (s.get("run") or "")
    ]
    assert invalidation_steps, "找不到 aws cloudfront create-invalidation 步驟"
    run_cmd = invalidation_steps[0]["run"]
    assert "needs.backend.outputs.cloudfront_distribution_id" in run_cmd
    assert '--paths "/*"' in run_cmd


# --- Scenario 3: frontend job 依賴 backend job 成功，不會單獨搶跑 ---

def test_frontend_job_depends_on_backend_only(frontend_job):
    needs = frontend_job.get("needs")
    assert needs is not None
    if isinstance(needs, str):
        needs = [needs]
    assert set(needs) == {"backend"}


def test_frontend_job_only_runs_on_push_to_main(frontend_job):
    condition = frontend_job.get("if", "")
    assert "push" in condition
    assert "refs/heads/main" in condition


# --- Scenario 4: 部署失敗時清楚可見 ---

def test_frontend_job_has_no_continue_on_error(frontend_job):
    """continue-on-error 會抑制失敗狀態顯示，違反可見性要求。"""
    assert "continue-on-error" not in frontend_job
    for step in frontend_job.get("steps", []):
        assert step.get("continue-on-error") is not True, (
            f"step {step.get('name')} 設定了 continue-on-error，會抑制失敗顯示"
        )


def test_frontend_job_has_no_top_level_notification_step(frontend_job):
    """規格明確表示不需要額外通知機制；確認沒有引入非必要的第三方通知 action。"""
    steps = frontend_job.get("steps", [])
    for step in steps:
        uses = step.get("uses", "")
        assert "slack" not in uses.lower()
        assert "notify" not in uses.lower()


def test_no_hardcoded_secret_literals_in_frontend_job(frontend_job):
    """粗略檢查 frontend job 中沒有明文寫死的機密值格式。"""
    raw = yaml.dump(frontend_job)
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",  # OpenAI-style key
        r"AKIA[0-9A-Z]{16}",  # AWS access key id
        r"AIza[0-9A-Za-z_-]{20,}",  # Google API key
    ]
    for pattern in suspicious_patterns:
        matches = re.findall(pattern, raw)
        assert not matches, f"frontend job 中發現疑似明文機密: {matches}"
