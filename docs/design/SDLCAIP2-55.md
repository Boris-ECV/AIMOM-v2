# 設計文件 — SDLCAIP2-55 Design System｜結果頁 view-result「會議紀錄」分頁五張卡片

## 對應需求規格

`docs/PRD.md`（G1 已核准版本，2026-09-24 通過）中 SDLCAIP2-55 段落，從 SDLCAIP2-49
（view-result）拆出，僅涵蓋 `#view-result` 「📝 會議紀錄」分頁（`#tab-minutes`）內的五張
`.card`：會議資訊、摘要、待辦事項、決定事項、討論重點。共 8 個 AC：

- AC1：`#view-result .section-title` 新增範圍限定規則，套用 `tokens.json` Heading `h2`
  （18px/26px/600，手機 `h2-mobile` 17px/24px/600），文字色 `--ds-text-primary`。
- AC2：`.meeting-info-grid` 與其 `label`/`input`（第 226–232 行，僅被 view-result 與
  view-history-detail 共用 → 直接改共用本體）：label 用 `--ds-text-secondary` +
  caption token；input 邊框 `--ds-border-strong`、圓角 `--ds-radius-sm`、高度
  `--ds-control-h-desktop`（手機 `--ds-control-h-mobile`）、placeholder
  `--ds-text-placeholder`、focus-visible 2px `--ds-focus-ring`；欄位間距
  `--ds-space-4`；<480px 單欄（間距 `--ds-space-3`）、寬度 100%。`onchange="markModified()"`
  與 placeholder 文字不變。
- AC3：`#summary-text`（第 222–224 行）：行高/文字色改用 Body `body` token（手機
  `body-mobile`）、`--ds-text-primary`；`contenteditable` 的外框/底色提示邏輯保留，顏色改
  `--ds-*`。
- AC4：`#view-result .action-table th/td` 新增範圍限定規則，比照 `#view-admin` 既有模式
  （約第 247–258 行）。共用 `.action-table` 本體（238–244 行）不動；
  `td[contenteditable="true"]` 編輯樣式（244 行）不變。
- AC5：`.decision-list`（273–277 行，僅與 view-history-detail 共用）：li 邊框
  `--ds-border`、字體改 body token；`li::before` 勾號顏色 `--ds-text-primary`（原
  `var(--success)`）。
- AC6：`.topic-item`/`.topic-header`/`.topic-body`（279–286 行，僅與 view-history-detail
  共用）：item 邊框 `--ds-border`；header 底色 `--ds-badge-bg`、文字
  `--ds-text-primary`、hover 底色（283 行，`#F1F5F9`）改一個 `--ds-*` 灰階 token；body
  文字 `--ds-text-secondary`、`--ds-font-sans`；`toggleTopic()` 的 `.open` 行為不變。
- AC7：<480px 不得因待辦事項表格造成頁面級橫向捲軸（參照 SDLCAIP2-45/50 手法）。
- AC8：編輯/儲存 JS 行為不變（`#action-tbody`/`#decision-list`/`#topics-container` 的
  id/class/data binding 不變，`markModified()` 顯示 `#modified-badge`）。

範圍外（明確不處理）：標題/操作列/Tabs（SDLCAIP2-54）、逐字稿分頁（SDLCAIP2-56）、`.card`
本體、`.action-table`/`.empty-state`/`.section-title` 共用本體、匯出檔案樣式。

補充背景：人類後續已決議（SDLCAIP2-58）由 view-history-detail 抄用本票
`#view-result .section-title` 與 `.action-table` 的最終數值，因此本文件在「關鍵技術決策」
最後附一張總表，供該票直接查表複製，不需重新推導。

## 現況確認（讀碼結果，供後續章節引用）

- `src/frontend/index.html` 第 475–513 行：`#tab-minutes` 內依序為五張 `.card`（會議資訊 /
  摘要 / 待辦事項 / 決定事項 / 討論重點），皆使用共用 `.section-title`（186–201 行，本體與
  `.badge` 皆為 SDLCAIP2-44 已處理，不在本票範圍）。
