# 設計文件 — SDLCAIP2-50 Design System｜歷史紀錄列表頁 view-history

## 對應需求規格

`docs/PRD.md`（G1 已核准版本）中 SDLCAIP2-50 段落，共 8 個 Gherkin scenario：`.card`
（`src/frontend/index.html` 第 533 行）沿用 SDLCAIP2-44 既有 token（回歸檢查，AC1）、
`#history-table`（第 535 行，`class="action-table"`）在 view-history 範圍內改用 `--ds-*`
token 但不得修改 `.action-table` 共用本體（AC2）、`#history-empty`（`.empty-state`，第 539
行）文字色改用 `--ds-*` token 但不得修改 `.empty-state` 共用本體（AC3）、`.section-title`
（第 534 行）移除裝飾性 emoji「📜」（AC4）、手機（<480px）表格不得撐破頁面且欄位可讀（AC5）、
點擊 `<tr>` 仍呼叫 `openMeetingDetail()`（回歸，AC6）、空清單時 `#history-table` 隱藏、
`#history-empty` 顯示（回歸，AC7）、其他頁面的 `.action-table`/`.empty-state`/`.card` 不受影響
（回歸，AC8）。

## 現況確認（讀碼結果，供後續章節引用）

- `src/frontend/index.html` 第 531–543 行：`#view-history` 只有一個 `.card`，內含
  `.section-title`（純文字「📜 歷史紀錄」，無返回按鈕）、`<table class="action-table"
  id="history-table">`（`thead` 兩欄：標題／建立時間，`tbody id="history-tbody"`）、
  `<div id="history-empty" class="empty-state">`。結構明顯比 SDLCAIP2-45 的 view-admin 單純
  （只有一張表、無 `<h4>` 子標題、無合計列）。
- 第 238–244 行 `.action-table` 共用本體、第 246–271 行 SDLCAIP2-45 已建立的
  `#view-admin .action-table th/td` 覆寫模式、`.ds-table-scroll`（第 268 行，全站共用 class，
  非 view-admin 專屬選取器）皆已存在，可直接沿用同一手法，不需重新發明。
- 第 323–324 行 `.empty-state` 共用本體：`text-align:center; padding:40px; color:var(--muted);`
  + `p { margin-top:8px; font-size:.9rem; }`。Grep 確認同一 class 在第 558（view-result 待辦
  事項空清單）、1016、1295、1338 行（其他頁面）皆被使用，證實是真正跨頁共用、AC3 明講不得修改
  的 class，與 AC2 對 `.action-table` 的隔離要求同一性質。
- 第 814–839 行 `openHistoryList()`：以 `document.getElementById('history-table')` /
  `document.getElementById('history-empty')` 取得元素後直接設定 `.style.display`（`table`/
  `none`/`block`），完全依 **id**，不依賴 DOM 結構（例如表格是否被某個 wrapper `<div>` 包住）。
  因此若依 SDLCAIP2-45 模式在 `<table id="history-table">` 外面加一層
  `<div class="ds-table-scroll">`，`table.style.display='table'`／`'none'` 仍直接作用在
  `#history-table` 本身，wrapper 不受影響、也不需要額外顯示/隱藏邏輯——AC7 的回歸行為不受本票
  影響。第 831 行 `onclick="openMeetingDetail(...)"` 綁在每個 `<tr>` 上，同樣與是否包 wrapper
  無關，AC6 不受影響。
- `.section-title` 第 186 行本體（`font-size:1rem; font-weight:600; color:var(--text);
  margin-bottom:14px; display:flex; align-items:center; gap:8px; flex-wrap:wrap;`）未被
  SDLCAIP2-44/45 token 化，本票延續 SDLCAIP2-45 決策 2 的先例：`.section-title` 本體字體
  token 化不在本票範圍（PRD 範圍外段落已明講），AC4 只要求移除 emoji 文字內容，屬於 HTML 文字
  變更，不涉及 CSS 規則變更。

## 介面/API 契約

