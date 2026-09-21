# 設計文件 — SDLCAIP2-41 頁首標題應移除麥克風圖示，並維持點擊可回到首頁

## 對應需求規格
G1 已核准的 SDLCAIP2-41 規格。兩條 Gherkin AC：
1. 頁首左上角標題「會議錄音轉紀錄系統」左側不應顯示麥克風圖示（不應存在
   該 `<svg>` 元素）。
2. 使用者位於任一非首頁畫面時，點擊頁首標題文字，畫面應切換回首頁
   （`view-upload`）。
範圍外：頁首其他元件（管理者儀表板按鈕、歷史紀錄按鈕、email、登出按鈕）
樣式行為不變；auth-gate 標題列的 🔐 emoji 不受影響（那是文字字元，非
`<svg>`，且屬於不同的 `#auth-gate` 區塊）；不新增瀏覽器路由，僅切換既有
的前端內部 view 狀態。

Ground truth（`src/frontend/index.html`）：
- 第 199-207 行：`<header>` 區塊，第 200 行為麥克風 `<svg>`，第 201 行為
  `<h1>會議錄音轉紀錄系統</h1>`。
- 第 1494-1497 行附近：既有 `function showView(id) { ... }` view 切換
  helper，各處既有導覽按鈕（例如第 213 行「← 返回」）已用
  `onclick="showView('view-upload')"` 這個既有慣例呼叫它。
- 第 229 行：`<div id="view-upload" class="view active">` 為首頁/上傳
  view，即點擊標題後應切換到的目標。
- 第 26-29 行：`header`／`header h1`／`header span` 既有 CSS 規則。

## 介面/API 契約
無。本 story 純屬前端靜態頁面（`src/frontend/index.html`）的 DOM 結構與
inline `onclick` 行為調整，不涉及任何後端 HTTP 端點、request/response
格式或狀態碼變更。

## 資料模型
無新增資料模型。本 story 不觸碰任何資料表、欄位或索引。

## 關鍵技術決策

1. **移除 `<svg>` 元素本身，而非用 CSS 隱藏（`display:none`）。**
   AC1 文字明確要求「不應存在該 svg 元素」，而非「不可見」；直接刪除第
   200 行整個 `<svg>...</svg>` 區塊，既滿足字面驗收條件（DOM 查詢不到該
   元素），也比留著一段永遠不顯示的死程式碼更簡潔，符合
   `CONSTITUTION.md`「避免不必要的抽象層／不留無用程式碼」的既有慣例
   （視覺設計章節：延續既有排版慣例，不引入多餘複雜度）。

2. **點擊行為沿用既有 `showView('view-upload')` helper，不新增任何 JS
   函式。** 頁首其他導覽按鈕（如第 213 行「← 返回」）已用這個既有 pattern
   呼叫同一個 helper 回到首頁；`<h1>` 直接加上
   `onclick="showView('view-upload')"` 與 `style="cursor:pointer;"`
   （或等效 class）即可達成 AC2，不需要另外寫路由或新的狀態管理邏輯，維持
   `CONSTITUTION.md`「遵循既有程式庫中已建立的慣例優先於個人偏好」原則。

3. **`cursor:pointer` 直接加在 `<h1>` 的 inline style，不新增獨立
   CSS class。** 這個視覺提示只在這一個元素上使用，且 `index.html` 目前
   對單一元素的行為性樣式（例如 `#drop-zone`、既有按鈕的 `onclick`）普遍
   採 inline style／既有 class 混用的既有形狀，新增一個只用一次的 class
   不划算；若未來有更多「可點擊回首頁」的類似元素出現，再抽成共用 class
   不遲（`CONSTITUTION.md`「避免不必要的抽象層」）。

4. **不動 auth-gate（第 189-196 行）的 🔐。** 範圍外明確排除，且該
   🔐 是文字 emoji 字元（`<h2>🔐 會議錄音轉紀錄系統</h2>`），不是 AC1
   指涉的 `<svg>` 元素，兩者本就是不同區塊、不同標記，不需要額外處理即
   可自然滿足「不更動」的範圍外聲明。

## UI 原型
見 `docs/design/SDLCAIP2-41-prototype.html`，可直接在瀏覽器開啟查看：
- 頁首標題左側已移除麥克風圖示（只保留「會議錄音轉紀錄系統」文字與副標
  「Meeting Minutes AI」，其餘按鈕/email/登出保持原樣版面，作為視覺對照）。
- 標題文字加上 `cursor:pointer` 視覺提示，並在原型頁面下方以文字說明點擊
  行為：點擊標題會呼叫既有 `showView('view-upload')` 切換回首頁 view（靜
  態原型無法示範真實的多 view 切換，故以行內註解/說明文字表示這個行為，
  實際切換效果由 developer 在 `index.html` 正式頁面中對照既有
  `showView()` 實作驗證）。

## 開放設計問題（定稿時必須為空）
無。兩條 AC 與範圍外聲明均可直接對照既有程式碼（`<svg>` 位置、
`showView()` helper、`view-upload` 目標 id）逐字落實，沒有規格未講清楚、
需要人類額外裁決的產品決策。