- `.meeting-info-grid`（226–232 行）與 `.decision-list`（273–277 行）、`.topic-item` 系列
  （279–286 行）皆被 `#view-history-detail`（565、598、602 行一帶）以相同 class 直接沿用，
  Grep 確認整個檔案內僅此兩處使用，證實是「僅兩頁共用」而非全站共用，可直接改共用本體，
  不需要 `#view-result` 前綴隔離（與 AC2/AC5/AC6 的描述一致：這三組明講「共用本體」）。
  `.action-table` 與 `.section-title` 則是全站共用（另被 view-admin/view-history 使用，見
  SDLCAIP2-45/50 設計文件現況確認），因此 AC1/AC4 改用 `#view-result` 前綴隔離規則，不碰
  共用本體，與既有前例（SDLCAIP2-45 決策 1、SDLCAIP2-50 決策 1）手法一致。
- `#action-tbody`（500–502 行）目前渲染的 `<td>` 帶
  `contenteditable="false" ondblclick="enableEdit(this)"`（`renderMinutes()`，1274–1282
  行），JS 只以 `document.getElementById('action-tbody')` 操作內容，`<table>` 本身沒有任何
  `style.display` 切換邏輯（與 SDLCAIP2-50 的 `#history-table` 不同）——比照 SDLCAIP2-45/50
  已驗證的做法，在 `<table>` 外包一層 `.ds-table-scroll`（既有全站共用 class，第 268 行）
  對 JS 完全無影響，AC8 不受影響。
- `renderMinutes()`（1249–1307 行）與 `enableEdit`/`disableEdit`/`markModified()`
  （1409–1419 行）皆未在渲染出的 HTML 中寫入任何行內 `style`（僅設定 `id`/`contenteditable`
  屬性），因此本票新增的 CSS 規則不會被行內樣式覆蓋，可正常生效。
- `docs/design-system/tokens.json` 的 `type.groups`：Heading `h2`
  18px/26px/600（`h2-mobile` 17px/24px/600）、Body `body` 15px/28px/400（`body-mobile`
  14px/26px/400）、Body `caption` 13px/18px/400（`caption-mobile` 12px/16px/400）。與
  SDLCAIP2-45 決策 2 已定案的慣例相同：`:root` 目前沒有字級/行高/字重的 `--ds-*` CSS 變數，
  本票延續同一做法，把具體數值直接寫進規則並註解對應 `tokens.json` 條目名稱，不新增變數。

## 介面/API 契約

無，本 Story 不涉及對外 API 變更。純前端靜態資源（HTML/CSS）調整，`src/frontend` 無建置
流程，不產生任何新的後端端點或請求/回應格式；`renderMinutes()`/`enableEdit`/`disableEdit`/
`markModified()`/`toggleTopic()` 的渲染與互動邏輯不變動。

## 資料模型

無新增資料模型。

## 關鍵技術決策

1. **AC1：`#view-result .section-title` 用「視圖 id 前綴」範圍限定規則覆寫，不動共用本體
   （186–201 行），套用 Heading `h2`/`h2-mobile`。**
   理由：`.section-title` 為全站共用（另被 view-admin/view-history/view-history-detail
   使用），若改共用本體會違反範圍外規則；`#id .class`（0,1,1）特異性高於 `.class`
   （0,1,0），可直接覆寫不需 `!important`。字重/`margin-bottom`/`display:flex` 等版面屬性
   維持繼承共用本體，只覆寫 AC1 明講的三項（字級/行高/顏色）：
   ```css
   #view-result .section-title {
     font-size: 18px;   /* tokens.json Heading.h2 */
     line-height: 26px;
     font-weight: 600;
     color: var(--ds-text-primary);
   }
   @media (max-width: 479px) {
     #view-result .section-title {
       font-size: 17px;  /* tokens.json Heading.h2-mobile */
       line-height: 24px;
     }
   }
   ```
   `.section-title .badge`（189–201 行）已由 SDLCAIP2-44 token 化，AC1 未要求變更，不動。