無，本 Story 不涉及對外 API 變更。純前端靜態資源（HTML/CSS）調整，`src/frontend` 無建置流程，
不產生任何新的後端端點或請求/回應格式；`/api/meetings` 的資料擷取與 `openHistoryList()` 的
渲染邏輯（`tbody.innerHTML = meetings.map(...)`）不變動。

## 資料模型

無新增資料模型。

## 關鍵技術決策

1. **`#history-table` 的 view-history 專屬樣式一律用 `#view-history .action-table th` /
   `#view-history .action-table td` 這種「視圖 id 前綴」選取器覆寫，完全比照
   SDLCAIP2-45 對 `#view-admin` 已建立的模式，絕不修改第 238–244 行 `.action-table` 本體。**
   理由：AC2 明講「以 `#view-history .action-table th/td` 實作」；共用本體同時被
   view-result／view-admin 使用（見現況確認），若改本體會破壞 AC8（其他頁面不得受影響）。CSS
   選取器特異性 `#id .class`（0,1,1）高於 `.class`（0,1,0），可直接覆寫、不需 `!important`。
   顏色/邊框/字體對照值與 SDLCAIP2-45 完全一致（同一份 design-system、同一種表格語意），維持
   全站表格視覺一致性：
   ```css
   #view-history .action-table th {
     background: var(--ds-badge-bg);
     color: var(--ds-text-secondary);
     border-bottom: 1px solid var(--ds-border);
     font-family: var(--ds-font-sans);
     font-size: 13px;
   }
   #view-history .action-table td {
     color: var(--ds-text-primary);
     border-bottom: 1px solid var(--ds-border);
     font-family: var(--ds-font-sans);
     font-size: 13px;
   }
   ```
   字級沿用 SDLCAIP2-45 已定案的 13px（`tokens.json` Body 群組 `caption`：13px/18px/400），
   理由不再重複推導——本票與 SDLCAIP2-45 是同一個 `.action-table` 元件在不同頁面的套用，
   若兩頁字級不一致，會造成使用者在 view-admin 與 view-history 之間切換時表格資訊密度不一致，
   明確違反 design-system「同元件同外觀」的目的；因此本票直接沿用，不重新評估
   `body`（15px）等其他選項。`td[contenteditable="true"]` 的黃色編輯樣式在 view-history 未被
   使用（此頁表格唯讀），不需處理。

2. **手機版（<480px）沿用 SDLCAIP2-45 決策 4 的「捲動容器」策略：`<table id="history-table">`
   外包 SDLCAIP2-45 已新增的全站共用 class `.ds-table-scroll`（第 268 行，`overflow-x:auto`），
   並在 `#view-history` 範圍內於手機斷點給 `.action-table` 一個 `min-width`。**
   理由：
   - `.ds-table-scroll` 是 SDLCAIP2-45 新增的全新、非 view-admin 專屬的 class（本體定義在
     `#view-admin`/`.action-table` 覆寫區塊之外，選取器本身不含 `#view-admin` 前綴），本票
     直接重用同一個 class，不需要新增或修改任何共用規則，符合 AC2/AC8「不修改共用本體」的
     精神，也維持「全站遇到手機版塞不下的橫向內容一律用捲動而非硬縮」的一致手法。
   - `min-width` 需要針對 view-history 的欄位（標題、建立時間）另訂數值，不可直接沿用
     SDLCAIP2-45 的 `560px`（那是 5 欄數字/日期表格的推算值，本頁只有 2 欄且「標題」欄需要
     容納較長的會議標題文字）：
     ```css
     #view-history .action-table { min-width: 420px; }
     ```
     推算：「標題」欄需保留至少 ~260px 讓常見長度的會議標題不至於過度換行/擠壓（比照現有
     `padding:10px 14px` 抓可讀下限）；「建立時間」欄為固定格式時間字串（如
     `fmtDateTime()` 輸出的 `2026-09-24 10:30`），抓 ~160px 即足夠不換行。兩欄加總取整為
     420px。與 SDLCAIP2-45 相同，此為估算值非精確科學數字，developer 實測後如需 ±30px
     微調，在不偏離「捲動而非硬縮」這個策略本身的前提下可自行調整，不需回頭改設計文件。
   - HTML 變更（僅 `#view-history` 內一個 `<table>`，id/結構不變，只加一層 wrapper）：
     ```html
     <div class="ds-table-scroll">
       <table class="action-table" id="history-table" style="display:none;">
         ...（原內容不變，含 tbody id="history-tbody"）...
       </table>
     </div>
     ```
   - 已於「現況確認」段落確認 `openHistoryList()`（第 815–839 行）以 id 直接操作
     `#history-table`/`#history-empty` 的 `style.display`，wrapper 不影響其行為，AC6/AC7
     回歸不受影響。

