"""SDLCAIP2-32：已保留會議紀錄歷史列表與詳情唯讀瀏覽 UI（前端）— 驗收測試。

Feature: 歷史紀錄列表與詳情唯讀瀏覽
覆蓋 G1 核准的 Gherkin 驗收條件中，可用靜態內容檢查驗證的部分：
  - 導覽入口 #history-nav-btn 存在且繫結 openHistoryList()
  - #view-history、#view-history-detail 兩個 view 與其內部關鍵 DOM id 存在
  - openHistoryList()/openMeetingDetail()/renderMinutesReadOnly()/
    switchHistoryTab()/fmtDateTime() 五個函式皆存在，且函式內容呼叫
    對應的既有後端端點、操作對應 DOM id
  - renderMinutesReadOnly() 產生的 DOM 不含 contenteditable/ondblclick/
    onchange="markModified()"（唯讀骨架，供 SDLCAIP2-17 疊加編輯模式）

實際瀏覽器互動行為（點擊列表項目切換畫面、空狀態顯示、404 錯誤顯示、
呼叫 API 後的實際 DOM 更新）屬於前端 JS 執行期行為，由
tests/e2e/history-detail.spec.ts 涵蓋（見 docs/design/SDLCAIP2-32.md）；
本檔案只驗證靜態 HTML/JS 原始碼結構，沿用既有
src/tests/test_ui_copy.py、test_speaker_naming_ui.py 的字串比對慣例。
"""
from pathlib import Path

FRONTEND_HTML = (Path(__file__).parent.parent / "frontend" / "index.html").read_text(encoding="utf-8")


# ─── Scenario: 導覽入口 ────────────────────────────────────

def test_history_nav_btn_exists_and_bound():
    assert 'id="history-nav-btn"' in FRONTEND_HTML
    idx = FRONTEND_HTML.index('id="history-nav-btn"')
    snippet = FRONTEND_HTML[idx:idx + 200]
    assert 'onclick="openHistoryList()"' in snippet


# ─── Scenario: 歷史列表顯示已保留的會議紀錄 / 空狀態 ────────────

def _history_view_html():
    start = FRONTEND_HTML.index('id="view-history"')
    end = FRONTEND_HTML.index('id="view-history-detail"')
    return FRONTEND_HTML[start:end]


def test_view_history_has_table_and_empty_state():
    view_html = _history_view_html()
    assert 'id="history-table"' in view_html
    assert 'id="history-tbody"' in view_html
    assert 'id="history-empty"' in view_html
    assert "尚無已保留的會議紀錄" in view_html


def test_open_history_list_defined_and_calls_meetings_endpoint():
    assert "async function openHistoryList()" in FRONTEND_HTML
    idx = FRONTEND_HTML.index("async function openHistoryList()")
    snippet = FRONTEND_HTML[idx:idx + 1200]
    assert "/api/meetings" in snippet
    assert "showView('view-history')" in snippet
    assert "history-tbody" in snippet
    assert "history-empty" in snippet
    assert "toast('讀取歷史紀錄失敗')" in snippet


def test_history_row_click_calls_open_meeting_detail():
    idx = FRONTEND_HTML.index("async function openHistoryList()")
    snippet = FRONTEND_HTML[idx:idx + 1200]
    assert "onclick=\"openMeetingDetail(" in snippet
    assert "fmtDateTime(" in snippet


# ─── Scenario: 點擊列表項目導向詳情頁 ───────────────────────

def _history_detail_view_html():
    start = FRONTEND_HTML.index('id="view-history-detail"')
    end = FRONTEND_HTML.index('</main>')
    return FRONTEND_HTML[start:end]


def test_view_history_detail_has_expected_ids():
    detail_html = _history_detail_view_html()
    for expected_id in [
        "history-detail-title",
        "history-detail-error",
        "history-detail-error-msg",
        "history-detail-body",
        "history-tab-btn-minutes",
        "history-tab-btn-transcript",
        "history-tab-minutes",
        "history-tab-transcript",
        "history-summary-text",
        "history-action-tbody",
        "history-decision-list",
        "history-topics-container",
        "history-transcript-container",
    ]:
        assert f'id="{expected_id}"' in detail_html, f"missing id: {expected_id}"


