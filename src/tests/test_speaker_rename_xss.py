"""SDLCAIP2-31：講者重新命名輸入框渲染未轉義使用者輸入，DOM-based XSS 風險 — 驗收測試。

Feature: 講者重新命名輸入框 XSS 修補
覆蓋 G1 核准的 Gherkin 驗收條件中，可用靜態內容檢查驗證的部分：
  - esc() 應同時轉義 &, <, >, " 四個字元，且 & 的替換必須排在最前面
    （避免 &quot; 被自身的 & 替換規則二次轉義）。
  - renderTranscript() 中 #rename-rows 的兩個注入點
    （<label>${sp}</label> 與 value="${state.speakers[sp] || sp}"）
    都必須改為透過 esc() 輸出，onchange 內的 sp 亦同（防禦性修補）。

實際 DOM 渲染結果（value 屬性讀出的字面值是否被截斷、是否多出
onmouseover 等額外屬性、是否觸發 alert）屬於瀏覽器執行期行為，
由 tests/e2e/speaker-rename-xss.spec.ts 涵蓋（見
docs/design/SDLCAIP2-31.md）；本檔案只驗證原始碼字串層級的修補是否到位，
沿用既有 src/tests/test_speaker_naming_ui.py 的字串比對慣例。
"""
import re
from pathlib import Path

FRONTEND_HTML = (Path(__file__).parent.parent / "frontend" / "index.html").read_text(encoding="utf-8")


# ─── esc() 應同時轉義 &, <, >, " ────────────────────────────────

def _esc_function_body():
    idx = FRONTEND_HTML.index("function esc(str) {")
    end = FRONTEND_HTML.index("}", idx)
    return FRONTEND_HTML[idx:end + 1]


def test_esc_escapes_double_quote():
    """esc() 應新增 " -> &quot; 的轉義，不移除既有的 &, <, > 轉義。"""
    body = _esc_function_body()
    assert "&amp;" in body
    assert "&lt;" in body
    assert "&gt;" in body
    assert "&quot;" in body
    assert re.search(r"replace\(/\"/g,\s*'&quot;'\)", body)


def test_esc_quote_replace_is_after_ampersand_replace():
    """" 的 replace 必須排在 & 的 replace 之後，避免 &quot; 中的 & 被
    自身的 &amp; 規則二次轉義（顧此失彼會讓輸出變成 &amp;quot;）。"""
    body = _esc_function_body()
    amp_pos = body.index("replace(/&/g")
    quote_pos = body.index("replace(/\"/g")
    assert amp_pos < quote_pos


# ─── renderTranscript() #rename-rows 的兩個注入點都必須套用 esc() ────

def _render_transcript_rename_rows_snippet():
    idx = FRONTEND_HTML.index("function renderTranscript() {")
    end = FRONTEND_HTML.index("const container = document.getElementById('transcript-container');", idx)
    return FRONTEND_HTML[idx:end]


def test_rename_row_label_uses_esc():
    snippet = _render_transcript_rename_rows_snippet()
    assert "<label>${esc(sp)}</label>" in snippet
    assert "<label>${sp}</label>" not in snippet


def test_rename_row_input_value_uses_esc():
    snippet = _render_transcript_rename_rows_snippet()
    assert 'value="${esc(state.speakers[sp] || sp)}"' in snippet
    assert 'value="${state.speakers[sp] || sp}"' not in snippet


def test_rename_row_onchange_sp_uses_esc_defense_in_depth():
    """onchange="renameSpeaker('${sp}', this.value)" 中的 sp 也應以 esc()
    包裹，防止單引號斷開屬性（雖非 Gherkin 明確斷言，但屬同類漏洞）。"""
    snippet = _render_transcript_rename_rows_snippet()
    assert "renameSpeaker('${esc(sp)}', this.value)" in snippet
    assert "renameSpeaker('${sp}', this.value)" not in snippet


# ─── 不應影響逐字稿本文渲染（現有 esc() 呼叫點維持不變）── 回歸檢查 ──

def test_transcript_body_speaker_chip_and_text_still_use_esc():
    """seg-speaker chip 與 seg-text 兩處既有 esc() 呼叫不受本次修補影響。"""
    assert '<span class="speaker-chip" style="background:${color}">${esc(displayName)}</span>' in FRONTEND_HTML
    assert '<span class="seg-text">${esc(seg.text)}</span>' in FRONTEND_HTML
