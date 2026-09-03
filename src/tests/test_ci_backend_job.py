"""SDLCAIP2-10: 靜態驗證 .github/workflows/ci.yml 的 backend job 結構，
以及 infra/variables.tf 中敏感變數與 workflow secrets 的對應關係。

無法在測試環境中實際觸發 terraform apply（無 AWS 憑證，也不應對真實
infra 造成影響），因此以下測試改為驗證 workflow YAML 的結構性正確性，
對應規格書中三個 Gherkin 情境：

1. PR 合併到 main 後自動觸發 terraform apply（非互動模式）
2. 敏感變數透過 GitHub Secrets 個別注入，不寫死於 workflow 檔
3. 部署失敗時清楚可見（無 continue-on-error 抑制失敗狀態）
"""
from pathlib import Path
import re

import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CI_YML_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
VARIABLES_TF_PATH = REPO_ROOT / "infra" / "variables.tf"
COGNITO_TF_PATH = REPO_ROOT / "infra" / "cognito.tf"
APIGATEWAY_TF_PATH = REPO_ROOT / "infra" / "apigateway.tf"
S3_TF_PATH = REPO_ROOT / "infra" / "s3.tf"


@pytest.fixture(scope="module")
def ci_workflow():
    with open(CI_YML_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def backend_job(ci_workflow):
    jobs = ci_workflow.get("jobs", {})
    assert "backend" in jobs, "workflow 缺少 backend job"
    return jobs["backend"]


@pytest.fixture(scope="module")
def sensitive_var_names():
    """從 infra/variables.tf 解析出所有 sensitive = true 的變數名稱。"""
    content = VARIABLES_TF_PATH.read_text(encoding="utf-8")
    blocks = re.findall(r'variable\s+"([a-zA-Z0-9_]+)"\s*\{([^}]*)\}', content, re.DOTALL)
    names = [name for name, body in blocks if re.search(r"sensitive\s*=\s*true", body)]
    assert names, "variables.tf 中未解析出任何 sensitive 變數，解析邏輯可能有誤"
    return names


# --- Scenario 1: PR 合併到 main 後自動觸發 terraform apply（非互動模式） ---

def test_backend_job_depends_on_quality_and_e2e(backend_job):
    needs = backend_job.get("needs")
    assert needs is not None
    if isinstance(needs, str):
        needs = [needs]
    assert set(needs) == {"quality", "e2e"}


def test_backend_job_only_runs_on_push_to_main(backend_job):
    condition = backend_job.get("if", "")
    assert "push" in condition
    assert "refs/heads/main" in condition


def test_backend_job_has_no_continue_on_error(ci_workflow):
    """continue-on-error 會抑制失敗狀態顯示，違反 Scenario 3 的可見性要求。"""
    backend_job = ci_workflow["jobs"]["backend"]
    assert "continue-on-error" not in backend_job
    for step in backend_job.get("steps", []):
        assert step.get("continue-on-error") is not True, (
            f"step {step.get('name')} 設定了 continue-on-error，會抑制失敗顯示"
        )


def test_terraform_apply_step_is_non_interactive(backend_job):
    steps = backend_job.get("steps", [])
    apply_steps = [s for s in steps if "terraform apply" in (s.get("run") or "")]
    assert apply_steps, "找不到 terraform apply 步驟"
    for step in apply_steps:
        run_cmd = step["run"]
        assert "-auto-approve" in run_cmd
        assert "-input=false" in run_cmd


def test_backend_hcl_reconstructed_from_secrets_not_hardcoded(backend_job):
    steps = backend_job.get("steps", [])
    hcl_steps = [s for s in steps if "backend.hcl" in (s.get("run") or "")]
    assert hcl_steps, "找不到重建 infra/backend.hcl 的步驟"
    run_cmd = hcl_steps[0]["run"]
    for secret_name in ("TF_STATE_BUCKET", "TF_STATE_KEY", "TF_STATE_REGION"):
        assert f"secrets.{secret_name}" in run_cmd, (
            f"backend.hcl 重建步驟未引用 secrets.{secret_name}，可能寫死了值"
        )


def test_terraform_init_step_present(backend_job):
    steps = backend_job.get("steps", [])
    init_steps = [s for s in steps if "terraform init" in (s.get("run") or "")]
    assert init_steps, "找不到 terraform init 步驟"


# --- Scenario 2: 敏感變數透過 GitHub Secrets 個別注入，不寫死於 workflow 檔 ---

def test_every_sensitive_variable_has_tf_var_env(backend_job, sensitive_var_names):
    steps = backend_job.get("steps", [])
    apply_steps = [s for s in steps if "terraform apply" in (s.get("run") or "")]
    assert apply_steps, "找不到 terraform apply 步驟"
    env = apply_steps[0].get("env", {})

    missing = []
    for var_name in sensitive_var_names:
        env_key = f"TF_VAR_{var_name}"
        if env_key not in env:
            missing.append(env_key)
            continue
        # 必須是透過 secrets 注入，而非寫死的明文
        assert "secrets." in env[env_key], (
            f"{env_key} 的值不是來自 GitHub Secrets: {env[env_key]!r}"
        )
    assert not missing, f"以下敏感變數缺少對應的 TF_VAR_ env 注入: {missing}"


def test_no_hardcoded_secret_literals_in_workflow_file():
    """粗略檢查 workflow 原始檔中沒有明文寫死的機密值格式。"""
    raw = CI_YML_PATH.read_text(encoding="utf-8")
    # 常見機密格式：長度 >= 20 的連續英數字混合字串，且不是 ${{ ... }} 表達式
    # 或已知的非機密識別字（terraform 版本號、action 版本等）。
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",  # OpenAI-style key
        r"AKIA[0-9A-Z]{16}",  # AWS access key id
        r"AIza[0-9A-Za-z_-]{20,}",  # Google API key
    ]
    for pattern in suspicious_patterns:
        matches = re.findall(pattern, raw)
        assert not matches, f"workflow 檔案中發現疑似明文機密: {matches}"


