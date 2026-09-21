# 設計文件 — SDLCAIP2-42 會議紀錄結果頁操作區塊排列應維持同排且靠右對齊，並移除三顆按鈕圖示

> **此為 G1b 駁回後修訂版。** 前一版設計沿用 SDLCAIP2-39 的技術手段（三層
> `.btn-row` 容器疊加 inline `flex-wrap:nowrap` + 外層 `overflow-x:auto`
> 水平捲動 fallback），套用在「標題＋操作列同排」的既有結構上。人類原文駁
> 回意見：「不准採用 SDLCAIP2-39 的排版方案，該方案就是設計太拙劣才被
> revert」、「不准採用橫向捲動這種違反使用習慣的方案」，並提出明確替代需
> 求（逐字翻譯如下）：
> ```
> 需求很簡單:
> "會議記錄" 字樣是一行
> job id: XXX  字樣是一行
> 操作列（模板／重新產生／匯出格式／匯出／清除暫存／新錄音）是一行
> -模板／重新產生／匯出格式／匯出 維持原樣靠左
> -「清除暫存」「新錄音」兩者並排靠右對齊
>
> 「重新產生」「匯出」「清除暫存」三顆按鈕只顯示文字
> ```
> 本修訂版完全依此重新設計：改為「標題列 / meta 列 / 操作列」三個獨立堆疊
> 區塊（非同一橫向 flex row），操作列本身**不使用**水平捲動；若窄寬度下仍
> 需要換行，改用 `flex-wrap:wrap` 的自然換行（class `.btn-row` 既有預設行
> 為即是如此，見下方關鍵技術決策第 2 點），不新增 `overflow-x:auto`。

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-42）：`#view-result` 操作列（模板／重新
產生／匯出格式／匯出／清除暫存／新錄音）在任何視窗寬度下都必須不與標題
列擠在同一橫排、維持清晰可讀，「清除暫存」「新錄音」靠右對齊，且
`#regenerate-btn`／`#export-confirm-btn`／`#cleanup-btn` 三顆按鈕文字移除
emoji 圖示前綴（`#new-recording-btn` 的 `+ 新錄音` 不動）。五條 Gherkin
AC（原始規格文字不變，僅實作手法因 G1b 駁回重新設計）：AC1 寬螢幕
（1280px）操作列不換行、相對順序不變；AC2 窄螢幕（480px）操作列維持可讀
排版，若換行僅允許自然換行（`flex-wrap:wrap`），**不得使用橫向捲動**；
AC3 清除暫存／新錄音靠右、模板到匯出靠左；AC4 三顆按鈕文字移除 emoji；
AC5（回歸）`regenerateSummary()`／`exportSelectedFormat()`／
`cleanupAndReset()`／`showView('view-upload')` 呼叫參數不變，id／class／
onclick／元素數量與順序不變，僅版面結構（標題/meta/操作列由同排改堆疊）
與三顆按鈕文字改變。範圍外：全站共用 `.btn-row` class 定義本身、新錄音
`+` 前綴、任何 JS 邏輯/函式簽章、`src/export.py`、字型檔。

## 目前程式碼狀態（重要前置事實）
`src/frontend/index.html` 目前的 `#view-result` 操作列（第 291-322
行，已重新核對行號，與駁回前版本一致）與 SDLCAIP2-40 revert 後的狀態一
致——三層 `.btn-row` 容器皆無 inline `flex-wrap:nowrap`／
`overflow-x:auto`，三顆按鈕文字仍帶 emoji（`🔄 重新產生`／`⬇ 匯出`／
`🗑 清除暫存`）。**與駁回前版本不同的關鍵事實**：目前標題（`h2`＋
`#result-meta`）與操作列（模板…新錄音）共用同一個最外層 flex 容器（第
293 行 `display:flex;justify-content:space-between;...`），標題在左、操
作列在右、同一橫排。這正是本次需要打破的結構——SDLCAIP2-39/40 兩份既有
設計文件描述的「操作列換行問題」都是在標題與操作列共擠一排、可用寬度被
標題吃掉的前提下發生；本次改為三行堆疊後，操作列有全版面寬度可用，本質
上大幅降低換行風險，不需要 SDLCAIP2-39 那種捲動手段。

