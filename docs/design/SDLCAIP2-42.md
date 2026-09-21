# 設計文件 — SDLCAIP2-42 會議紀錄結果頁操作區塊排列應維持同排且靠右對齊，並移除三顆按鈕圖示

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-42）：`#view-result` 操作列（模板／重新
產生／匯出格式／匯出／清除暫存／新錄音）在任何視窗寬度下都必須同排不換
行，「清除暫存」「新錄音」靠右對齊，且 `#regenerate-btn`／
`#export-confirm-btn`／`#cleanup-btn` 三顆按鈕文字移除 emoji 圖示前綴（
`#new-recording-btn` 的 `+ 新錄音` 不動）。五條 Gherkin AC：AC1 寬螢幕
（1280px）操作列不換行、相對順序不變；AC2 窄螢幕（480px）仍不換行，允許
水平捲動；AC3 清除暫存／新錄音靠右、模板到匯出靠左；AC4 三顆按鈕文字移
除 emoji；AC5（回歸）`regenerateSummary()`／`exportSelectedFormat()`／
`cleanupAndReset()`／`showView('view-upload')` 呼叫參數不變，id／class／
onclick／元素數量與順序不變，僅 inline style 與三顆按鈕文字改變。範圍
外：標題列排版、全站共用 `.btn-row` class 定義本身、新錄音 `+` 前綴、任
何 JS 邏輯/函式簽章。

## 目前程式碼狀態（重要前置事實）
`src/frontend/index.html` 目前的 `#view-result` 操作列（第 291-320
行）與 SDLCAIP2-40 revert 後的狀態一致——也就是說，**目前程式碼與
SDLCAIP2-39 合併前的原始狀態相同**：三層 `.btn-row` 容器皆無 inline
`flex-wrap:nowrap`／`overflow-x:auto`，三顆按鈕文字仍帶 emoji（`🔄 重新
產生`／`⬇ 匯出`／`🗑 清除暫存`）。SDLCAIP2-39 曾用完全相同的技術手段達
成幾乎相同的排版目標，其 squash-merge commit `9b9d4e4` 後因「產品偏好」
（非技術缺陷）被 SDLCAIP2-40 revert。本次 ticket 明確要求 requirements-
analyst 交由 architect 決定手法，並在規格中建議沿用 `9b9d4e4` 的技術路
線——見下方「關鍵技術決策」第 1 點的取捨。

## 介面/API 契約
無對外 HTTP API 變更。契約範圍限定在 `src/frontend/index.html` 中
`#view-result` 操作列既有元素的 inline style 與三顆按鈕的顯示文字內容。

### 現況（第 291-320 行，逐行同上方 Read 結果）
```html
291   <!-- ============ RESULT VIEW ============ -->
292   <div id="view-result" class="view">
293     <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px;">
294       <div>
295         <h2 style="font-size:1.2rem;">📋 會議紀錄</h2>
296         <p id="result-meta" ...></p>
297       </div>
298       <div class="btn-row" style="align-items:center;justify-content:space-between;flex:1;">
299         <div class="btn-row" id="result-action-group-content" style="align-items:center;">
300           <span id="modified-badge">...</span>
301           <span id="low-confidence-badge">...</span>
302           <label>模板 <select id="template-select"></select></label>
305           <button class="btn btn-outline btn-sm" id="regenerate-btn" onclick="regenerateSummary()">🔄 重新產生</button>
306           <label>匯出格式 <select id="export-format-select">...</select></label>
314           <button class="btn btn-outline btn-sm" id="export-confirm-btn" onclick="exportSelectedFormat()">⬇ 匯出</button>
315       </div>
316       <div class="btn-row" id="result-action-group-reset" style="align-items:center;">
317         <button class="btn btn-outline btn-sm" id="cleanup-btn" onclick="cleanupAndReset()">🗑 清除暫存</button>
318         <button class="btn btn-outline btn-sm" id="new-recording-btn" onclick="showView('view-upload')">+ 新錄音</button>
319       </div>
320     </div>
321   </div>
```
CSS（第 70 行，全站共用 `.btn-row` 規則，本 story 不可修改）：
```css
.btn-row { display: flex; gap: 10px; flex-wrap: wrap; }
```

### 變更後
只改三處 inline style（疊加覆寫共用 class 的 `flex-wrap:wrap`）與三顆按
鈕文字，其餘 id／class／onclick／元素數量與順序不變：

```html
298   <div class="btn-row" style="align-items:center;justify-content:space-between;flex:1;flex-wrap:nowrap;overflow-x:auto;">
299     <div class="btn-row" id="result-action-group-content" style="align-items:center;flex-wrap:nowrap;">
        ...
305       <button class="btn btn-outline btn-sm" id="regenerate-btn" onclick="regenerateSummary()">重新產生</button>
        ...
314       <button class="btn btn-outline btn-sm" id="export-confirm-btn" onclick="exportSelectedFormat()">匯出</button>
315   </div>
316   <div class="btn-row" id="result-action-group-reset" style="align-items:center;flex-wrap:nowrap;">
317     <button class="btn btn-outline btn-sm" id="cleanup-btn" onclick="cleanupAndReset()">清除暫存</button>
318     <button class="btn btn-outline btn-sm" id="new-recording-btn" onclick="showView('view-upload')">+ 新錄音</button>
319   </div>
```