def test_all_env_values_in_apply_step_reference_secrets_or_vars_context(backend_job):
    """terraform apply 步驟的 env 區塊中，所有值都必須引用 GitHub Actions
    的 ${{ secrets.* }} 或 ${{ vars.* }} context，不得是字面常數。

    SDLCAIP2-12/SDLCAIP2-13 核准的設計決策 1（docs/design/SDLCAIP2-12.md）：
    非機密的前端網址（frontend_callback_urls/frontend_logout_urls）改用
    GitHub Actions repository Variables（${{ vars.* }}）注入，而非 Secrets，
    因為這些值本來就是前端公開網址、不具機密性。此測試的核心不變量——
    「所有值都必須來自 GitHub context、不得是寫死的字面常數」——維持不變，
    只放寬允許的 context 前綴以涵蓋 vars.*。"""
    steps = backend_job.get("steps", [])
    apply_steps = [s for s in steps if "terraform apply" in (s.get("run") or "")]
    env = apply_steps[0].get("env", {})
    assert env, "terraform apply 步驟沒有 env 區塊"
    for key, value in env.items():
        assert re.match(r"^\$\{\{\s*(secrets|vars)\.", value), (
            f"{key} 的值 {value!r} 不是以 secrets 或 vars context 開頭"
        )


# --- SDLCAIP2-12/SDLCAIP2-13: 正式站前端 callback/logout URL 注入 CI/CD ---

