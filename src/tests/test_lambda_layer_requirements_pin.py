"""SDLCAIP2-14: 靜態驗證 src/requirements-lambda.txt 與 src/requirements.txt
的 assemblyai 版本鎖定維持同步。

正式環境事故根因：requirements-lambda.txt 的 assemblyai 版本缺少上限，
build_lambda_layer.sh 重建 Layer 時解析到 0.65.0+（移除了
assemblyai.transcriber.api，src/progress.py 有 import），導致 Lambda 每次
cold start 皆因 `cannot import name 'api' from 'assemblyai.transcriber'`
而 crash。

無法在測試環境中實際安裝套件、建 Layer、觸發 Lambda cold start 來驗證
（成本高，且會受測試環境套件快取/套件源版本波動影響，不穩定），因此比照
本專案既有慣例（`src/tests/test_ci_backend_job.py`：以正規表示式解析設定
檔文字、斷言結構/內容一致，不實際跑 terraform/AWS），改用靜態文字比對。
"""
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REQUIREMENTS_LAMBDA_PATH = REPO_ROOT / "src" / "requirements-lambda.txt"
REQUIREMENTS_PATH = REPO_ROOT / "src" / "requirements.txt"

ASSEMBLYAI_LINE_PATTERN = re.compile(r"^assemblyai\s*(.+)$")


def _find_assemblyai_line(path: Path):
    """逐行掃描檔案，回傳 (完整原始行, 版本限制字串) 或 None（找不到）。"""
    content = path.read_text(encoding="utf-8")
    for raw_line in content.splitlines():
        line = raw_line.strip()
        match = ASSEMBLYAI_LINE_PATTERN.match(line)
        if match:
            return line, match.group(1).strip()
    return None


def _strip_inline_comment(constraint: str) -> str:
    return constraint.split("#", 1)[0].strip()


def test_both_requirements_files_have_an_assemblyai_line():
    lambda_result = _find_assemblyai_line(REQUIREMENTS_LAMBDA_PATH)
    main_result = _find_assemblyai_line(REQUIREMENTS_PATH)
    assert lambda_result is not None, (
        "src/requirements-lambda.txt 找不到 assemblyai 這一行，"
        "檔案格式可能跑掉了"
    )
    assert main_result is not None, (
        "src/requirements.txt 找不到 assemblyai 這一行，"
        "檔案格式可能跑掉了"
    )


def test_assemblyai_version_constraints_stay_in_sync_and_capped_below_0_65_0():
    _, lambda_constraint = _find_assemblyai_line(REQUIREMENTS_LAMBDA_PATH)
    _, main_constraint = _find_assemblyai_line(REQUIREMENTS_PATH)

    lambda_constraint_no_comment = _strip_inline_comment(lambda_constraint)
    main_constraint_no_comment = _strip_inline_comment(main_constraint)

    assert lambda_constraint_no_comment == main_constraint_no_comment, (
        "src/requirements-lambda.txt 與 src/requirements.txt 的 assemblyai "
        f"版本限制不一致: {lambda_constraint_no_comment!r} != "
        f"{main_constraint_no_comment!r} —— 兩份 requirements 必須同步鎖版，"
        "否則 Lambda Layer 建置會解析到與正式環境不同的 assemblyai 版本"
    )

    # 這是本次事故的確切邊界，直接寫死斷言，不用泛用 semver 邏輯，避免漏掉
    # regression：0.65.0+ 移除了 assemblyai.transcriber.api（src/progress.py
    # 有 import），是造成正式環境 Lambda 每次 cold start 皆 crash 的根因。
    assert "<0.65.0" in lambda_constraint_no_comment, (
        f"src/requirements-lambda.txt 的 assemblyai 版本限制 "
        f"{lambda_constraint_no_comment!r} 未鎖定 <0.65.0 上限，"
        "0.65.0+ 移除了 assemblyai.transcriber.api（src/progress.py 有 "
        "import），會導致 Lambda 每次 cold start 皆因 ImportModuleError crash"
    )


def test_requirements_lambda_assemblyai_line_has_explanatory_comment():
    lambda_line, _ = _find_assemblyai_line(REQUIREMENTS_LAMBDA_PATH)
    assert "#" in lambda_line and "assemblyai.transcriber.api" in lambda_line, (
        "src/requirements-lambda.txt 的 assemblyai 版本限制缺少解釋性 "
        "comment，未來有人手動改版本時，鎖 <0.65.0 的理由會被無聲丟失"
    )
