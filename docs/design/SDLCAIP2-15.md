# 設計文件 — SDLCAIP2-15 前端會議模板選擇 UI 與匯出格式調整

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-15），並延續 G1 refinement 階段
HUMAN-INPUT 回合（SDLCAIP2-24）確認的 Option C：**不新增「產生前」選模板畫面，
只擴充現有結果畫面**。核心行為：結果畫面新增模板下拉選單（前端內建固定清單，
對應 `src/meeting_templates.py` 5 種模板代碼）；使用者可重新選模板並點擊
「重新產生」以帶入新 `template` 呼叫既有 `/api/summarize`；Word/PDF 匯出
新增「討論重點」區塊，依 `sections` 陣列通用渲染（不因模板而異的程式邏輯）；
前端 3 處 `m.topics` 讀取（`renderMinutes`／`exportMarkdown`／
`exportPlainText`）全面改為 `m.sections`（銜接 SDLCAIP2-16 後端已完成的
`topics`→`sections` 改名）。

範圍外（依 ticket 明列，設計不逾越）：使用者自訂模板 UI、舊會議紀錄模板
回溯套用、新增後端「列出可用模板」API、變更首次自動觸發 `/api/summarize`
的既有時機/流程。

## 介面/API 契約

### 前端 → 後端：沿用既有 `POST /api/summarize`（無新增/變更後端端點）
本故事不新增後端 API。`SummarizeRequest`/`SummarizeResponse` 契約已在
SDLCAIP2-16 定案（見 `docs/design/SDLCAIP2-16.md`），本故事只是前端第二次
（重新產生時）帶入使用者選擇的 `template` 值呼叫同一端點：

```json
// Request
{ "job_id": "string", "template": "retro" }

// Response（節錄，與 SDLCAIP2-16 相同）
{
  "job_id": "string",
  "template": "retro",
  "meeting_info": { ... },
  "summary": "string",
  "action_items": [ ... ],
  "decisions": ["string"],
  "sections": [ { "title": "Keep", "content": "string" } ]
}
```

狀態碼／錯誤情境沿用 SDLCAIP2-16 既有行為，不變更。

### 前端內建模板清單（靜態常數，鏡射 `src/meeting_templates.py`）
```js
const TEMPLATE_OPTIONS = [
  { code: 'general',        name: '一般會議' },
  { code: 'project_status', name: '專案進度會議' },
  { code: 'client_meeting', name: '客戶業務會議' },
  { code: 'brainstorm',     name: '腦力激盪' },
  { code: 'retro',          name: 'Retro' },
];
```
用於填入結果畫面新增的 `<select id="template-select">`；初始選中值＝
`state.minutes.template`（來自 `/api/summarize` 回應，未帶時後端已回填
`"general"`，見 SDLCAIP2-16 決策 #6）。

### 前端內部函式變更（無對外 API，但屬於契約明確化範圍）
- `renderMinutes()`：`(m.topics || [])` → `(m.sections || [])`；另新增：
  結果畫面渲染完成後，將 `#template-select` 的值設為 `m.template`。
- `exportMarkdown()`：`(m.topics || [])` → `(m.sections || [])`。
- `exportPlainText()`：`(m.topics || [])` → `(m.sections || [])`。
- 新增 `regenerateSummary()`：讀取 `#template-select` 目前選中的 `code`，
  以 `POST /api/summarize`（body 帶 `job_id` 與 `template`）重新取得
  `SummarizeResponse`，覆蓋 `state.minutes`，重新呼叫 `renderMinutes()`。
  按鈕文案「🔄 重新產生」，沿用 `doUpload()` 既有的
  disable-during-request 樣式慣例（呼叫期間按鈕文字改為「產生中...」並
  disable，成功/失敗後還原）。

### 後端匯出（`src/export.py`）新增「討論重點」區塊
`_build_docx()` 與 `_build_pdf()` 目前完全沒有 sections/topics 渲染（新增
程式碼，非重構），各自在「待辦事項」之後新增：

```python
doc.add_heading("討論重點", level=2)
sections = minutes.get("sections", [])
if sections:
    for s in sections:
        doc.add_heading(s.get("title", ""), level=3)
        doc.add_paragraph(s.get("content", "") or "（無）")
else:
    doc.add_paragraph("（無）")
```
（PDF 版本以既有 `_line()`/`_wrap()` 輔助函式做等價的逐行輸出。）

