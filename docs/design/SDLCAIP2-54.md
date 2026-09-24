# 設計文件 — SDLCAIP2-54 Design System｜view-result 標題／操作列／分頁 Tabs 套用設計系統

## 對應需求規格

`docs/PRD.md`（G1 已核准版本）中 SDLCAIP2-54 段落，從 SDLCAIP2-49（view-result）拆出，涵蓋
`#view-result` 的 `<h2>`（~460 行）、`#result-meta`（~461 行）、操作列（`.btn-row`，~462-484 行，
兩組 `result-action-group-content`／`result-action-group-reset`）、`.tabs`/`.tab`（~178-183 行，
與 `#view-history-detail` 共用）。共 8 個 AC：

- AC1：`<h2>`（~460 行）文字「會議紀錄」，移除「📋」；h2 token 18px/26px/600，色
  `--ds-text-primary`；<480px 17px/24px/600。
- AC2：`#result-meta`（~461 行，現用 inline style + 舊 `--muted`）→ caption token
  13px/18px/400，色 `--ds-text-secondary`。需決定是否移除 inline style 改用外部 CSS
  （inline style 會覆蓋外部 CSS；比照 SDLCAIP2-46 同類場景的處理方式）。
- AC3（回歸）：六個控制項順序（模板→重新產生→匯出格式→匯出→清除暫存→新錄音）與同排
  不換行在 1280px 與 480px 維持不變；清除暫存／新錄音靠右對齊；按鈕文字不變。明確**不**套用
  design-system README「工具列在手機版垂直堆疊」的規則——SDLCAIP2-42 已鎖定的行為優先。
- AC4（回歸）：按鈕仍呼叫 `regenerateSummary()`／`exportSelectedFormat()`／
  `cleanupAndReset()`／`showView('view-upload')`，參數不變。
- AC5：`#template-select`（~467 行）與 `#export-format-select`（~471 行）加上 `.input`
  class；高度/邊框/圓角/focus 比照 design-system input，option 與 onchange/data binding
  不變。需檢查加上 `.input` 是否破壞 AC3 的同排不換行（例如 `.input` 手機版 `width:100%`
  會破壞），並提出必要的範圍限定覆寫。
- AC6：`.tabs`/`.tab`（~178-183 行，僅被 view-result 與 view-history-detail 共用）：目前分頁
  文字/底線 `--ds-ink-100`、字重 600；非目前分頁 `--ds-text-secondary`；分頁列底部邊框
  `--ds-border`。view-result 分頁文字移除 emoji（「📝 會議紀錄」→「會議紀錄」、
  「🎙 逐字稿」→「逐字稿」）。history-detail 分頁樣式同步改變（預期、已揭露）。`switchTab()`
  行為不變——確認 `switchTab()` 不會改寫按鈕文字。
- AC7：<480px 分頁列不換行/不溢出，允許 `flex:1` 等寬。
- AC8：`#modified-badge`「● 未儲存修改」與 `#low-confidence-badge`「⚠ …」維持符號、
  顯示/隱藏邏輯、琥珀色不變。

範圍外：五張卡片（SDLCAIP2-55）、逐字稿分頁（SDLCAIP2-56）、共用 `.btn` 本體、徽章顏色、
匯出檔案樣式、全站 header。

## 現況確認（讀碼結果，供後續章節引用）

- `src/frontend/index.html` 第 458-489 行：`#view-result` 依序為 `<h2>`（460 行，inline style
  `font-size:1.2rem;margin-bottom:4px;`，文字「📋 會議紀錄」）、`#result-meta`（461 行，inline
  style `color:var(--muted);font-size:.8rem;margin-bottom:16px;`）、操作列（462-484 行，三層
  `.btn-row`，SDLCAIP2-42 已定案的三行堆疊＋內部左右分佈結構）、`.tabs`（486-489 行，兩顆
  `.tab`，文字帶 emoji）。此結構為 SDLCAIP2-42 G1b 駁回後修訂版落地的最終狀態，本票**不**重新
  設計版面結構，僅調整視覺 token 與必要的範圍限定覆寫（AC1/AC2/AC5/AC6/AC7）。