3. **`#history-empty` 的 view-history 專屬樣式用 `#view-history .empty-state` 選取器覆寫文字
   色，不修改第 323–324 行 `.empty-state` 本體。**
   理由：AC3 明講「以 `#view-history .empty-state` 實作」，且本體同時被第 558、1016、1295、
   1338 行共用，改本體會破壞 AC8。只覆寫文字顏色這一項（`.empty-state` 本體的
   `text-align`/`padding` 等版面屬性維持繼承，不重複定義）：
   ```css
   #view-history .empty-state { color: var(--ds-text-secondary); }
   ```
   選 `--ds-text-secondary`（而非 `--ds-text-primary`）：呼應共用本體原本的 `color:var(--muted)`
   語意——空清單提示文字本來就是次要、非強調內容，`--ds-text-secondary` 是 design-system 對
   「次要文字」的既有對應 token，與 SDLCAIP2-45 決策 1 對 `.action-table td`／表頭文字色的
   token 選用邏輯一致（次要語意 → secondary token）。`.empty-state p` 的 `font-size:.9rem`
   未被 AC3 要求變更，維持不動。

4. **AC4（移除 `.section-title` 內的「📜」emoji）為純 HTML 文字內容變更，不涉及任何 CSS 規則
   新增或修改。**
   ```html
   <div class="section-title">歷史紀錄</div>
   ```
   理由：`.section-title` 本體（第 186 行）本身不含 emoji，emoji 是寫死在 view-history 這個
   實例的文字內容裡（`📜 歷史紀錄`），移除後其餘頁面的 `.section-title` 不受影響，符合 AC8；
   本體字體 token 化明確在 PRD 範圍外（沿用 SDLCAIP2-45 決策先例），不在本票處理。

5. **AC1（`.card` 沿用 SDLCAIP2-44 token）不需要任何程式碼變更，本設計文件把它列為回歸斷言
   （regression assertion），而非待實作項目。**
   理由：`.card` 是 SDLCAIP2-44 已全站遷移的共用 class，view-history 的 `.card`
   （第 533 行）本來就繼承該規則，未被本票任何選取器改動。測試階段應針對此點寫「維持現狀」的
   回歸驗證，不應誤解成需要新增樣式。

## UI 原型

`docs/design/SDLCAIP2-50-prototype.html` —— 可直接在瀏覽器開啟的靜態原型，重現 view-history 的
`.card` + `.section-title`（已移除 emoji）+ 捲動包裝表格 + 空清單狀態，套用上述決策 1/2/3/4
的具體 CSS。原型內同時提供「桌面寬度」（900px 容器）與「手機寬度」（360px 容器，模擬 <480px
斷點）兩個並排預覽區塊，並各自提供「有資料列」（before/after 對照：舊版 token 與新版 `--ds-*`
token 並排比較）與「空清單狀態」兩種畫面，讓人類在 G1b 審核時不必自行縮放瀏覽器視窗、也不必
手動清空資料即可同時看到所有情境。也可另外用瀏覽器 DevTools 縮窄視窗驗證真實斷點行為。

## 開放設計問題（定稿時必須為空）

無。`.action-table`/`.empty-state` 範圍隔離（決策 1/3）、手機表格技術與 `min-width` 數值
（決策 2）、`.section-title` emoji 移除的實作範圍（決策 4）、AC1 的回歸性質（決策 5），皆已
依現有規格、程式碼現況、以及 SDLCAIP2-45 已定案的同類決策明確解決並附理由，未留待 developer
或後續工單自行決定。