def test_open_meeting_detail_defined_and_calls_meeting_endpoint():
    assert "async function openMeetingDetail(meetingId)" in FRONTEND_HTML
    idx = FRONTEND_HTML.index("async function openMeetingDetail(meetingId)")
    snippet = FRONTEND_HTML[idx:idx + 1200]
    assert "/api/meetings/${meetingId}" in snippet
    assert "showView('view-history-detail')" in snippet
    assert "res.status === 404" in snippet
    assert "renderMinutesReadOnly(data)" in snippet


# ─── Scenario: 詳情頁以唯讀方式顯示完整內容 ────────────────────

def _render_minutes_readonly_snippet():
    idx = FRONTEND_HTML.index("function renderMinutesReadOnly(data)")
    end = FRONTEND_HTML.index("function toggleHistoryTopic", idx)
    return FRONTEND_HTML[idx:end]


def test_render_minutes_readonly_writes_expected_ids():
    snippet = _render_minutes_readonly_snippet()
    for expected_id in [
        "history-detail-title",
        "history-summary-text",
        "history-action-tbody",
        "history-decision-list",
        "history-topics-container",
        "history-transcript-container",
    ]:
        assert expected_id in snippet, f"missing id reference: {expected_id}"
    assert "data.transcript_text" in snippet


def test_render_minutes_readonly_has_no_edit_affordances():
    """唯讀渲染不得包含 contenteditable/ondblclick/markModified，
    以與既有 renderMinutes() 的可編輯行為明確分離。"""
    snippet = _render_minutes_readonly_snippet()
    assert "contenteditable" not in snippet
    assert "ondblclick" not in snippet
    assert "markModified" not in snippet


def test_render_minutes_readonly_uses_independent_topic_toggle():
    """討論重點 toggle 使用獨立的 toggleHistoryTopic/history-topic-body-*/
    history-topic-arrow-*，避免與既有 view-result 的 toggleTopic()/
    topic-body-* 撞名。"""
    snippet = _render_minutes_readonly_snippet()
    assert "toggleHistoryTopic(" in snippet
    assert "history-topic-body-" in snippet
    assert "history-topic-arrow-" in snippet


def test_render_minutes_readonly_shows_meeting_info_not_included():
    """AC4 只列舉摘要／待辦事項／決定事項／討論重點，不含 meeting_info。"""
    snippet = _render_minutes_readonly_snippet()
    assert "meeting_info" not in snippet


# ─── Scenario: 詳情頁遇到 404 時顯示錯誤並可返回列表 ─────────────

def test_history_detail_error_view_has_back_button():
    detail_html = _history_detail_view_html()
    error_idx = detail_html.index('id="history-detail-error"')
    error_snippet = detail_html[error_idx:error_idx + 400]
    assert "showView('view-history')" in error_snippet
    assert "返回歷史列表" in error_snippet


def test_open_meeting_detail_404_fallback_message():
    idx = FRONTEND_HTML.index("async function openMeetingDetail(meetingId)")
    snippet = FRONTEND_HTML[idx:idx + 1200]
    assert "找不到此會議紀錄" in snippet


# ─── 輔助函式 ────────────────────────────────────────────

def test_switch_history_tab_defined():
    assert "function switchHistoryTab(tab)" in FRONTEND_HTML
    idx = FRONTEND_HTML.index("function switchHistoryTab(tab)")
    snippet = FRONTEND_HTML[idx:idx + 600]
    assert "history-tab-minutes" in snippet
    assert "history-tab-transcript" in snippet
    assert "history-tab-btn-minutes" in snippet
    assert "history-tab-btn-transcript" in snippet


def test_fmt_date_time_defined():
    assert "function fmtDateTime(epochSeconds)" in FRONTEND_HTML
    idx = FRONTEND_HTML.index("function fmtDateTime(epochSeconds)")
    snippet = FRONTEND_HTML[idx:idx + 200]
    assert "toLocaleString('zh-TW')" in snippet