- 第 153 行 `.btn-row { display: flex; gap: 10px; flex-wrap: wrap; }`（全站共用，範圍外，不可
  修改）；第 154-157 行全域 `.btn` 手機版規則 `@media (max-width: 479px) { .btn { height:
  var(--ds-control-h-mobile); width: 100%; } }`（SDLCAIP2-44 已建立，範圍外）。這條全域規則已
  讓 `#regenerate-btn`／`#export-confirm-btn`／`#cleanup-btn`／`#new-recording-btn` 在
  <480px 各自佔滿容器寬度（`.btn-row` 的 `flex-wrap:wrap` 因此在窄寬度自然觸發換行）——這是
  **本票開始之前就存在**的行為，非本票造成，AC3「同排不換行…480px 不變」的「不變」在本票語境
  下解讀為「本票不得再新增任何進一步影響換行狀態的 CSS」，而非「本票需要讓六個控制項在
  480px 真正擠進單一橫排」（後者會是新增的產品行為，本票規格未要求、也未授權）。
- `#template-select`（232-233 行）與 `#export-format-select`（234-235 行）目前各自有一條
  ID 專屬 CSS 規則（`font-size:.9rem;padding:8px 10px;border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-family:inherit;`），特異性（0,1,0，ID）高於
  `.input`（0,1,0，class）同階但 ID 選取器書寫順序在 `.input` 之後，若不處理会直接覆蓋
  `.input` 的新樣式，兩者無法同時套用完整視覺。
- `.input`/`select.input`（204-220 行，SDLCAIP2-44 已建立、SDLCAIP2-52 決議「本工單不套用到
  任何現有元素」）含手機版規則 `@media (max-width: 479px) { .input, select.input { height:
  var(--ds-control-h-mobile); width: 100%; } }`——這是本票唯一會**新增**、且會影響 AC3 換行
  狀態的風險點（決策 4 處理）。
- `.tabs`/`.tab`（178-183 行）grep 確認全檔案僅 `#view-result`（487-488 行）與
  `#view-history-detail`（599-600 行，`history-tab-btn-minutes`/`history-tab-btn-transcript`，
  文字同樣帶 emoji）使用，證實 AC6「僅被兩頁共用」為真，可直接改共用本體。
- `switchTab()`（1651-1656 行）僅操作 `.tab-minutes`/`#tab-transcript` 的
  `style.display`、`#tab-btn-minutes`/`#tab-btn-transcript` 的 `classList.toggle('active', …)`，
  未寫入/讀取任何按鈕文字，確認 AC6「`switchTab()` 行為不變」對程式碼零風險。
- `docs/design-system/components/Tabs/README.md`：目前分頁 `ink-100`/字重 600/底線 2px
  `ink-100`；非目前分頁 `text-secondary`；底部 `border` 分隔線貫穿整列；分頁間距
  `space-6`（32px，桌面）；手機版分頁改為等寬 `flex:1`，不使用固定間距。`docs/design-system/
  tokens.json` 的 Body 群組另有 `label-button`（14px/20px/500，usage 明講「按鈕、分頁文字」），
  直接對應本元件。
- `docs/design-system/components/Input/README.md`：高度桌面 `control-h-desktop`／手機
  `control-h-mobile`，邊框 `border-strong`，圓角 `radius-sm`，focus 2px `focus-ring`——與現有
  `.input` class（204-220 行）定義完全一致，AC5 只是把既有 class 套用到這兩個既有元素，非新建
  元件。

## 介面/API 契約

無，本 Story 不涉及對外 API 變更。純前端靜態資源（HTML/CSS）調整，`src/frontend` 無建置流程，
不產生任何新的後端端點或請求/回應格式；`regenerateSummary()`/`exportSelectedFormat()`/
`cleanupAndReset()`/`showView()`/`switchTab()`/`markModified()` 等既有 JS 邏輯與其呼叫參數不變動。

## 資料模型

無新增資料模型。

## 關鍵技術決策