2. **AC2：`.meeting-info-grid`／`label`／`input` 直接改共用本體（226–232 行），不加
   `#view-result` 前綴。**
   理由：現況確認已證實此 class 僅被 view-result 與 view-history-detail 共用（非全站），
   AC2 本身也明講「shared ONLY by view-result and view-history-detail → modify the
   shared body」，改本體時兩頁同時受影響是預期行為（已於 AC 揭露、非本票意外副作用）。
   ```css
   .meeting-info-grid {
     display: grid;
     grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
     gap: var(--ds-space-4);
   }
   .meeting-info-grid label {
     display: flex; flex-direction: column; gap: 4px;
     font-family: var(--ds-font-sans);
     font-size: 13px; line-height: 18px; font-weight: 400;  /* tokens.json Body.caption */
     color: var(--ds-text-secondary);
   }
   .meeting-info-grid input {
     height: var(--ds-control-h-desktop);
     padding: 0 12px;
     border: 1px solid var(--ds-border-strong);
     border-radius: var(--ds-radius-sm);
     background: var(--ds-surface);
     color: var(--ds-text-primary);
     font-family: var(--ds-font-sans);
     font-size: 14px;
     box-sizing: border-box;
   }
   .meeting-info-grid input::placeholder { color: var(--ds-text-placeholder); }
   .meeting-info-grid input:focus-visible { outline: 2px solid var(--ds-focus-ring); outline-offset: 2px; }
   @media (max-width: 479px) {
     .meeting-info-grid { grid-template-columns: 1fr; gap: var(--ds-space-3); }
     .meeting-info-grid label { font-size: 12px; line-height: 16px; }  /* Body.caption-mobile */
     .meeting-info-grid input { height: var(--ds-control-h-mobile); width: 100%; }
   }
   ```
   - `gap` 選單一 token `--ds-space-4`（而非保留原本 row/column 各異的 `12px 16px`）：
     `docs/design-system/README.md` 間距表明講 `space-4`「欄位群組（如日期／時間／地點）
     間距」——與本元件的四個欄位（日期/時間/地點/參與者）用途完全對應，是唯一精確命中的
     既有 token，因此兩軸統一用同一值，不額外拆分 row/column，維持簡潔可預期。
   - `input` 的 `font-family`/`font-size`/`color`/`background` 對照既有 `.input` class
     （204–220 行，SDLCAIP2-44 已建立但目前未套用到任何現有元素）：AC2 條文未逐字列出這四項，
     但既然要把 input 改成與既有 design-system input 元件同一視覺語言（邊框/圓角/高度/
     placeholder/focus 皆已明講對照 `.input`），若唯獨字體/顏色/底色不跟進會產生「一半是
     design-system、一半是舊樣式」的不一致外觀，判斷屬於落實 AC2 意圖的必要延伸而非另立
     產品決策，因此一併套用，與 SDLCAIP2-45 決策 1（AC 只列顏色但一併補上 `font-family`）
     的判斷基準一致。

3. **AC3：`#summary-text` 改用 Body `body`/`body-mobile` token，`contenteditable` 提示色改
   `--ds-focus-ring`（外框）+ `--ds-badge-bg`（底色）。**
   ```css
   #summary-text {
     font-family: var(--ds-font-sans);
     font-size: 15px; line-height: 28px; font-weight: 400;  /* tokens.json Body.body */
     color: var(--ds-text-primary);
     min-height: 48px;
   }
   #summary-text[contenteditable="true"] {
     outline: 2px solid var(--ds-focus-ring);
     border-radius: var(--ds-radius-sm);
     padding: 4px 8px;
     background: var(--ds-badge-bg);
   }
   @media (max-width: 479px) {
     #summary-text { font-size: 14px; line-height: 26px; }  /* Body.body-mobile */
   }
   ```
   `contenteditable` 外框選 `--ds-focus-ring`：與 AC2 `.meeting-info-grid input` 的
   focus-visible 用同一 token，讓「進入編輯狀態」在全站呈現一致的視覺語言（既有
   `.input:focus-visible` 前例）。底色選 `--ds-badge-bg`（中性淺灰）取代原本
   `#EFF6FF`（淺藍）：呼應 SDLCAIP2-44 全站把強調色改為灰階中性色的既定方向（例如
   `.section-title .badge` 已從藍色改為 `--ds-badge-bg`），編輯提示不需要用品牌藍色強調。