具體變更點：
1. 第 298 行（操作列外層容器，本身也是 `.btn-row`）：inline style 新增
   `flex-wrap:nowrap;overflow-x:auto;`（AC1、AC2）。既有
   `justify-content:space-between` 已使
   `result-action-group-content`（左）與 `result-action-group-reset`
   （右）左右分佈，加上 `nowrap` 後即滿足 AC3「清除暫存／新錄音靠右、
   模板到匯出靠左」，不需額外新增 `margin-left:auto` 等寫法。
2. 第 299 行 `#result-action-group-content`：inline style 新增
   `flex-wrap:nowrap;`（AC1、AC3，維持內部元素原相對順序不變）。
3. 第 316 行 `#result-action-group-reset`：inline style 新增
   `flex-wrap:nowrap;`（AC1、AC3）。
4. `#regenerate-btn`／`#export-confirm-btn`／`#cleanup-btn` 文字：分別
   由 `🔄 重新產生`／`⬇ 匯出`／`🗑 清除暫存` 改為 `重新產生`／`匯出`／
   `清除暫存`（AC4）。`#new-recording-btn` 的 `+ 新錄音` 前綴不動（範圍
   排除項明示）。
5. `class`、`id`、`onclick`、元素數量與順序全部不變（AC5）；
   `<script>` 區塊完全不動，`regenerateSummary()`／
   `exportSelectedFormat()`／`cleanupAndReset()`／
   `showView('view-upload')` 呼叫參數不受影響。
6. 第 293 行（標題列，`h2`＋操作列的最外層 flex 容器）與第 70 行共用
   `.btn-row` class 規則本身皆維持原樣，不動（範圍外明示）。

### 狀態碼
不涉及。純前端視覺/標記變更。

## 資料模型
無新增資料模型。

## 關鍵技術決策

1. **沿用 SDLCAIP2-39（commit `9b9d4e4`）已驗證過的技術手段：三層
   `.btn-row` 容器各自疊加 inline `flex-wrap:nowrap`，外層另加
   `overflow-x:auto` 作為窄螢幕 fallback；不修改第 70 行共用 `.btn-row`
   class、不新增專屬 CSS class、不加 media query。** 理由：(a)
   `9b9d4e4` 被 SDLCAIP2-40 revert 的原因是「產品偏好」而非技術缺陷（見
   SDLCAIP2-40 設計文件），本 ticket 的 AC1-AC4 與 SDLCAIP2-39 的
   AC1-AC4 在排版/文字要求上實質相同，沒有理由改用不同手法；(b) 延續
   SDLCAIP2-36/37 已建立的慣例（一次性容器排版用 inline style，不為單一
   場景新增等價 class），避免共用 `.btn-row` 規則外溢影響本 ticket 範圍
   外的其他頁面區塊；(c) requirements-analyst 在規格中已將此列為非約束
   性建議，交由 architect 定案——本設計採納該建議。
2. **不直接 cherry-pick/revert-the-revert `9b9d4e4`，改以本設計文件描述
   的目標狀態由 developer 依現況手動套用等效 diff。** 因為 SDLCAIP2-40
   之後 `index.html` 可能已有其他不相關行號偏移的既有變更風險需要
   developer 依「現況」核對而非盲套歷史 commit；且與 SDLCAIP2-40（其實
   作方式受人類硬性裁決限定為 revert）不同，本 ticket 的規格與開放問題
   段落並未鎖定「必須用 git 特定操作」這個限制，故技術路線交由
   architect／developer 依現況實作最直接、風險最低。
3. **水平捲動只加在第 298 行（操作列最外層容器），兩個子分組
   （299／316）只設 `nowrap` 不重複加 `overflow-x`。** AC2 只要求「模板
   到匯出」與「清除暫存、新錄音」整體維持同一列、可水平捲動，捲動軸只
   需一層；避免巢狀捲動容器互相干擾。
4. **不新增 media query、不做窄螢幕專屬版面。** Ticket 範圍外已明示「是
   否需要 media query 由 architect 決定；若無特別需要，預設不新增」，
   水平捲動 fallback 已足以滿足 AC2 的「不整排換行」要求，不需額外斷點。

## UI 原型
`docs/design/SDLCAIP2-42-prototype.html`：靜態、可直接用瀏覽器開啟的原
型，重現變更後的 `#view-result` 操作列（同排、`nowrap`、右側
`overflow-x:auto` fallback、三顆按鈕純文字、`+ 新錄音` 不變）。檔案內同
時提供「寬版（1280px 容器）」與「窄版（480px 容器，模擬窄螢幕）」兩組並
排展示，兩者共用同一套 inline style，不需另外調整瀏覽器視窗即可比較兩種
寬度下的呈現結果；註解中說明如何另外用瀏覽器 DevTools 縮放視窗做進一步
驗證。不含任何後端呼叫、不含 JS 邏輯（按鈕僅為靜態展示，`onclick` 保留
文字但不綁定真實函式，避免原型檔案被誤用於功能驗證）。

## 開放設計問題（定稿時必須為空）
無。現況程式碼（第 291-320 行）與 SDLCAIP2-39 合併前狀態一致，目標狀態
與變更手法皆可從 ticket 的五條 AC、範圍外聲明與 SDLCAIP2-39/40 既有設計
文件直接推定，未發現規格未決的產品決策。