1. **AC1/AC2：移除 `<h2>` 與 `#result-meta` 的 inline `style`，改用外部 CSS 規則
   `#view-result h2` 與 `#result-meta`（ID 選取器）覆寫，比照 `#view-admin h4`
   （259-266 行）既有的「ID + 元素/直接選取器」範圍限定模式。**
   ```css
   #view-result h2 {
     font-family: var(--ds-font-sans);
     font-size: 18px; line-height: 26px; font-weight: 600;  /* tokens.json Heading.h2 */
     color: var(--ds-text-primary);
     margin-bottom: 4px;
   }
   @media (max-width: 479px) {
     #view-result h2 { font-size: 17px; line-height: 24px; }  /* Heading.h2-mobile */
   }
   #result-meta {
     font-family: var(--ds-font-sans);
     font-size: 13px; line-height: 18px; font-weight: 400;  /* tokens.json Body.caption */
     color: var(--ds-text-secondary);
     margin-bottom: 16px;
   }
   ```
   理由：inline style 的特異性（1,0,0,0）高於任何外部類別/ID 選取器，若保留 inline style，
   本票新增的 CSS 規則永遠不會生效，這正是 AC2 條文本身點出的問題（「inline style would
   override external CSS」）。改用 ID 選取器（`#result-meta` 本身已有 id；`<h2>` 無 id，改用
   `#view-result h2` 描述性選取器，與 `#view-admin h4` 前例一致）取代 inline style 是唯一能讓
   token 生效、又不需要 `!important` 的做法。`margin-bottom` 兩個 AC 皆未要求變更，沿用原
   inline 數值（4px／16px）搬進新規則，不改變版面間距。`font-family` 兩個 AC 皆未逐字列出，
   但比照 SDLCAIP2-45/55 已定案的判斷基準（既然要接上 design-system 的字體視覺語言，遺漏
   `font-family` 會產生「一半 design-system、一半瀏覽器預設字體」的不一致），一併補上。

2. **AC1 emoji 移除：`<h2>📋 會議紀錄</h2>` → `<h2>會議紀錄</h2>`。**
   純文字內容變更，`id`/`onclick`/結構完全不受影響（`<h2>` 本無 `onclick`）。

3. **AC3（六控制項順序/靠右對齊/按鈕文字）與 AC4（四個函式呼叫參數）不需要任何 CSS/JS 變更，
   本設計文件把它們列為回歸斷言，而非待實作項目。**
   理由：現況確認已證實 SDLCAIP2-42 定案的三行堆疊結構、`result-action-group-content`（左，
   `justify-content:space-between` 左組）／`result-action-group-reset`（右組）左右分佈、四個
   `onclick` 呼叫皆維持原樣，本票（決策 1/2/4/5）未觸碰這些選取器/結構，只新增字級/色彩/
   class 屬性。唯一有換行風險的變更點是決策 4（AC5 的 `.input`），已於該決策明確處理並中和
   風險，不需要另外為操作列本身新增任何 `nowrap`/`overflow-x` 類手段——這類手段已被
   SDLCAIP2-42 人類明確駁回，本票延續同一立場，不重新引入。

4. **AC5：`#template-select`／`#export-format-select` 加上 `class="input"`，同時刪除兩者
   舊有的 ID 專屬 CSS 規則（232-235 行），並新增一條範圍限定覆寫中和 `.input` 手機版
   `width:100%` 對 AC3 換行狀態的影響。**
   ```html
   <select id="template-select" class="input"></select>
   ...
   <select id="export-format-select" class="input"> ... </select>
   ```
   ```css
   /* 刪除 232-235 行舊 #template-select / #export-format-select 規則，
     改由 .input / select.input（204-220 行）提供完整樣式 */

   /* ===== SDLCAIP2-54: view-result select.input 換行風險中和（比照 SDLCAIP2-44
      決策 5 的 header .btn { width:auto } 手法） ===== */
   @media (max-width: 479px) {
     #view-result #template-select.input,
     #view-result #export-format-select.input { width: auto; }
   }
   ```
   - 刪除舊 ID 專屬規則：兩條規則與 `.input` 提供幾乎相同語意（字級/邊框/圓角/顏色），保留
     會因 ID 選取器特異性更高而覆蓋 `.input` 的新樣式，讓 AC5「高度/邊框/圓角/focus 比照
     design-system input」實質上無法生效；規則本身除了 AC5 要求替換的屬性外沒有其他獨有邏輯，
     刪除是安全的重構（與 SDLCAIP2-47 決策 2「移除失去意義的死規則」同一原則）。
   - 新增 `width: auto` 範圍限定覆寫：`.input` 手機版規則（218 行）帶
     `width: 100%`，是**本票新增** class 才會第一次作用在這兩個既有元素上的屬性——現況確認
     已證實加上 `.input` 前，這兩個 `<select>` 在手機版維持瀏覽器原生（非 100%）寬度，若不
     中和，會讓 480px 版面在「加上 `.input` 之後」比「加上之前」多出兩個滿版寬度元素，是本票
     自己引入的新換行行為，違反 AC3「480px 不變」。用 `#view-result` 前綴 + `.input`
     class 選取器（特異性 0,3,0）覆寫 `.input` 的 `width:100%`（特異性 0,2,0）足以生效，
     不需要 `!important`；手法與 SDLCAIP2-44 決策 5 `header .btn { width: auto; }` 的
     「範圍限定排除全域手機版規則」完全同一模式。1280px 桌面版不受影響（該覆寫僅在
     `max-width:479px` media query 內）。

