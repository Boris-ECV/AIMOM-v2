"""SDLCAIP2-18：逐字稿分頁講者命名 UI（前端）— 驗收測試。

Feature: 逐字稿分頁講者命名 UI
覆蓋 G1 核准的 Gherkin 驗收條件中，可用靜態內容檢查驗證的部分：
  Scenario: 逐字稿分頁列出偵測到的講者標籤與命名輸入框（既有元素/新增送出按鈕存在）
  Scenario: 畫面明確告知命名的影響範圍

互動行為（送出按鈕呼叫 API、更新逐字稿顯示、未命名維持原標籤、未知標籤不報錯）
屬於前端 JS 執行期行為，由 tests/e2e/speaker-naming.spec.ts 涵蓋（見
docs/design/SDLCAIP2-18.md）；本檔案只驗證靜態 HTML 結構與文案，
沿用既有 src/tests/test_ui_copy.py 的字串比對慣例。
"""
from pathlib import Path

FRONTEND_HTML = (Path(__file__).parent.parent / "frontend" / "index.html").read_text(encoding="utf-8")


# ─── Scenario: 逐字稿分頁列出偵測到的講者標籤與命名輸入框 ──────

def _speaker_rename_area_html():
    start = FRONTEND_HTML.index('id="speaker-rename-area"')
    end = FRONTEND_HTML.index('<div class="card">', start)
    return FRONTEND_HTML[start:end]


def test_speaker_rename_area_has_submit_button():
    """#speaker-rename-area 應包含一個送出按鈕，繫結到 submitSpeakerNames()。"""
    area_html = _speaker_rename_area_html()
    assert 'id="submit-speaker-names-btn"' in area_html
    assert "onclick=\"submitSpeakerNames()\"" in area_html


def test_submit_speaker_names_function_defined():
    """submitSpeakerNames() 函式應存在，且呼叫既有 POST /api/speaker-names。"""
    assert "async function submitSpeakerNames()" in FRONTEND_HTML
    idx = FRONTEND_HTML.index("async function submitSpeakerNames()")
    snippet = FRONTEND_HTML[idx:idx + 1500]
    assert "/api/speaker-names" in snippet
    assert "state.segments = data.segments" in snippet
    assert "state.speakers = {}" in snippet


# ─── Scenario: 畫面明確告知命名的影響範圍 ──────────────────────

def test_speaker_rename_area_has_scope_disclosure_text():
    """#speaker-rename-area 應包含明確的影響範圍提示文字（只更新逐字稿分頁與
    匯出檔案，不更新會議紀錄分頁的參與者／待辦事項負責人）。"""
    area_html = _speaker_rename_area_html()
    assert "只會更新此逐字稿分頁與匯出檔案" in area_html
    assert "不會更新「會議紀錄」分頁的參與者／待辦事項負責人" in area_html
