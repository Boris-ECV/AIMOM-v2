# 設計文件 — SDLCAIP2-35 匯出功能的四種格式應整合為單一選單

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-35）：目前結果畫面（`view-result`）有 4
個獨立的匯出按鈕（Markdown／純文字／Word／PDF），應整合為「單一下拉選單 +
一個確認按鈕」的操作方式，UI 慣例比照 SDLCAIP2-15 已導入的
`template-select` 下拉選單 + 確認按鈕（`regenerate-btn`）模式。僅改變
「使用者如何選擇要匯出哪一種格式」的操作介面，**不變更**任一匯出格式
背後的既有函式邏輯（`exportMarkdown()`／`exportPlainText()`／
`exportServerFile('docx')`／`exportServerFile('pdf')` 內部實作原封不動）。
歷史紀錄詳情頁（SDLCAIP2-32／`view-history-detail`）目前沒有任何匯出功能，
明列範圍外，本設計不觸碰該頁面。純前端改動，無新增/變更後端 API。

## 介面/API 契約

本故事不涉及對外 HTTP API（無新增/變更後端端點），契約範圍限定在前端
DOM 結構與既有 JS 函式的呼叫方式。

### 現況（`src/frontend/index.html` 第 296–299 行）
```html
<button class="btn btn-success btn-sm" onclick="exportMarkdown()">⬇ 匯出 Markdown</button>
<button class="btn btn-success btn-sm" onclick="exportPlainText()">⬇ 匯出純文字</button>
<button class="btn btn-success btn-sm" onclick="exportServerFile('docx')">⬇ 匯出 Word</button>
<button class="btn btn-success btn-sm" onclick="exportServerFile('pdf')">⬇ 匯出 PDF</button>
```

### 變更後
比照第 292–294 行既有的 `template-select` 標籤+下拉選單寫法，將上述 4 個
按鈕替換為 1 個 `<select>` + 1 個確認 `<button>`：

```html
<label style="font-size:.8rem;color:var(--muted);">匯出格式
  <select id="export-format-select">
    <option value="markdown">Markdown</option>
    <option value="plaintext">純文字</option>
    <option value="docx">Word</option>
    <option value="pdf">PDF</option>
  </select>
</label>
<button class="btn btn-success btn-sm" id="export-confirm-btn" onclick="exportSelectedFormat()">⬇ 匯出</button>
```

放置位置：取代原第 296–299 行 4 個 `<button>`，插入位置維持在
`#regenerate-btn` 之後、`cleanupAndReset` 按鈕之前（與原 4 按鈕群組相同的
`.btn-row` 內順序區段）。預設選中值＝`markdown`（`<select>` 第一個
`<option>`，對應原本 4 按鈕由左到右的第一個，即 Markdown）。

### 新增的前端函式：`exportSelectedFormat()`
```js
function exportSelectedFormat() {
  const format = document.getElementById('export-format-select').value;
  switch (format) {
    case 'markdown':  exportMarkdown(); break;
    case 'plaintext': exportPlainText(); break;
    case 'docx':      exportServerFile('docx'); break;
    case 'pdf':       exportServerFile('pdf'); break;
  }
}
```
此函式是唯一新增的程式碼；`exportMarkdown()`、`exportPlainText()`、
`exportServerFile(format)` 三個既有函式簽章與內部邏輯完全不變，只是改由
`exportSelectedFormat()` 依下拉選單當下的值分派呼叫，取代原本個別按鈕的
`onclick` 直接呼叫。

### 狀態碼
不變。`exportServerFile()` 呼叫的 `GET /api/export/{job_id}?format=...`
既有行為（404/500 等）未受影響。

## 資料模型
無新增資料模型。本故事純粹是前端 UI 標記（markup）與一個新增的分派函式，
不涉及任何資料表、欄位或索引變更。

## 關鍵技術決策

1. **新增獨立的 `exportSelectedFormat()` 分派函式，而非直接把 4 個既有
   函式其中之一綁在確認按鈕上。** Ticket 明確要求「使用者選格式、按確認
   才觸發」的單一選單模式，需要一個依 `<select>` 當前值決定呼叫哪個既有
   函式的中介層；比照 CONSTITUTION「避免不必要的抽象層」，這裡不是可省略
   的抽象——沒有它就無法用同一顆按鈕分派到 4 種既有邏輯。

2. **`<select id="export-format-select">` 的 4 個 `<option>` 命名（`markdown`
   /`plaintext`/`docx`/`pdf`）沿用 `exportServerFile(format)` 既有第一參數
   慣用字串（`'docx'`/`'pdf'`），前兩者為新引入但採一致的全小寫英文簡稱風
   格。** 因為這是純前端內部 value，不對外，沿用既有程式碼已用過的字串
   降低新讀者需要記憶的命名數量。

3. **UI 結構與樣式（`<label>` + `<select>` 外層包裝、按鈕沿用 `.btn
   .btn-success .btn-sm` class）逐字比照 SDLCAIP2-15 引入的
   `template-select` + `regenerate-btn` pattern。** Ticket 明文要求「與
   template-select 相同的下拉選單 + 確認按鈕慣例」；依 CONSTITUTION
   「視覺設計」原則——先讀現有慣例延續，不引入新前端模式——不新增任何
   額外的視覺樣式或元件。

4. **`exportMarkdown()`／`exportPlainText()`／`exportServerFile()` 三個既有
   函式的函式簽章與函式體完全不改動，只改變呼叫來源。** Ticket 明確排除
   「變更匯出格式背後的邏輯」，依 CONSTITUTION「範圍紀律」，只做 spec
   要求的「整合選單操作介面」，不順手重構既有匯出邏輯。

5. **不觸碰 `view-history-detail`（SDLCAIP2-32 歷史紀錄詳情頁）。** 該頁面
   目前無任何匯出按鈕或匯出邏輯，ticket 明列為範圍外；依 CONSTITUTION
   「範圍紀律」，看得到但未被要求的功能（例如「順便」替歷史詳情頁也加上
   匯出選單）不在本故事實作。

## 開放設計問題（定稿時必須為空）
無。UI 結構、命名、預設選中值、範圍邊界均可由 ticket 描述與既有
`template-select`/`regenerate-btn` 慣例直接推定，未發現規格未決的產品
決策。