## 介面/API 契約
無對外 HTTP API 變更。契約範圍限定在 `src/frontend/index.html` 中
`#view-result` 標題/meta/操作列的 DOM 結構、inline style 與三顆按鈕的顯示
文字內容。

### 現況（第 291-322 行，逐行同上方 Read 結果）
```html
291   <!-- ============ RESULT VIEW ============ -->
292   <div id="view-result" class="view">
293     <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px;">
294       <div>
295         <h2 style="font-size:1.2rem;">📋 會議紀錄</h2>
296         <p id="result-meta" style="color:var(--muted);font-size:.8rem;margin-top:4px;"></p>
297       </div>
298       <div class="btn-row" style="align-items:center;justify-content:space-between;flex:1;">
299         <div class="btn-row" id="result-action-group-content" style="align-items:center;">
300           <span id="modified-badge">● 未儲存修改</span>
301           <span id="low-confidence-badge">⚠ 偵測到的語言信心水準較低，逐字稿可能不夠準確</span>
302           <label style="font-size:.8rem;color:var(--muted);">模板
303             <select id="template-select"></select>
304           </label>
305           <button class="btn btn-outline btn-sm" id="regenerate-btn" onclick="regenerateSummary()">🔄 重新產生</button>
306           <label style="font-size:.8rem;color:var(--muted);">匯出格式
307             <select id="export-format-select">...</select>
308           </label>
314           <button class="btn btn-outline btn-sm" id="export-confirm-btn" onclick="exportSelectedFormat()">⬇ 匯出</button>
315         </div>
316         <div class="btn-row" id="result-action-group-reset" style="align-items:center;">
317           <button class="btn btn-outline btn-sm" id="cleanup-btn" onclick="cleanupAndReset()">🗑 清除暫存</button>
318           <button class="btn btn-outline btn-sm" id="new-recording-btn" onclick="showView('view-upload')">+ 新錄音</button>
319         </div>
320       </div>
321     </div>
322   </div>
```
CSS（第 70 行，全站共用 `.btn-row` 規則，本 story 不可修改）：
```css
.btn-row { display: flex; gap: 10px; flex-wrap: wrap; }
```

### 變更後
拆解第 293 行「標題＋操作列同排」的最外層 flex 容器，改為三個獨立、垂直
堆疊的區塊：標題（`h2`）、meta（`#result-meta`）、操作列（原第 298-319
行結構，內部左右兩組不動）。三顆按鈕文字移除 emoji。`class`／`id`／
`onclick`／元素數量與相對順序全部不變。

```html
291   <!-- ============ RESULT VIEW ============ -->
292   <div id="view-result" class="view">
293     <h2 style="font-size:1.2rem;margin-bottom:4px;">📋 會議紀錄</h2>
294     <p id="result-meta" style="color:var(--muted);font-size:.8rem;margin-bottom:16px;"></p>
295     <div class="btn-row" style="align-items:center;justify-content:space-between;margin-bottom:20px;">
296       <div class="btn-row" id="result-action-group-content" style="align-items:center;">
297         <span id="modified-badge">● 未儲存修改</span>
298         <span id="low-confidence-badge">⚠ 偵測到的語言信心水準較低，逐字稿可能不夠準確</span>
299         <label style="font-size:.8rem;color:var(--muted);">模板
300           <select id="template-select"></select>
301         </label>
302         <button class="btn btn-outline btn-sm" id="regenerate-btn" onclick="regenerateSummary()">重新產生</button>
303         <label style="font-size:.8rem;color:var(--muted);">匯出格式
304           <select id="export-format-select">...</select>
305         </label>
306         <button class="btn btn-outline btn-sm" id="export-confirm-btn" onclick="exportSelectedFormat()">匯出</button>
307       </div>
308       <div class="btn-row" id="result-action-group-reset" style="align-items:center;">
309         <button class="btn btn-outline btn-sm" id="cleanup-btn" onclick="cleanupAndReset()">清除暫存</button>
310         <button class="btn btn-outline btn-sm" id="new-recording-btn" onclick="showView('view-upload')">+ 新錄音</button>
311       </div>
312     </div>
313   </div>
```

