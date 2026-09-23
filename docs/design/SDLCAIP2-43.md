# 設計文件 — SDLCAIP2-43 PDF 匯出中英文混合內容換行修正

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-43）。現況（已讀 `src/export.py` 確認）：

- `_wrap(text, width=40)`（第 170-173 行）是純字元數切片
  （`text[i:i+width]`），完全不量測實際渲染寬度，也不管字元邊界是否落在英文
  單字中間。且只在 `_build_pdf` 的摘要（第 133 行）與討論重點內容
  （第 160 行）兩處被呼叫。
- 會議資訊（第 128-130 行）、決定事項（第 136-142 行）、待辦事項
  （第 144-153 行）、討論重點標題（第 159 行）都是直接呼叫 `_line()` →
  `c.drawString()`，完全沒有換行或寬度檢查，內容一長就會直接超出頁面右緣。
- `_line()` 閉包（第 117-124 行）只處理垂直方向的分頁（`y < 60` 時
  `c.showPage()`），不處理水平方向溢出。
- `_CJK_FONT`（第 38 行，= `"NotoSansTC"`，延續 SDLCAIP2-38 內嵌字型設定）
  已於模組載入時透過 `pdfmetrics.registerFont(TTFont(...))` 註冊完成，可直接
  搭配 `pdfmetrics.stringWidth(text, _CJK_FONT, size)` 使用。

依賴 SDLCAIP2-38（Done）：延續其 `_CJK_FONT` 常數，不重新設計字型註冊。

範圍外（依 ticket 明列，設計不逾越）：docx／前端 Markdown 匯出排版、各家
PDF 檢視器逐一視覺回歸、CJK 以外非 ASCII 語系斷行、分頁/分欄改版、
export API 請求/回應格式或狀態碼。

## 介面/API 契約
無，本 Story 不涉及對外 API 變更。`GET /api/export/{job_id}` 與
`GET /api/export/meetings/{meeting_id}`（`format=pdf`）既有請求/回應格式、
狀態碼（200／404／400）完全不變——本故事只調整 `_build_pdf` 內部的換行邏輯，
是純粹的內部渲染修正。

## 資料模型
無新增資料模型。本故事不觸及 DynamoDB 資料表或 `minutes` JSON 結構。

## 關鍵技術決策

1. **新增一個獨立的寬度感知換行函式 `_wrap_by_width(text, max_width, font=_CJK_FONT, size=12)`，取代舊的 `_wrap(text, width)`（直接移除 `_wrap`，不保留相容殼）。**
   理由：舊 `_wrap` 的字元數切片與新的寬度量測邏輯在概念上完全不相容（一個
   假設固定寬度、一個依實際渲染寬度動態決定斷點），保留舊函式只會製造誤用
   風險；`_wrap` 目前只有 `_build_pdf` 內兩處呼叫（皆會被本故事改掉），確認
   無其他呼叫點（已用 Grep 確認 `src/` 下僅 `export.py` 使用），移除是安全的。

2. **可用內容寬度（content width）＝頁寬扣除左右邊界，右邊界比照現有左邊界
   同為 50pt：`_CONTENT_WIDTH = A4[0] - 50 - 50`（新增模組常數
   `_PAGE_MARGIN_L = _PAGE_MARGIN_R = 50`，`_line()` 的
   `c.drawString(50, y, text)` 改用 `_PAGE_MARGIN_L` 取代硬編碼 `50`）。**
   理由：現有程式碼只定義了左邊界（`drawString` 的 x=50），右邊界從未定義
   過（現況就是文字直接畫出頁面）。Spec 只要求「不超過頁面可用內容寬度
   （頁寬扣除左右邊界）」，但未指定右邊界確切數值——這是實作需要的具體
   數字，不是產品行為，故由本設計直接決定：採用與左邊界對稱的 50pt，是
   PDF 排版最常見的預設慣例，且與現有左邊界一致（視覺對稱），不引入額外
   的產品決策空間。

3. **斷詞規則：用正規表示式 `_WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[^A-Za-z0-9]")` 把文字切成 token 序列——ASCII 英數字的連續片段（含系統名稱、專有名詞）視為一個不可切割的 token；其餘每個字元（CJK 字、標點、空白）各自成一個 token。**
   理由：直接對應 spec Scenario 2「英文單字不會被從中間硬拆」的驗收條件，
   同時保留 CJK「可在任兩字元間換行」的既有直覺行為（中文本來就沒有西方
   語言的「單字」邊界概念，逐字換行是中文排版常態，spec 也明確只要求 ASCII
   單字不被拆，未要求 CJK 也要有詞邊界斷行——若真的做 CJK 分詞斷行需要額外
   的分詞函式庫，屬於 spec 範圍外的過度設計）。用單一正規表示式取代逐字元
   判斷迴圈的邏輯更簡單、可讀性更高。

4. **換行演算法：逐 token 累加至目前行，用 `pdfmetrics.stringWidth(candidate, font, size)` 量測「目前行 + 下一個 token」的寬度，一旦超過 `max_width` 就把目前行推入結果、以該 token 開新行；新行起始若該 token 是空白則捨棄（避免換行後行首多一個空格）。**
   理由：貼齊 spec Scenario 1「以 NotoSansTC 字型、對應字級量測的渲染寬度」
   的要求——`stringWidth` 就是 reportlab 官方提供、専為此用途設計的 API
   （ticket 依賴段落已指名可直接用）。逐 token 累加式量測是換行演算法的
   標準做法（貪婪演算法），不需要更複雜的最佳斷行（如 Knuth-Plass），
   spec 也未要求逐行寬度最佳化，貪婪法已足夠滿足所有 4 個 Gherkin 情境。