5. **AC6：`.tabs`/`.tab` 直接改共用本體（178-183 行），套用 Tabs README 全部規格（含
   README 明講但 AC 未逐字列出的 `label-button` 字級 token 與桌面分頁間距 `space-6`），
   view-result 分頁文字移除 emoji；history-detail 分頁文字**不**移除 emoji。**
   ```css
   .tabs {
     display: flex;
     gap: var(--ds-space-6);
     border-bottom: 2px solid var(--ds-border);
     margin-bottom: 24px;
   }
   .tab {
     padding: 10px 20px;
     cursor: pointer;
     border: none; background: none;
     font-family: var(--ds-font-sans);
     font-size: 14px; line-height: 20px; font-weight: 500;  /* tokens.json Body.label-button */
     color: var(--ds-text-secondary);
     border-bottom: 2px solid transparent;
     margin-bottom: -2px;
     transition: color .15s, border-color .15s;
   }
   .tab.active {
     color: var(--ds-ink-100);
     font-weight: 600;
     border-bottom-color: var(--ds-ink-100);
   }
   @media (max-width: 479px) {
     .tabs { gap: 0; }
     .tab { flex: 1; min-width: 0; text-align: center; }
   }
   ```
   ```html
   <button class="tab active" id="tab-btn-minutes" onclick="switchTab('minutes')">會議紀錄</button>
   <button class="tab" id="tab-btn-transcript" onclick="switchTab('transcript')">逐字稿</button>
   ```
   - `label-button` 字級/字重與桌面 `gap: var(--ds-space-6)`：AC6 條文只逐字列出顏色/字重/
     底線/底部邊框，未提字級與間距，但 `tokens.json` 明講 `label-button` 的 usage 就是「按鈕、
     分頁文字」，且 Tabs README 明講桌面分頁間距為 `space-6`——這兩者都是「套用 Tabs
     元件」這件事在 design-system 文件裡唯一、明確對應的既有規格，比照 SDLCAIP2-55 決策 2
     的判斷基準（把元件套好套滿、避免「一半 design-system」），一併套用而非只套用 AC 逐字
     列出的三項。
   - `.tab.active` 額外加 `font-weight: 600`：AC6 明講「active tab text/underline
     --ds-ink-100, weight 600」，非目前分頁維持 `label-button` 預設字重 500（README 描述
     「非目前分頁…字重維持 label-button 預設」）。
   - 手機版 `.tab { flex: 1; min-width: 0; }`：直接對應 AC7「<480px 不換行/不溢出，允許
     flex:1 等寬」與 Tabs README「手機版分頁改為等寬…避免文字被壓縮」；`min-width: 0`
     是必要的技術細節（flex item 預設 `min-width: auto` 會依內容寬度撐開，可能在極窄視窗
     下仍造成溢出，加上 `min-width: 0` 讓 `flex:1` 真正等分可用寬度，兩個分頁文字皆為
     2-4 個中文字，等分後仍可完整顯示不換行/不省略）；`.tabs` 手機版 `gap: 0`
     是因為等寬版面下固定 `gap` 會與「等分可用寬度」的效果衝突（多出的 `gap` 會讓兩個
     等寬分頁總寬度超出容器，可能觸發溢出），故手機版改為靠 `flex:1` 本身的等分間距，
     不另外疊加固定 `gap`。
   - **明確不套用 design-system README「工具列手機版垂直堆疊」規則**：AC3 已明講此規則
     不適用於本頁操作列（`.btn-row`），本決策僅套用 Tabs 元件自己的 README（`.tabs`/`.tab`
     與 `.btn-row` 是完全不同的元件，Tabs README 本身也未提及「垂直堆疊」，兩者無關聯，此處
     重申避免混淆。
   - view-result 分頁文字移除 emoji，history-detail（599-600 行）不動：AC6 條文明講
     「view-result tab labels drop emoji」，只點名 view-result；「History-detail tabs change
     too (expected, disclosed)」這句緊接在後、且用「change」（樣式變化）而非「drop emoji」
     措辭，對照現況確認已證實 `.tabs`/`.tab` 是共用本體，指的應是**樣式**（顏色/字重/底線/
     底部邊框/字級/間距）透過共用 class 自動套用到 history-detail，而非要求連文字也一併改。
     本設計嚴格依 AC 逐字範圍，不擴大解讀替 history-detail 的分頁文字也拿掉 emoji——若真的
     需要，應由後續工單另行提出 AC，不由本票自行決定（避免違反「不可自行發明產品需求」的
     架構角色分際）。