具體變更點：
1. **刪除第 293 行的最外層 flex 容器與第 294/297 行包住 `h2`／
   `#result-meta` 的 wrapper `<div>`。** 標題與 meta 不再與操作列同排；
   改為 `h2`、`#result-meta` 兩個各自獨立的 block-level 元素依序排列
   （第 1 行「會議紀錄」、第 2 行 job id/meta），`h2` 加
   `margin-bottom:4px`、`#result-meta` 加 `margin-bottom:16px` 取代原本
   靠 `gap:10px`/`margin-bottom:20px` 做的間距（AC1、AC2，對應人類需求
   「'會議記錄' 字樣是一行、job id: XXX 字樣是一行」）。`h2` 文字
   `📋 會議紀錄` 與 `#result-meta` 的 id、內容產生邏輯完全不動（範圍外，
   ticket 未要求改標題文字）。
2. **原第 298 行操作列外層容器（`.btn-row`）不再是誰的 flex 子項，改為
   `#view-result` 底下第三個獨立 block（第 295 行）。** 移除已無意義的
   `flex:1`（該屬性只在父層為 flex container 時才有作用，父層改為
   `#view-result`〈`class="view"`，非 flex〉後 `flex:1` 不再有效，故一併
   移除，避免死屬性造成閱讀混淆）；新增 `margin-bottom:20px` 取代原本由
   父層 293 行提供的間距。`justify-content:space-between`／
   `align-items:center` 不動——這正是目前就已經在用、能讓
   `result-action-group-content`（左）與 `result-action-group-reset`
   （右）左右分佈的既有寫法，對應人類需求「模板／重新產生／匯出格式／
   匯出 維持原樣靠左」「清除暫存／新錄音 兩者並排靠右對齊」（AC3）——這部
   分**維持原樣**，不需要任何新增/修改。
3. **不新增 `flex-wrap:nowrap`、不新增 `overflow-x:auto`。** 三層
   `.btn-row` 容器（第 295／296／308 行）皆不覆寫共用 class 第 70 行的
   `flex-wrap:wrap` 預設值，保留原生換行能力（AC1、AC2，見下方關鍵技術
   決策第 2、3 點的完整理由）。
4. `#regenerate-btn`／`#export-confirm-btn`／`#cleanup-btn` 文字：分別由
   `🔄 重新產生`／`⬇ 匯出`／`🗑 清除暫存` 改為 `重新產生`／`匯出`／
   `清除暫存`（AC4）。`#new-recording-btn` 的 `+ 新錄音` 前綴不動（範圍
   排除項明示）。
5. `class`、`id`、`onclick`、元素數量與順序全部不變（AC5）；
   `<script>` 區塊完全不動，`regenerateSummary()`／
   `exportSelectedFormat()`／`cleanupAndReset()`／
   `showView('view-upload')` 呼叫參數不受影響。`#modified-badge`／
   `#low-confidence-badge` 兩個徽章元素（預設 `display:none`，由
   `<script>` 動態切換顯示）維持在 `result-action-group-content` 內、
   相對順序不變，未受本次版面重構影響（範圍外事實，第 163/167 行 CSS
   與第 1106/1272/1332/1442 行 JS 皆不動）。
6. 第 70 行共用 `.btn-row` class 規則本身維持原樣，不動（範圍外明示）。

### 狀態碼
不涉及。純前端視覺/標記變更。

## 資料模型
無新增資料模型。

## 關鍵技術決策

1. **拆解「標題＋操作列同排」的最外層 flex 容器，改為 `h2`／
   `#result-meta`／操作列三個獨立 block-level 元素依序堆疊，取代
   SDLCAIP2-39/駁回版沿用的「同排 + nowrap + 橫向捲動」手法。** 理由：
   人類已明確否決橫向捲動（違反使用習慣）與 SDLCAIP2-39 的整體排版方案
   （設計拙劣、曾被 revert），並給出明確替代方向——三行堆疊。堆疊後操作
   列不再需要與標題共享水平空間，這正是原本換行問題的根源（可用寬度被
   標題排擠），拆開後問題在絕大多數寬度下自然消失，不需要任何 nowrap/
   捲動類手段來「硬擠」進同一排。

