"""SDLCAIP2-17：已保留會議紀錄詳情頁編輯 UI（拆分後改寫範圍）— 驗收測試。

Feature: 在 SDLCAIP2-32 已合併的唯讀詳情頁上疊加編輯模式
覆蓋 G1 核准的 Gherkin 驗收條件中，可用靜態內容檢查驗證的部分：
  - 「編輯」／「儲存」／「取消」三個按鈕存在且預設顯示/隱藏狀態正確
  - 會議資訊欄位（history-date/time/location/participants）存在且預設 disabled
  - enableHistoryEditMode()/cancelHistoryEdit()/saveHistoryEdit()/
    buildHistoryEditPayload()/renderHistoryMeetingInfo() 五個函式皆存在，
    且函式內容操作對應的 DOM id、呼叫 PATCH /api/meetings/{meeting_id}
  - openMeetingDetail() 有在成功讀取後保存 state.detail 並重新初始化編輯
    狀態（exitHistoryEditMode）
  - 儲存失敗（含 404）路徑不呼叫任何渲染/復原函式，只 toast 訊息

實際瀏覽器互動行為（點擊編輯切換可輸入狀態、雙擊欄位進入 contenteditable、
儲存成功/失敗/404 的畫面行為、取消還原輸入）屬於前端 JS 執行期行為，由
tests/e2e/history-detail-edit.spec.ts 涵蓋；本檔案只驗證靜態 HTML/JS
原始碼結構，沿用既有 test_history_detail_ui.py 的字串比對慣例。
"""
from pathlib import Path

FRONTEND_HTML = (Path(__file__).parent.parent / "frontend" / "index.html").read_text(encoding="utf-8")


def _history_detail_view_html():
    start = FRONTEND_HTML.index('id="view-history-detail"')
    end = FRONTEND_HTML.index('</main>')
    return FRONTEND_HTML[start:end]


# ─── Scenario: 詳情頁提供編輯模式切換 ───────────────────────

def test_edit_save_cancel_buttons_exist_with_correct_default_visibility():
    detail_html = _history_detail_view_html()
    assert 'id="history-edit-btn"' in detail_html
    assert 'onclick="enableHistoryEditMode()"' in detail_html

    save_idx = detail_html.index('id="history-save-btn"')
    save_snippet = detail_html[save_idx:save_idx + 200]
    assert 'style="display:none;"' in save_snippet
    assert 'onclick="saveHistoryEdit()"' in save_snippet

    cancel_idx = detail_html.index('id="history-cancel-btn"')
    cancel_snippet = detail_html[cancel_idx:cancel_idx + 200]
    assert 'style="display:none;"' in cancel_snippet
    assert 'onclick="cancelHistoryEdit()"' in cancel_snippet


def test_meeting_info_fields_exist_and_default_disabled():
    detail_html = _history_detail_view_html()
    for field_id in ["history-date", "history-time", "history-location", "history-participants"]:
        assert f'id="{field_id}"' in detail_html, f"missing id: {field_id}"
        idx = detail_html.index(f'id="{field_id}"')
        snippet = detail_html[idx:idx + 120]
        assert "disabled" in snippet


def _enable_edit_mode_snippet():
    idx = FRONTEND_HTML.index("function enableHistoryEditMode()")
    end = FRONTEND_HTML.index("function cancelHistoryEdit()", idx)
    return FRONTEND_HTML[idx:end]


def test_enable_history_edit_mode_toggles_buttons_and_unlocks_fields():
    snippet = _enable_edit_mode_snippet()
    assert "history-edit-btn" in snippet
    assert "history-save-btn" in snippet
    assert "history-cancel-btn" in snippet
    assert "history-date" in snippet
    assert "disabled = false" in snippet
    assert "enableHistoryFieldEdit(this)" in snippet
    assert "history-summary-text" in snippet
    assert "history-action-tbody td" in snippet
    assert "history-decision-list li" in snippet
    assert "history-topics-container .topic-body" in snippet


# ─── Scenario: 儲存成功後畫面顯示最新內容 ────────────────────

def _save_history_edit_snippet():
    idx = FRONTEND_HTML.index("async function saveHistoryEdit()")
    return FRONTEND_HTML[idx:idx + 1600]


def test_save_history_edit_calls_patch_endpoint():
    snippet = _save_history_edit_snippet()
    assert "/api/meetings/${meetingId}" in snippet
    assert "method: 'PATCH'" in snippet
    assert "buildHistoryEditPayload()" in snippet


def test_save_history_edit_success_rerenders_readonly_and_toasts():
    snippet = _save_history_edit_snippet()
    assert "state.detail = data;" in snippet
    assert "renderMinutesReadOnly(data)" in snippet
    assert "renderHistoryMeetingInfo(data)" in snippet
    assert "exitHistoryEditMode()" in snippet
    assert "toast('已儲存')" in snippet


# ─── Scenario: 儲存失敗時保留使用者輸入 / 編輯時遇到 404 顯示錯誤 ─────

def test_save_history_edit_404_and_failure_do_not_touch_dom():
    snippet = _save_history_edit_snippet()
    error_idx = snippet.index("if (res.status === 404)")
    error_snippet = snippet[error_idx:error_idx + 150]
    assert "toast('找不到此會議紀錄')" in error_snippet
    assert "renderMinutesReadOnly" not in error_snippet
    assert "exitHistoryEditMode" not in error_snippet

    catch_idx = snippet.index("} catch (e) {")
    catch_snippet = snippet[catch_idx:catch_idx + 150]
    assert "toast('儲存失敗，請稍後再試')" in catch_snippet
    assert "renderMinutesReadOnly" not in catch_snippet
    assert "exitHistoryEditMode" not in catch_snippet


def test_build_history_edit_payload_full_object_shape():
    idx = FRONTEND_HTML.index("function buildHistoryEditPayload()")
    end = FRONTEND_HTML.index("async function saveHistoryEdit()", idx)
    snippet = FRONTEND_HTML[idx:end]
    for expected in [
        "job_id: m.job_id",
        "template: m.template",
        "meeting_info:",
        "summary:",
        "action_items:",
        "decisions:",
        "sections:",
        "history-date",
        "history-summary-text",
        "history-action-tbody",
        "history-decision-list",
        "history-topic-body-",
    ]:
        assert expected in snippet, f"missing: {expected}"


# ─── Scenario 支援：取消 ────────────────────────────────────

def test_cancel_history_edit_restores_readonly_from_snapshot():
    idx = FRONTEND_HTML.index("function cancelHistoryEdit()")
    end = FRONTEND_HTML.index("function buildHistoryEditPayload()", idx)
    snippet = FRONTEND_HTML[idx:end]
    assert "renderMinutesReadOnly(state.detail)" in snippet
    assert "renderHistoryMeetingInfo(state.detail)" in snippet
    assert "exitHistoryEditMode()" in snippet


# ─── openMeetingDetail 整合點 ────────────────────────────────

def test_open_meeting_detail_stores_state_detail_and_resets_edit_mode():
    idx = FRONTEND_HTML.index("async function openMeetingDetail(meetingId)")
    snippet = FRONTEND_HTML[idx:idx + 1400]
    assert "exitHistoryEditMode()" in snippet
    assert "state.detail = data;" in snippet
    assert "renderHistoryMeetingInfo(data)" in snippet