4. **AC4：`#view-result .action-table th/td` 比照 SDLCAIP2-45 對 `#view-admin` 已建立的
   範圍限定模式，數值完全一致（同一元件、同一語意）。**
   ```css
   #view-result .action-table th {
     background: var(--ds-badge-bg);
     color: var(--ds-text-secondary);
     border-bottom: 1px solid var(--ds-border);
     font-family: var(--ds-font-sans);
     font-size: 13px;
   }
   #view-result .action-table td {
     color: var(--ds-text-primary);
     border-bottom: 1px solid var(--ds-border);
     font-family: var(--ds-font-sans);
     font-size: 13px;
   }
   ```
   理由不重複推導（見 SDLCAIP2-45 決策 1、SDLCAIP2-50 決策 1 已定案的同一組理由：共用本體
   跨頁使用不能直接改、`13px` 對照 `tokens.json` Body.caption、選取器特異性足夠覆寫）——
   三頁（view-admin／view-history／view-result）使用同一張表格元件，數值一致是刻意的
   「同元件同外觀」，並非巧合。`td[contenteditable="true"]` 的黃色編輯樣式（244 行）在
   view-result 確實會被觸發（AC8 明講待辦事項可雙擊編輯），AC4 未要求變更此規則，維持共用
   本體現況不動。

5. **AC5：`.decision-list` 直接改共用本體（273–277 行），套用 Body `body` token；未新增
   手機版變體。**
   ```css
   .decision-list li {
     padding: 8px 0;
     border-bottom: 1px solid var(--ds-border);
     display: flex; align-items: flex-start; gap: 10px;
     font-family: var(--ds-font-sans);
     font-size: 15px; line-height: 28px; font-weight: 400;  /* tokens.json Body.body */
   }
   .decision-list li:last-child { border-bottom: none; }
   .decision-list li::before { content: "✓"; color: var(--ds-text-primary); font-weight: 700; flex-shrink: 0; }
   ```
   AC5 條文僅提及「font → body token」，未像 AC1/AC2/AC3 一樣額外提及手機版對應 token，
   因此本票不另加 `body-mobile` media query，避免自行擴大規格；`body`（15/28px）在手機
   寬度下仍可正常換行顯示，不影響可用性。改共用本體的理由與 AC2 相同：現況確認已證實
   `.decision-list` 僅 view-result／view-history-detail 共用，非全站共用，AC5 條文也明講
   「shared only with view-history-detail」。

6. **AC6：`.topic-item`/`.topic-header`/`.topic-body` 直接改共用本體（279–286 行），hover
   底色選 `--ds-border`。**
   ```css
   .topic-item { border: 1px solid var(--ds-border); border-radius: 8px; margin-bottom: 10px; overflow: hidden; }
   .topic-header {
     padding: 12px 16px; cursor: pointer; font-weight: 500;
     display: flex; justify-content: space-between;
     background: var(--ds-badge-bg);
     color: var(--ds-text-primary);
   }
   .topic-header:hover { background: var(--ds-border); }
   .topic-body {
     padding: 12px 16px; font-size: .875rem; line-height: 1.6; display: none;
     color: var(--ds-text-secondary);
     font-family: var(--ds-font-sans);
   }
   .topic-body.open { display: block; }
   ```
   hover 選 `--ds-border`（#E4E3DF）而非再拿 `--ds-badge-bg`（#EFEEEA，與 header 底色相同、
   hover 會沒有視覺變化）或 `--ds-border-strong`（#D2D0CA，該 token 既有慣例保留給輸入框
   邊框，見 AC2/`.input`）：`--ds-border` 是灰階色階中僅次於 `--ds-badge-bg` 的下一階，能
   提供可辨識但依然中性、克制的 hover 回饋，符合 AC6「a `--ds-*` grayscale token」的要求。
   `.topic-body` 的 `font-size`（`.875rem`）AC6 未要求變更，維持原值不動，只改文字色與
   `font-family`。`toggleTopic()`（1309–1314 行）僅操作 `.open` class 與箭頭文字，未受影響。