def test_frontend_callback_and_logout_urls_injected_from_repo_vars(backend_job):
    """SDLCAIP2-12 Scenario「CI 注入正式站 callback/logout URL」:
    backend job 的 terraform apply 步驟必須設定 TF_VAR_frontend_callback_urls
    與 TF_VAR_frontend_logout_urls，且皆來自 GitHub Actions repository
    Variables（${{ vars.* }}），而非 secrets 或字面常數。"""
    steps = backend_job.get("steps", [])
    apply_steps = [s for s in steps if "terraform apply" in (s.get("run") or "")]
    assert apply_steps, "找不到 terraform apply 步驟"
    env = apply_steps[0].get("env", {})

    assert "TF_VAR_frontend_callback_urls" in env, (
        "terraform apply 步驟缺少 TF_VAR_frontend_callback_urls"
    )
    assert "TF_VAR_frontend_logout_urls" in env, (
        "terraform apply 步驟缺少 TF_VAR_frontend_logout_urls"
    )
    assert env["TF_VAR_frontend_callback_urls"] == "${{ vars.FRONTEND_CALLBACK_URLS }}", (
        f"TF_VAR_frontend_callback_urls 的值不是來自 vars.FRONTEND_CALLBACK_URLS: "
        f"{env['TF_VAR_frontend_callback_urls']!r}"
    )
    assert env["TF_VAR_frontend_logout_urls"] == "${{ vars.FRONTEND_LOGOUT_URLS }}", (
        f"TF_VAR_frontend_logout_urls 的值不是來自 vars.FRONTEND_LOGOUT_URLS: "
        f"{env['TF_VAR_frontend_logout_urls']!r}"
    )


def test_cognito_app_client_references_frontend_url_vars():
    """SDLCAIP2-12 Scenario「Cognito App Client 白名單修正」:
    aws_cognito_user_pool_client 的 callback_urls/logout_urls 必須引用
    var.frontend_callback_urls/var.frontend_logout_urls，而非寫死的值，
    這樣 CI 注入的 TF_VAR_* 才能實際傳遞到白名單。"""
    content = COGNITO_TF_PATH.read_text(encoding="utf-8")
    assert re.search(r"callback_urls\s*=\s*var\.frontend_callback_urls", content), (
        "infra/cognito.tf 的 callback_urls 未引用 var.frontend_callback_urls"
    )
    assert re.search(r"logout_urls\s*=\s*var\.frontend_logout_urls", content), (
        "infra/cognito.tf 的 logout_urls 未引用 var.frontend_logout_urls"
    )


def test_apigateway_cors_references_frontend_callback_urls_var():
    """SDLCAIP2-13 Scenario「CI 注入的變數同時修正 API Gateway CORS」:
    aws_apigatewayv2_api.http_api 的 cors_configuration.allow_origins
    必須引用 var.frontend_callback_urls，而非寫死或 localhost 預設值。"""
    content = APIGATEWAY_TF_PATH.read_text(encoding="utf-8")
    assert re.search(r"allow_origins\s*=\s*var\.frontend_callback_urls", content), (
        "infra/apigateway.tf 的 CORS allow_origins 未引用 var.frontend_callback_urls"
    )


def test_s3_bucket_cors_references_frontend_callback_urls_var():
    """SDLCAIP2-13 Scenario「S3 bucket CORS 也同步修正」:
    音檔 S3 bucket 的 cors_rule.allowed_origins 必須引用
    var.frontend_callback_urls，確保上傳流程走同一組正式站網址。"""
    content = S3_TF_PATH.read_text(encoding="utf-8")
    assert re.search(r"allowed_origins\s*=\s*var\.frontend_callback_urls", content), (
        "infra/s3.tf 的 CORS allowed_origins 未引用 var.frontend_callback_urls"
    )


# --- Scenario 3: 部署失敗時清楚可見 ---

def test_backend_job_has_no_top_level_notification_step(backend_job):
    """規格明確表示不需要額外通知機制；確認沒有引入非必要的第三方通知 action。"""
    steps = backend_job.get("steps", [])
    for step in steps:
        uses = step.get("uses", "")
        assert "slack" not in uses.lower()
        assert "notify" not in uses.lower()
