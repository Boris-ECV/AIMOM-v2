# 設計文件 — SDLCAIP2-39 會議紀錄結果頁操作按鈕排列在特定寬度下會換行，且部分按鈕圖示與文字混雜

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-39）：`#view-result` 操作區塊（
`#result-action-group-content`／`#result-action-group-reset`，SDLCAIP2-37
建立）在特定寬度下換行排列不可預期，且 `#regenerate-btn`／
`#export-confirm-btn`／`#cleanup-btn` 文字含 emoji 圖示。五條 Gherkin
AC：AC1 寬螢幕（1280px）操作列不換行；AC2 窄螢幕（480px）仍不換行、外層
容器可水平捲動；AC3 `result-action-group-reset` 靠右、
`result-action-group-content` 靠左且相對順序不變；AC4 三顆按鈕文字移除
emoji 前綴；AC5 既有 `regenerateSummary()`／`exportSelectedFormat()`／
`cleanupAndReset()` 行為與呼叫參數不變。純 HTML/CSS 修正，決策已在 ticket
定案為「不換行 + 水平捲動 fallback」，不新增 CSS class、不加 media query。

## 介面/API 契約
無對外 HTTP API 變更。契約範圍限定在 `src/frontend/index.html` 中
`#view-result` 操作列相關元素的既有 inline style 與按鈕文字內容。

### 現況（`src/frontend/index.html`，實際行號，較 ticket 描述的「~293」略有偏移）
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
CSS（第 70 行，`.btn-row` 共用規則，全站多處 `.btn-row` 沿用）：
```css
.btn-row { display: flex; gap: 10px; flex-wrap: wrap; }
```

實際 DOM 比 ticket root-cause 描述多一層：第 293 行是「標題（h2/meta）＋操
作列」的最外層 flex 容器（不是 `.btn-row`，僅 inline `flex-wrap:wrap`），
第 298 行才是**操作列本身**的直接容器——本身也是 `.btn-row`（沿用共用
class），內含 `result-action-group-content`（299 行）與
`result-action-group-reset`（316 行）兩個子分組，靠第 298 行的
`justify-content:space-between` 做左右分佈。AC1-AC3 描述的「操作列所有元
素同一列」，指的是第 298／299／316 這三層，第 293 行（標題列）不在操作
列範圍內、不動。

### 變更後
只修改 inline style 與按鈕文字，**不修改第 70 行共用 `.btn-row` 規則**
（該規則被全站其他 `.btn-row` 使用，例如上傳頁等，若直接改共用規則的
`flex-wrap`／新增 `overflow-x`，會把本 ticket 範圍外的區塊一併改變，違
反「僅限 `#view-result` 操作列」的範圍限制）。三處各自的 inline style 疊
加覆寫該 class 的 `flex-wrap:wrap`：

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
1. 第 298 行（操作列外層容器）：inline style 新增
   `flex-wrap:nowrap;overflow-x:auto;`（AC1、AC2）。
2. 第 299 行 `#result-action-group-content`：inline style 新增
   `flex-wrap:nowrap;`（AC1、AC3，維持內部元素原相對順序不變）。
3. 第 316 行 `#result-action-group-reset`：inline style 新增
   `flex-wrap:nowrap;`（AC1、AC3）；本身已因第 298 行的
   `justify-content:space-between` 靠右對齊，不需額外調整。
4. `#regenerate-btn`／`#export-confirm-btn`／`#cleanup-btn`：文字分別由
   `🔄 重新產生`／`⬇ 匯出`／`🗑 清除暫存` 改為 `重新產生`／`匯出`／
   `清除暫存`（AC4）。`#new-recording-btn` 的 `+ 新錄音` 前綴不動（範圍
   排除項明示）。
5. `class`、`id`、`onclick`、按鈕/元素數量與順序皆不變（AC5）。

### 狀態碼
不涉及。純前端視覺/標記變更，AC5 明確要求
`regenerateSummary()`／`exportSelectedFormat()`／`cleanupAndReset()` 的
JS 邏輯與呼叫參數不變，本設計未觸碰任何 `<script>` 區塊。

## 資料模型
無新增/變更資料模型。

## 關鍵技術決策

1. **用 inline style 疊加覆寫 `flex-wrap`/新增 `overflow-x`，不修改第 70
   行共用 `.btn-row` 規則、不新增專屬 CSS class。** `.btn-row` 是全站共
   用 class（其他頁面的按鈕列也用它），直接改共用規則會讓效果外溢到
   ticket 範圍外的區塊；沿用 SDLCAIP2-36/37 已建立的慣例（一次性容器排
   版用 inline style，不為單一場景新增等價 class），影響面最小且與既有
   慣例一致。

2. **水平捲動只加在第 298 行（操作列最外層容器），兩個子分組
   （299／316）只設 `nowrap` 不重複加 `overflow-x`。** AC2 只要求「外層
   容器可水平捲動」，捲動軸只需要一層；子分組本身寬度由內容決定，nowrap
   後會撐開，捲動交給唯一的外層容器處理即可，避免巢狀捲動容器互相干擾。

3. **第 293 行（標題列，`h2`＋操作列的最外層 flex 容器）維持原樣，不
   動。** Ticket 的 AC1-AC3 描述的「操作列元素同一列」指操作列內部
   （298/299/316 三層），不含標題；範圍限定「僅限 `#view-result` 操作
   列」，標題與操作列之間如何排列是既有行為，不在本次 AC 驗收範圍內，
   改動它會超出範圍。

4. **不新增 media query、不做 <375px 專屬版面，水平捲動 fallback 統一涵
   蓋所有寬度。** 這是 ticket 已定案的產品決策（見「已做的決定」段落），
   直接依規格實作，不再另行設計斷點。

## 開放設計問題（定稿時必須為空）
無。實際程式碼結構（三層 flex 容器：298 外層／299 與 316 子分組）已與
ticket 描述的 root cause 對應清楚，僅行號有 ~5 行偏移（ticket 寫
「line ~293」，實際操作列外層容器在第 298 行；已在上方現況/決策 3 中說
明並修正）。CSS 覆寫方式、捲動範圍、emoji 移除皆可直接從 AC 與既有慣例
（SDLCAIP2-36/37 的 inline-style 慣例）推定，未發現規格未決的產品決策。