7. **AC7：手機版（<480px）沿用 SDLCAIP2-45/50 已定案的「捲動容器」策略：`#action-tbody` 所在
   `<table class="action-table">` 外包 `.ds-table-scroll`（既有全站共用 class，第 268 行，
   不需新增），並在 `#view-result` 範圍內於手機斷點給 `.action-table` 一個 `min-width`。**
   ```html
   <div class="ds-table-scroll">
     <table class="action-table">
       <thead><tr><th>負責人</th><th>工作事項</th><th>截止時間</th></tr></thead>
       <tbody id="action-tbody"></tbody>
     </table>
   </div>
   ```
   ```css
   @media (max-width: 479px) {
     #view-result .action-table { min-width: 500px; }
   }
   ```
   `min-width: 500px` 推算（比照 SDLCAIP2-45/50 同一估算方式，非精確科學數字，developer
   實測後如需 ±30px 微調不需回頭改設計文件）：三欄中「工作事項」欄需容納一句描述性文字，
   抓 ~260px 可讀下限；「負責人」欄抓 ~100px（通常 2–4 個中文字姓名）；「截止時間」欄為
   日期/時間格式字串，抓 ~140px。三欄加總取整為 500px。現況確認已證實 `#action-tbody` 上
   無任何 `<table>` 層級的 `style.display` 切換邏輯，包 wrapper 不影響 `renderMinutes()`
   行為，AC8 不受影響。

8. **AC8（編輯/儲存 JS 行為不變）不需要任何 JS 程式碼變更，本設計文件把它列為回歸斷言，而非
   待實作項目。**
   理由：本票所有變更皆為 CSS 規則調整 + 一層純展示用的 HTML wrapper（決策 7），未新增/
   刪除/更名任何 `id`/`class`，`renderMinutes()`/`enableEdit`/`disableEdit`/
   `markModified()`/`toggleTopic()` 皆以既有 `id` 操作、不依賴 DOM 結構層級，已於現況確認
   段落逐一核對。測試階段應針對此點寫「維持現狀」的回歸驗證。

### 最終數值總表（供 SDLCAIP2-58 直接查表複製，不需重新推導）

| 選取器 | 屬性 | 桌面值 | 手機值（<480px） |
|---|---|---|---|
| `#view-result .section-title` | font-size | `18px` | `17px` |
| `#view-result .section-title` | line-height | `26px` | `24px` |
| `#view-result .section-title` | font-weight | `600` | `600`（不變） |
| `#view-result .section-title` | color | `var(--ds-text-primary)` | 不變 |
| `#view-result .action-table th` | background | `var(--ds-badge-bg)` | 不變 |
| `#view-result .action-table th` | color | `var(--ds-text-secondary)` | 不變 |
| `#view-result .action-table th` | border-bottom | `1px solid var(--ds-border)` | 不變 |
| `#view-result .action-table th` | font-family | `var(--ds-font-sans)` | 不變 |
| `#view-result .action-table th` | font-size | `13px` | 不變 |
| `#view-result .action-table td` | color | `var(--ds-text-primary)` | 不變 |
| `#view-result .action-table td` | border-bottom | `1px solid var(--ds-border)` | 不變 |
| `#view-result .action-table td` | font-family | `var(--ds-font-sans)` | 不變 |
| `#view-result .action-table td` | font-size | `13px` | 不變 |

## UI 原型

`docs/design/SDLCAIP2-55-prototype.html` —— 可直接在瀏覽器開啟的靜態原型，重現
`#view-result` 「會議紀錄」分頁五張卡片（會議資訊／摘要／待辦事項／決定事項／討論重點），
套用上述決策 1–7 的具體 CSS，並提供桌面寬度（900px 容器）與手機寬度（360px 容器，模擬
<480px 斷點）並排的 before/after 對照。原型另附一個小區塊，示範 `.meeting-info-grid`／
`.decision-list`／`.topic-item` 這三個與 view-history-detail 共用的元件在改動後的實際樣貌
（決策 2/5/6，說明變更會同步套用到 view-history-detail，此為預期行為、AC 已明講）。也可
另外用瀏覽器 DevTools 縮窄視窗驗證真實斷點行為。

## 開放設計問題（定稿時必須為空）

無。`.action-table`/`.section-title` 的範圍隔離 vs. `.meeting-info-grid`/`.decision-list`/
`.topic-item` 的共用本體直接修改（決策 1–2、5–6）、字級/行高 token 對照（決策 1–3，依
`tokens.json` Heading/Body 群組）、`contenteditable` 提示色選用（決策 3）、hover 灰階 token
選用（決策 6）、手機表格技術與 `min-width` 數值（決策 7）、AC8 的回歸性質（決策 8），皆已
依現有規格、程式碼現況、以及 SDLCAIP2-44/45/50 已定案的同類決策明確解決並附理由，未留待
developer 或後續工單自行決定。