6. **AC7 不需要任何額外實作，已由決策 5 的 `.tab { flex: 1; min-width: 0; }` 完整涵蓋，
   本設計文件把它列為決策 5 的直接結果而非獨立待辦項目。**

7. **AC8（徽章符號/顯示邏輯/琥珀色不變）不需要任何程式碼變更，本設計文件把它列為回歸斷言。**
   理由：`#modified-badge`／`#low-confidence-badge`（327-332 行）與其顯示/隱藏邏輯
   （`markModified()` 等）皆不在本票任何決策的選取器範圍內（決策 1-5 僅觸碰 `#view-result h2`／
   `#result-meta`／`#template-select`／`#export-format-select`／`.tabs`/`.tab`），已於現況確認
   逐一核對。

## UI 原型

`docs/design/SDLCAIP2-54-prototype.html` —— 可直接在瀏覽器開啟的靜態原型，套用上述決策 1-7
的具體 CSS/HTML，以 Before／After 對照方式，桌面（1280px 容器）與手機（360px 容器，模擬
<480px 斷點）並排呈現：`#view-result` 的 `<h2>`＋`#result-meta`、操作列（兩組，同排不換行的
現況/After 對照）、Tabs（active/inactive 狀態），並另附一個 `#view-history-detail` Tabs 區塊，
示範共用樣式（決策 5）同步套用後的視覺效果（emoji 保留、顏色/底線/字重比照決策 5）。純靜態
展示，`onclick` 保留文字但不綁定真實函式，不含任何後端呼叫或 JS 邏輯。也可另外用瀏覽器
DevTools 縮窄視窗驗證真實斷點行為。

### 最終數值對照表

| 選取器 | 屬性 | 舊值 | 新值 |
|---|---|---|---|
| `#view-result h2` | font-size / line-height / font-weight | inline `1.2rem` / 正常 / 正常 | `18px` / `26px` / `600`（<480px：`17px`/`24px`） |
| `#view-result h2` | color | 未設（繼承 `--text`） | `var(--ds-text-primary)` |
| `#result-meta` | font-size / line-height / font-weight | inline `.8rem` / 正常 / 正常 | `13px` / `18px` / `400` |
| `#result-meta` | color | inline `var(--muted)` | `var(--ds-text-secondary)` |
| `#template-select` / `#export-format-select` | class | 無 | `.input` |
| `#template-select` / `#export-format-select` | 舊 ID 專屬規則（232-235 行） | 存在 | 刪除，改由 `.input` 提供 |
| `#view-result select.input`（手機版） | width | `.input` 預設 `100%` | 覆寫回 `auto` |
| `.tabs` | gap / border-bottom | `4px` / `2px solid var(--border)` | `var(--ds-space-6)` / `2px solid var(--ds-border)`（<480px gap: `0`） |
| `.tab` | font-size/line-height/font-weight/color | `.9rem`/正常/`500`/`var(--muted)` | `14px`/`20px`/`500`/`var(--ds-text-secondary)` |
| `.tab.active` | color / font-weight / border-bottom-color | `var(--primary)` / `500` / `var(--primary)` | `var(--ds-ink-100)` / `600` / `var(--ds-ink-100)` |
| `.tab`（手機版） | flex / min-width / text-align | 無 | `1` / `0` / `center` |
| `#tab-btn-minutes` / `#tab-btn-transcript` 文字 | — | `📝 會議紀錄` / `🎙 逐字稿` | `會議紀錄` / `逐字稿` |
| `#history-tab-btn-minutes` / `#history-tab-btn-transcript` 文字 | — | `📝 會議紀錄` / `🎙 逐字稿` | 不變（僅樣式隨共用本體改變） |

## 開放設計問題（定稿時必須為空）

無。inline style 移除與改用外部 ID/描述性選取器（決策 1）、AC3/AC4 的回歸性質與換行風險
的唯一來源（決策 3/4）、`.input` 手機版寬度中和覆寫（決策 4）、Tabs README 全量套用範圍與
手機等寬技術手段（決策 5）、history-detail 分頁文字不動 emoji 的範圍解讀（決策 5 末段）、
AC7/AC8 的回歸與衍生性質（決策 6/7），皆已依現有規格、程式碼現況、`docs/design-system/`
元件 README，以及 SDLCAIP2-42/44/45/47/55 已定案的同類決策明確解決並附理由，未留待
developer 或後續工單自行決定。