**狀態碼**：`GET /api/export/{job_id}` 既有行為不變（404 找不到會議紀錄、
400 未知 format）。

## 資料模型
無新增資料模型。`minutes` JSON blob 的 `sections` 欄位已由 SDLCAIP2-16
定義完成；本故事只是消費既有欄位（前端讀取、後端匯出渲染），未新增/變更
任何欄位、資料表或索引。

## 關鍵技術決策

1. **前端模板下拉選單用寫死的靜態常數陣列，不呼叫後端 API 取得清單。**
   spec 範圍外明列「新增後端列出可用模板 API」；5 種模板代碼在
   `src/meeting_templates.py` 已是固定清單（新增/修改模板本身也不在此
   故事範圍），依 CONSTITUTION「避免不必要的抽象層」，沒有「執行期動態
   模板清單」的需求就不建這層。風險（前後端清單日後不同步）由 spec 的
   範圍界定接受，不在本故事處理。

2. **匯出「討論重點」區塊在 `export.py` 是新增程式碼，通用依 `sections`
   陣列逐一渲染標題＋內容，不依模板代碼做任何 if/switch 分支。** AC2
   明文要求「不因模板不同而需要額外程式邏輯」；固定模板的標題/順序已由
   `_normalize_sections()`（SDLCAIP2-16 決策 #3）在後端鎖定，匯出端只要
   忠實渲染陣列即可，不需要也不應該重複模板邏輯。

3. **新增獨立的 `regenerateSummary()` 函式，不擴充既有 `callStep()`。**
   `callStep()` 目前固定送出 `{job_id}` body，被 `/api/transcribe` 與
   首次 `/api/summarize` 共用；重新產生需要額外帶入 `template` 欄位，若
   直接改 `callStep()` 簽章會牽動所有既有呼叫點，擴大不必要的變更範圍。
   新函式維持改動侷限在本故事新增的行為。

4. **`m.topics` → `m.sections` 只改 3 處資料欄位讀取（spec 明列的
   `renderMinutes`／`exportMarkdown`／`exportPlainText`），DOM 元素
   id／class（`topics-container`、`.topic-item`、`toggleTopic()` 等）
   維持原名不變。** 這些是內部實作細節，非使用者可見文字也非 spec
   要求範圍；沿用 CONSTITUTION「避免不必要的抽象層」／範圍紀律，不做
   spec 未要求的順手重新命名，降低此故事的 diff 範圍與回歸風險。

5. **重新產生按鈕沿用 `doUpload()` 既有的「請求期間 disable + 文案變更」
   互動樣式**，而非額外設計 spinner/modal 等新的前端等待態樣式——延續
   CONSTITUTION「視覺設計」原則：先讀現有慣例延續，不引入新模式除非有
   獨立故事明確要做這個決策。

## 開放設計問題（定稿時必須為空）

1. **「重新產生」呼叫 `/api/summarize` 後，覆蓋範圍是整個
   `state.minutes`（含 `meeting_info`／`summary`／`action_items`／
   `decisions`），還是只覆蓋 `sections`？** AC3 原文只寫「覆蓋原本的
   sections」，但後端 `/api/summarize` 回應是完整物件，若使用者在重新
   產生前已手動編輯過摘要/待辦事項/會議資訊（結果畫面本身支援雙擊編輯），
   兩種實作對使用者體感差異很大（後者會保留使用者手動編輯，前者會被
   LLM 重新產生的內容蓋掉）。這是 spec 未講清楚的產品行為，不可用「合理
   猜測」補上，需要人類決策。
2. **覆蓋 `sections`（或整個 minutes）前是否需要跳出確認提示，警示使用者
   目前對討論重點（或其他欄位，視問題 1 決議）的手動編輯將遺失？** AC3
   未提及任何確認流程，是否需要屬於未定的產品決策。

## 對應摘要
- 檔案：`docs/design/SDLCAIP2-15.md`
- 介面/資料模型：無新增後端端點/資料模型；前端新增模板下拉選單 + 重新產生
  流程（沿用既有 `/api/summarize`），`export.py` 新增通用 sections 渲染。
- 開放問題：2 項（重新產生的覆蓋範圍；是否需要覆蓋前確認提示）。