2. **不加 `flex-wrap:nowrap`、不加 `overflow-x:auto`，操作列三層
   `.btn-row` 容器維持共用 class 原生的 `flex-wrap:wrap`（自然換行）。**
   理由：(a) 人類已明確禁止橫向捲動這個技術手段本身，不只是禁止其視覺結
   果；(b) 人類指示「若判斷窄寬度仍需要 flex-wrap，用 wrap（自然換行到
   第二行）或其他非捲動手段」——共用 `.btn-row` class（第 70 行）預設值
   本來就是 `flex-wrap:wrap`，這正是「非捲動手段」，且不需要任何新增
   inline style 即可達成，是影響面最小、與既有共用 class 語意最一致的做
   法；(c) 操作列不再與標題共排後，AC1（1280px 寬螢幕不換行）在正常寬度
   下自然滿足，AC2（480px 窄螢幕）若觸發自然換行（例如
   `result-action-group-content` 內含徽章/下拉選單/兩顆按鈕，內容本身較
   長），屬於可接受的「自然換行到第二行」，不是 AC2 要避免的「不可預期
   的凌亂換行」或「橫向捲動」，符合人類需求原文「操作列…是一行」的精神
   （在絕大多數實際寬度下如此），也符合其對窄寬度換行 fallback 的明確放
   行。
3. **`result-action-group-content`（左組）與 `result-action-group-reset`
   （右組）之間的左右分佈邏輯（`justify-content:space-between`）維持原
   樣不動，不重新設計。** 這部分已是目前程式碼的既有寫法（SDLCAIP2-37 建
   立），且與人類需求「模板…匯出 維持原樣靠左」「清除暫存／新錄音 並排靠
   右對齊」完全吻合，不需要為此重新設計欄位或改用 `margin-left:auto` 等
   其他等效寫法——沿用既有寫法可將本次變更範圍縮到最小，降低回歸風險。
4. **移除操作列容器（原第 298 行）上已無作用的 `flex:1`，不遷移到新結構
   的任何一層。** 該屬性只在父層是 flex container 時才有效果；父層改為
   `#view-result`（非 flex，`class="view"`）後 `flex:1` 變成死屬性，保留
   只會誤導未來讀者以為它仍有作用，故隨本次重構一併清除，不特別立新的
   `flex` 規則替代（操作列本身不需要在新結構下伸縮撐滿寬度以外的行為，
   block-level 元素預設即已滿寬）。
5. **不新增 media query、不新增專屬 CSS class。** 三行堆疊本身以及操作
   列內部左右分佈全部靠既有 `.btn-row` class 與少量 inline
   `margin-bottom` 即可達成，延續 SDLCAIP2-36/37/39/40 已建立的「一次性
   容器排版用 inline style，不為單一場景新增等價 class」慣例，且未觸碰
   共用 `.btn-row` class 定義本身（範圍外明示）。

## UI 原型
`docs/design/SDLCAIP2-42-prototype.html`：靜態、可直接用瀏覽器開啟的原
型，重現變更後的三行堆疊結構（標題列 / meta 列 / 操作列，操作列內左組靠
左、右組靠右，三顆按鈕純文字，`+ 新錄音` 不變，且**不含任何水平捲動樣
式**）。檔案內同時提供「寬版（1280px 容器）」與「窄版（375px 容器，模擬
窄螢幕）」兩組並排展示，可直接目視確認：(a) 三行堆疊順序正確、(b) 兩種
寬度下皆無橫向捲動軸出現、(c) 窄版若操作列內容較長，僅以自然換行方式折
到第二行，容器本身不會出現 `overflow-x` 卷軸。不含任何後端呼叫、不含 JS
邏輯（按鈕僅為靜態展示，`onclick` 保留文字但不綁定真實函式，避免原型檔
案被誤用於功能驗證）。

## 開放設計問題（定稿時必須為空）
無。現況程式碼（第 291-322 行）與 SDLCAIP2-39 合併前狀態一致，目標三行
堆疊結構、操作列內部左右分佈維持原樣、按鈕文字移除 emoji 皆可從 ticket
既有五條 AC、人類 G1b 駁回意見的逐字替代需求，以及 SDLCAIP2-37/39/40 既
有設計文件直接推定，未發現規格未決的產品決策。
