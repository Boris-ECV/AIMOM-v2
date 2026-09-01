"""SDLCAIP2-7：上傳頁與處理中頁面文案精簡 — 驗收測試。

Feature: 上傳與處理中頁面文案精簡
覆蓋 G1 核准的 Gherkin 驗收條件：
  Scenario: 上傳頁提示文字更新
  Scenario: 處理中頁面訊息更新且不含供應商/模型名稱
"""
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app import app
import jobstore

client = TestClient(app)

FRONTEND_HTML = (Path(__file__).parent.parent / "frontend" / "index.html").read_text(encoding="utf-8")


# ─── Scenario: 上傳頁提示文字更新 ─────────────────────────────

def test_upload_page_drop_zone_text():
    """拖放區塊文字應顯示「拖放錄音檔至此，或點擊選取」。"""
    assert "拖放錄音檔至此，或點擊選取" in FRONTEND_HTML


def test_upload_page_privacy_text():
    """隱私說明文字應顯示「本系統不會儲存您的錄音檔，處理完成後可手動清除暫存資料。」
    （而非舊版「不長期」用詞，因為系統其實完全不儲存錄音檔）。"""
    assert "本系統不會儲存您的錄音檔，處理完成後可手動清除暫存資料。" in FRONTEND_HTML
    assert "不長期" not in FRONTEND_HTML


# ─── Scenario: 處理中頁面訊息更新且不含供應商/模型名稱 ──────────

def _setup_job(job_id="ui-copy-job-001"):
    jobstore.create_job(
        job_id,
        filename="meeting.mp3",
        duration_sec=60.0,
        size_bytes=1024,
        audio_path=f"/tmp/{job_id}/audio.mp3",
    )
    return job_id


def test_transcribe_progress_message_at_15_percent():
    """轉錄剛送出（15% 進度點）應先寫入「準備轉錄...」且不包含 AssemblyAI 字樣。

    /transcribe 在呼叫 _submit_to_assemblyai() 之前會先呼叫
    update_progress(job_id, "transcribing", 15, "準備轉錄...")（見 transcribe.py），
    這裡在 _submit_to_assemblyai 的 side_effect 裡讀取當下的 job 狀態，
    以驗證 15% 這個中繼進度點的訊息內容。
    """
    job_id = _setup_job("ui-copy-job-15pct")
    captured = {}

    def _capture_mid_progress(job):
        captured["job"] = jobstore.get_job(job_id)
        return "aai-transcript-captured"

    with patch("transcribe._submit_to_assemblyai", side_effect=_capture_mid_progress):
        response = client.post("/api/transcribe", json={"job_id": job_id})

    assert response.status_code == 200
    assert captured["job"]["progress"] == 15
    assert captured["job"]["message"] == "準備轉錄..."
    assert "AssemblyAI" not in captured["job"]["message"]


def test_transcribe_progress_message_at_20_percent():
    """轉錄送出成功後（20% 進度點）應顯示「等待轉錄完成...」且不包含 AssemblyAI 字樣。"""
    job_id = _setup_job("ui-copy-job-20pct")

    with patch("transcribe._submit_to_assemblyai", return_value="aai-transcript-abc"):
        response = client.post("/api/transcribe", json={"job_id": job_id})

    assert response.status_code == 200
    data = response.json()
    assert data["progress"] == 20
    assert data["message"] == "等待轉錄完成..."
    assert "AssemblyAI" not in data["message"]

    job = jobstore.get_job(job_id)
    assert job["message"] == "等待轉錄完成..."
    assert "AssemblyAI" not in job["message"]


def test_transcribe_submit_failure_message_may_contain_provider_detail():
    """範圍說明：/transcribe 送出失敗時的錯誤訊息（例如 AssemblyAI 回傳的錯誤內容）
    不在本story驗收範圍內（僅涵蓋 15%/20% 正常進度訊息），此處記錄現況以避免誤解為回歸。"""
    job_id = _setup_job("ui-copy-job-error")
    with patch("transcribe._submit_to_assemblyai", side_effect=RuntimeError("AssemblyAI 送出失敗：boom")):
        response = client.post("/api/transcribe", json={"job_id": job_id})
    assert response.status_code == 500


def test_stage_transcribed_label_text_excludes_provider_name():
    """語音轉文字階段說明應顯示「處理中（轉錄 + 發言人同步完成）」且不包含 AssemblyAI 字樣。"""
    assert "處理中（轉錄 + 發言人同步完成）" in FRONTEND_HTML
    # 只檢查這段固定文案本身，不逐字比對而是確認該字串出現的上下文不含 AssemblyAI
    idx = FRONTEND_HTML.index("處理中（轉錄 + 發言人同步完成）")
    snippet = FRONTEND_HTML[max(0, idx - 200):idx + 200]
    assert "AssemblyAI" not in snippet


def test_stage_done_label_text_excludes_model_name():
    """AI 整理階段說明應顯示「摘要與整理」且不包含 GPT-4o 字樣。"""
    assert "摘要與整理" in FRONTEND_HTML
    idx = FRONTEND_HTML.index("摘要與整理")
    snippet = FRONTEND_HTML[max(0, idx - 200):idx + 200]
    assert "GPT-4o" not in snippet


def test_frontend_html_never_mentions_gpt4o_or_assemblyai_in_visible_stage_labels():
    """全域防呆：處理中頁面的三個 stage-msg 區塊文字皆不應出現供應商/模型名稱。
    （API 註解、內部程式碼中的說明性註解不在此限，這裡只掃描 view-progress 區塊）"""
    start = FRONTEND_HTML.index('id="view-progress"')
    end = FRONTEND_HTML.index("<!-- ============ RESULT VIEW", start)
    progress_view_html = FRONTEND_HTML[start:end]
    assert "AssemblyAI" not in progress_view_html
    assert "GPT-4o" not in progress_view_html