5. **邊界情況：單一 token（多半是很長的英文單字/URL）本身的量測寬度就已經超過 `max_width` 時，該 token 仍獨占一行整段輸出，不強制二次切割。**
   理由：這是 Scenario 1（每行不超寬）與 Scenario 2（英文單字不被硬拆）
   兩條驗收條件在此極端輸入下彼此邏輯衝突時的必要取捨——spec 明確禁止
   拆開一個英文單字，因此在「單字本身就比整頁可用寬度還寬」這種現實中
   極罕見的輸入下，選擇滿足「不拆字」而允許該行輸出略微超寬，是唯一能同時
   不違反 Scenario 2、又不用引入 spec 未提及的「強制斷字」機制的作法。
   這不是留白的產品決策（spec 兩條驗收條件都聚焦在「中英文混合的一般文字」
   與「換行位置接近邊界的完整單字」，並未描述此極端情境的測資），是演算法
   在合理輸入範圍外的既有行為說明，記錄於此供未來讀者理解，不再列為開放
   設計問題。

6. **統一套用範圍：`_wrap_by_width` 套用在 `_build_pdf` 中所有目前呼叫
   `_line()` 且內容長度可變的位置——摘要、討論重點內容、討論重點**標題**、
   會議資訊四行（日期/時間/地點/參與者）、決定事項每一項（含 `"- "`
   前綴一併量測換行）、待辦事項每一項（含 `"- [負責人] ... （期限：...）"`
   前綴一併量測換行）。標題列（如「會議資訊」「摘要」等固定短字串的區塊
   標題）維持原樣直接 `_line()`，不套用，因為那些是程式碼常數字串，長度
   固定已知不會超寬。**
   理由：spec Scenario 3 明確要求決定/待辦事項「含前綴」的整段文字都要正確
   換行；討論重點**標題**雖然 ticket 描述沒有逐字列出，但它和摘要/內容一樣
   來自 LLM 摘要結果、長度不可控，且現況（第 159 行）與決定/待辦事項一樣是
   直接 `_line()` 無防護——若不一併修正會留下一個和本故事要修的問題同根同
   源的殘留 bug，故依「PDF 每一行文字...渲染寬度皆不超過頁面可用內容寬度」
   這條驗收條件的精神一併套用，屬於實作範圍的一致性判斷，不是新增產品
   行為。前綴（`"- "`、`"[負責人] ... （期限：...）"`）與內容合併成單一
   字串後一起丟進 `_wrap_by_width`，換行後的續行不重複前綴——spec 只要求
   「換行顯示在多行，且每一行渲染寬度皆不超過頁面可用內容寬度」，未規定
   續行是否需要縮排對齊前綴，維持最簡單的實作（不縮排）即可滿足驗收條件。

7. **`_line()` 的分頁（page-break）邏輯完全不動。** `_wrap_by_width` 只負責
   把一段文字切成多個字串，實際輸出仍逐行呼叫既有 `_line()`，其
   `y < 60` 觸發 `c.showPage()` 的既有行為對每一個換行後的短字串一樣適用，
   不需要新邏輯介入或改寫，維持既有 diff 範圍最小化。

參考實作骨架（供 developer 參考，非強制逐字照抄）：

```python
import re

_PAGE_MARGIN_L = 50
_PAGE_MARGIN_R = 50
_CONTENT_WIDTH = A4[0] - _PAGE_MARGIN_L - _PAGE_MARGIN_R

_WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[^A-Za-z0-9]")


def _wrap_by_width(
    text: str, max_width: float = _CONTENT_WIDTH, font: str = _CJK_FONT, size: int = 12
) -> list[str]:
    if not text:
        return [""]
    tokens = _WORD_TOKEN_RE.findall(text)
    lines: list[str] = []
    current = ""
    for tok in tokens:
        candidate = current + tok
        if current and pdfmetrics.stringWidth(candidate, font, size) > max_width:
            lines.append(current)
            current = "" if tok.isspace() else tok
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]
```

呼叫端範例（決定事項，其餘區塊同理套用）：

```python
_line("決定事項", size=14, gap=22)
decisions = minutes.get("decisions", [])
if decisions:
    for d in decisions:
        for chunk in _wrap_by_width(f"- {d}"):
            _line(chunk)
else:
    _line("（無）")
```

`_line()` 內部的 `c.drawString(50, y, text)` 改為
`c.drawString(_PAGE_MARGIN_L, y, text)`（純粹把硬編碼常數換成具名常數，不
改變數值、不改變行為）。

## UI 原型
無，本 Story 不涉及前端 UI 新增或變更：修正範圍完全侷限於伺服器端
`_build_pdf`／`_wrap_by_width` 的 PDF 產生邏輯，不涉及任何前端畫面、元件或
使用者互動。

## 開放設計問題（定稿時必須為空）
無。可用內容寬度（左右邊界各 50pt）、斷詞規則（ASCII 英數字連續片段視為
不可切割 token）、換行演算法（逐 token 累加＋`stringWidth` 量測）、套用
範圍（摘要／討論重點內容與標題／會議資訊／決定事項／待辦事項，含前綴一併
換行、續行不縮排）、單一超寬 token 的邊界行為，均已在本設計中具體決定，
developer 可直接依此實作，不需要再向 spec 或人類確認額外的產品決策。
