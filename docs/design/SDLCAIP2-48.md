# 設計文件 — SDLCAIP2-48 Design System｜歷史紀錄詳情頁 view-history-detail

## 對應需求規格

`docs/PRD.md`（G1 已核准版本）中 SDLCAIP2-48 段落，共 8 個 AC，涵蓋
`#view-history-detail`（`src/frontend/index.html`，目前約第 564–629 行）整頁：標題列按鈕
文字（AC1）、Tabs 按鈕文字（AC2）、`.section-title` 範圍限定覆寫（AC3）、`.action-table`
範圍限定覆寫（AC4）、`.empty-state` 範圍限定覆寫（AC5）、標題列 `gap` token 化（AC6）、
`.tabs`/`.meeting-info-grid`/`.decision-list`/`.topic-*` 一旦 SDLCAIP2-54/55 併入後與
view-result 一致（AC7，回歸斷言，本票不變更）、`openMeetingDetail()`/編輯/儲存/返回等 JS
行為不變（AC8，回歸斷言）。

**依賴聲明：開發必須等 SDLCAIP2-55 併入 main 後才能開始。** 理由見現況確認與決策 3/4：
`.meeting-info-grid`／`.decision-list`／`.topic-*` 的共用本體 token 化由 55 負責（55 決策
2/5/6 明講這兩頁共用、直接改共用本體），`#view-result .section-title`／`.action-table`
的前綴隔離規則亦由 55 先建立範例；本票 AC3/AC4 的最終數值須與 55 一致（55 文件末尾已附
「最終數值總表」供本票直接查表複製），若在 55 併入前開發，開發者會缺乏比對基準、且共用本體
可能在 55 併入時被覆蓋，故列為依賴。

## 現況確認（讀碼結果，供後續章節引用）

- `src/frontend/index.html` 第 564–629 行為目前 `#view-history-detail` 完整結構（行號為本次
  讀碼結果，早於 spec 文字所引用的舊行號；後續實作請以 id 定位，不要依賴行號）：
  - 第 566–574 行：標題列 `<div style="display:flex;...;gap:10px;">`，內含 `<h2
    id="history-detail-title">` 與 `.btn-row`（`#history-edit-btn` "✏️ 編輯"、
    `#history-save-btn` "💾 儲存"、`#history-cancel-btn` "取消"、無 id 的「← 返回歷史列表」
    按鈕）。
  - 第 576–579 行：`#history-detail-error`（`class="empty-state"`）。
  - 第 583–596 行：`.meeting-info-grid`（與 `#view-result` 共用同一 class，55 決策 2 直接改
    共用本體）。
  - 第 598–601 行：`.tabs` 內 `#history-tab-btn-minutes`（"📝 會議紀錄"）、
    `#history-tab-btn-transcript`（"🎙 逐字稿"）。
  - 第 602–622 行：`#history-tab-minutes` 內四張 `.card`（摘要 / 待辦事項 / 決定事項 /
    討論重點），其中待辦事項表格（第 609–612 行）**目前沒有 `.ds-table-scroll` wrapper**
    （與 view-result／view-admin／view-history 不同，這三頁已在各自工單補上），AC4 要求
    「reuse `.ds-table-scroll` + min-width like 55」，本票需補上此 wrapper。
    `.decision-list`（616 行）、`.topic-*`（620 行渲染於 `renderMinutesReadOnly()`）皆與
    `#view-result` 共用同一 class。
- `enableHistoryEditMode()`（917–939 行）/`cancelHistoryEdit()`（941–946 行）/
  `saveHistoryEdit()`（977–1008 行）：`saveHistoryEdit()` 第 981–982 行
  `const btn = document.getElementById('history-save-btn'); const originalText =
  btn.textContent;`，第 1006 行 `btn.textContent = originalText;`——**已逐行確認**
  `saveHistoryEdit()` 以 `textContent` 讀取並在 `finally` 區塊還原按鈕文字，與按鈕文字內容
  本身無關（不論文字是否含 emoji 皆會被完整還原），因此 AC1 只需改 HTML 中的靜態文字，JS
  不需變更。
- `switchHistoryTab()`（1060–1065 行）：以 `document.getElementById('history-tab-btn-minutes'
  /'-transcript')` 操作 `classList.toggle('active', ...)`，與按鈕內文字內容無關，AC2 只需改
  HTML 靜態文字，JS 不需變更。
- `renderMinutesReadOnly()`（1010–1051 行）：討論重點為空時第 1034 行寫入
  `tc.innerHTML = '<div class="empty-state"><p>無討論重點</p></div>'`；`#history-detail-error`
  （576 行）亦為 `.empty-state`。AC5 明講兩者皆須套用，選取器 `#view-history-detail
  .empty-state` 可同時涵蓋兩處（皆在 `#view-history-detail` 容器內），不需個別選取器。
- `openMeetingDetail()`（859–882 行）：成功路徑呼叫 `renderMinutesReadOnly(data)` +
  `renderHistoryMeetingInfo(data)`；404／例外路徑切換 `#history-detail-body`/
  `#history-detail-error` 的 `style.display`。皆以 id 操作，未依賴任何本票會變更的 DOM
  結構（新增 `.ds-table-scroll` wrapper 是純展示用外層 `<div>`，不影響 `#history-action-tbody`
  的 `getElementById`），AC8 不受影響。
- `.tabs`/`.tab`/`.tab.active`（第 178–182 行）目前仍是舊版 token（`var(--border)`/
  `var(--muted)`/`var(--primary)`），尚未被 SDLCAIP2-54 token 化；`.meeting-info-grid`
  （225–231 行）、`.decision-list`（291–295 行）、`.topic-item`/`.topic-header`
  （297 行起）亦皆為舊版樣式，尚未被 SDLCAIP2-55 token 化——與任務說明一致，55/54 尚未併入
  main。`.action-table`（237–243 行）、`.empty-state`（341 行）本體皆為全站共用，已被
  `#view-admin`/`#view-history` 前綴覆寫（245–289 行）但尚無 `#view-history-detail`
  前綴規則。`.section-title` 本體（185–186 行）亦尚未被任何前綴規則覆寫成 h2 token（55 尚未
  併入）。
- `docs/design/SDLCAIP2-54.md` 在目前工作目錄與 git 歷史中皆不存在（僅
  `SDLCAIP2-46/47/50/55` 等設計文件存在），也不在 `docs/design/*` glob 結果中，無法讀取其
  ripple 相關決策內容。**本文件的 AC7 因此僅依任務提供的 spec 文字描述為「回歸斷言、本票不
  變更」處理，不引用 54 的任何具體實作細節**（見開放設計問題章節說明此點不影響本票定稿）。
- `:root`（第 11–49 行）逐一核對本文件下方所有 `--ds-*` 引用皆存在：`--ds-space-2`（43 行）、
  `--ds-text-primary`（30 行）、`--ds-text-secondary`（31 行）、`--ds-badge-bg`（37 行）、
  `--ds-border`（28 行）、`--ds-font-sans`（41 行）。均已於 `:root` 定義，不需新增變數。

## 介面/API 契約

無，本 Story 不涉及對外 API 變更。純前端靜態資源（HTML/CSS）調整，`src/frontend` 無建置
流程，不產生任何新的後端端點或請求/回應格式；`openMeetingDetail()`／
`enableHistoryEditMode()`／`cancelHistoryEdit()`／`saveHistoryEdit()`／
`switchHistoryTab()`／`renderMinutesReadOnly()`（含 `PATCH /api/meetings/{id}`）的邏輯不變動。

## 資料模型

無新增資料模型。

## 選取器 → 屬性 → 舊值 → 新值對照表

| 選取器 | 屬性 | 舊值 | 新值 |
|---|---|---|---|
| `#history-edit-btn` | textContent | `✏️ 編輯` | `編輯` |
| `#history-save-btn` | textContent | `💾 儲存` | `儲存` |
| `#history-cancel-btn` | textContent | `取消` | 不變 |
| 返回按鈕（無 id） | textContent | `← 返回歷史列表` | 不變 |
| `#history-tab-btn-minutes` | textContent | `📝 會議紀錄` | `會議紀錄` |
| `#history-tab-btn-transcript` | textContent | `🎙 逐字稿` | `逐字稿` |
| 標題列外層 `<div>`（564 行下、無 id） | `style` 中 `gap` | `10px`（inline） | `var(--ds-space-2)`（inline） |
| `#view-history-detail .section-title`（新增規則） | font-size / line-height / font-weight / color | 繼承共用本體 `1rem`/預設/`600`/`var(--text)` | `18px`/`26px`/`600`/`var(--ds-text-primary)`（桌面）；`17px`/`24px`（<480px） |
| `#view-history-detail .action-table th`（新增規則） | background / color / border-bottom / font-family / font-size | 繼承共用本體 `var(--bg)`/`var(--muted)`/`var(--border)`/預設/`.8rem` | `var(--ds-badge-bg)`/`var(--ds-text-secondary)`/`1px solid var(--ds-border)`/`var(--ds-font-sans)`/`13px` |
| `#view-history-detail .action-table td`（新增規則） | color / border-bottom / font-family / font-size | 繼承共用本體 `var(--text)`（未設）/`var(--border)`/預設/`.875rem` | `var(--ds-text-primary)`/`1px solid var(--ds-border)`/`var(--ds-font-sans)`/`13px` |
| `#view-history-detail .empty-state`（新增規則） | color | 繼承共用本體 `var(--muted)` | `var(--ds-text-secondary)` |
| 第 609–612 行 `<table class="action-table">`（待辦事項） | HTML 結構 | 無 wrapper | 外包 `<div class="ds-table-scroll">`（既有全站共用 class，不需新增） |
| `#view-history-detail .action-table`（新增，僅 <480px） | min-width | 無 | `500px`（比照 55 對 view-result 的估算，欄位語意相同） |

## 關鍵技術決策

1. **AC1/AC2：純 HTML 文字內容變更，不涉及 CSS 或 JS。**
   理由：現況確認已逐行核對 `saveHistoryEdit()`（981–982、1006 行）以 `textContent`
   讀取並還原按鈕文字，`switchHistoryTab()`（1060–1065 行）以 id 操作
   `classList.toggle('active', ...)`，兩者皆與按鈕文字內容本身無關，移除 emoji 後行為不變。

2. **AC3/AC4：一律用 `#view-history-detail` 前綴覆寫規則，不修改 `.section-title`/
   `.action-table` 共用本體，數值與 SDLCAIP2-55 對 `#view-result` 的規則完全一致（照抄
   55 文件末尾「最終數值總表」）。**
   ```css
   #view-history-detail .section-title {
     font-size: 18px;   /* tokens.json Heading.h2 */
     line-height: 26px;
     font-weight: 600;
     color: var(--ds-text-primary);
   }
   @media (max-width: 479px) {
     #view-history-detail .section-title {
       font-size: 17px;  /* tokens.json Heading.h2-mobile */
       line-height: 24px;
     }
   }
   #view-history-detail .action-table th {
     background: var(--ds-badge-bg);
     color: var(--ds-text-secondary);
     border-bottom: 1px solid var(--ds-border);
     font-family: var(--ds-font-sans);
     font-size: 13px;
   }
   #view-history-detail .action-table td {
     color: var(--ds-text-primary);
     border-bottom: 1px solid var(--ds-border);
     font-family: var(--ds-font-sans);
     font-size: 13px;
   }
   ```
   理由：`.section-title`/`.action-table` 為全站共用（另被 view-admin/view-history/
   view-result 使用），改共用本體會破壞其他頁面（範圍外明講）；`#id .class`（0,1,1）特異性
   高於 `.class`（0,1,0），可直接覆寫不需 `!important`。與 view-result 用同一數值：兩頁本來
   就渲染同一組「會議資訊/摘要/待辦事項/決定事項/討論重點」語意資料，SDLCAIP2-58 的人類決議
   已明講兩頁最終要一致，維持「同元件同外觀」而非各自另訂一套數值。

3. **AC4 手機版沿用 55/45/50 已定案的「捲動容器」策略：待辦事項 `<table>` 外包既有全站共用
   `.ds-table-scroll`（不需新增 class），並在 `#view-history-detail` 範圍給 `min-width`。**
   ```html
   <div class="ds-table-scroll">
     <table class="action-table">
       <thead><tr><th>負責人</th><th>工作事項</th><th>截止時間</th></tr></thead>
       <tbody id="history-action-tbody"></tbody>
     </table>
   </div>
   ```
   ```css
   @media (max-width: 479px) {
     #view-history-detail .action-table { min-width: 500px; }
   }
   ```
   `min-width: 500px` 直接沿用 55 對 `#view-result` 的推算值（不重新推導）：兩頁待辦事項表格
   三欄（負責人／工作事項／截止時間）語意與資料形狀完全相同，理應撐開同一個可讀下限。現況
   確認已核對 `renderMinutesReadOnly()`（1010–1051 行）僅以
   `document.getElementById('history-action-tbody')` 操作 `tbody.innerHTML`，未對
   `<table>` 本身做任何 `style.display` 切換，包 wrapper 不影響此函式，AC8 不受影響。

4. **AC5：`#view-history-detail .empty-state` 用同一條規則同時涵蓋
   `#history-detail-error` 與 `renderMinutesReadOnly()` 渲染出的討論重點空清單，不需要
   兩條選取器。**
   ```css
   #view-history-detail .empty-state {
     color: var(--ds-text-secondary);
   }
   ```
   理由：兩者皆位於 `#view-history-detail` 容器內（576 行 error 區塊、620/1034 行討論重點
   容器），單一前綴選取器即可命中，不需分別處理；顏色選 `--ds-text-secondary`
   沿用 SDLCAIP2-50 決策 3 已定案的「次要提示文字 → secondary token」慣例，與 55 對
   view-result 空清單（若有）維持一致語意。

5. **AC6：標題列 `gap:10px`（inline style）改 `gap:var(--ds-space-2)`（inline style），
   不抽成 class。**
   理由：spec 明講只改這一個 inline 屬性；`--ds-space-2` = `12px`，是既有
   token 中最接近原始 `10px` 的值（`--ds-space-1`=8px 過近、`--ds-space-3`=16px 差距較大），
   維持視覺變動最小化，與 AC6 條文「gap:10px → var(--ds-space-2)」逐字對應，不另行評估其他
   token。此區塊目前仍是行內 `style`（非獨立 CSS 規則），本票延續同一寫法，僅改動這一個
   屬性值，不重構成獨立選取器（重構不在本 AC 範圍內）。

6. **AC7（`.tabs`/`.meeting-info-grid`/`.decision-list`/`.topic-*` 一旦 54/55 併入後與
   view-result 一致）列為回歸斷言，本票不新增/變更任何相關 CSS 規則。**
   理由：現況確認已證實 `.meeting-info-grid`/`.decision-list`/`.topic-*` 為
   view-result/view-history-detail 共用 class（55 決策 2/5/6 直接改共用本體，兩頁自動同步
   套用），`.tabs`/`.tab` 為全站共用 class（54 負責，範圍未知但同屬共用本體模式）；只要 55/54
   依各自設計文件改動共用本體，`#view-history-detail` 內同 class 的元素會自動繼承新樣式，
   不需要本票另寫任何 `#view-history-detail` 前綴規則。測試階段應在 55（與 54，若可取得）
   併入後，針對本票做「電腦運算樣式與 view-result 一致」的回歸驗證，而非在本票開發時新增
   實作。

7. **AC8（編輯/儲存/返回等 JS 行為不變）不需要任何 JS 程式碼變更，列為回歸斷言。**
   理由：本票所有變更皆為 CSS 規則新增（決策 2/3/4）+ HTML 文字內容變更（決策 1）+ 一層純
   展示用 wrapper（決策 3）+ 一個 inline style 屬性值（決策 5），未新增/刪除/更名任何
   `id`/`class`，`openMeetingDetail()`/`enableHistoryEditMode()`/`cancelHistoryEdit()`/
   `saveHistoryEdit()`/`switchHistoryTab()`/`renderMinutesReadOnly()` 皆以既有 id 操作、
   不依賴 DOM 結構層級，已於現況確認段落逐一核對。測試階段應針對此點寫「維持現狀」的回歸
   驗證。

## UI 原型

`docs/design/SDLCAIP2-48-prototype.html` —— 可直接在瀏覽器開啟的靜態原型，重現
`#view-history-detail` 整頁：標題列（返回/編輯/儲存/取消按鈕，含 gap token 化）、Tabs、
會議資訊卡、摘要、待辦事項表格（含捲動 wrapper）、決定事項、討論重點，以及
`#history-detail-error` 錯誤狀態與討論重點空清單狀態，套用上述決策 1–5 的具體 CSS。原型提供
桌面寬度（900px 容器）與手機寬度（360px 容器，模擬 <480px 斷點）並排的 before/after 對照，
並各附一組「空清單/錯誤狀態」畫面。原型中的 `.tabs`/`.meeting-info-grid`/`.decision-list`/
`.topic-item` 維持目前 main 分支上的舊版樣式（決策 6 說明：這些由 54/55 併入後才會自動改變，
本票不改動，原型如實呈現這個「部分 token 化」的過渡狀態，不假裝 54/55 已完成）。也可另外用
瀏覽器 DevTools 縮窄視窗驗證真實斷點行為。

## 開放設計問題（定稿時必須為空）

無。`docs/design/SDLCAIP2-54.md` 在目前程式碼庫中不存在（任務說明已預告此可能性並指示
「若不存在，依 spec 文字描述 AC7」），本文件已依此指示將 AC7 處理為純回歸斷言、不引用 54
任何未經確認的實作細節，不影響本票其餘 AC 的定案，因此不視為需要人類介入的開放問題。
`.section-title`/`.action-table` 的前綴隔離 vs. `.empty-state` 前綴隔離（決策 2/4）、
`gap` token 選用（決策 5）、待辦事項表格 `min-width` 數值沿用（決策 3）、AC7/AC8 的回歸性質
（決策 6/7），皆已依現有規格、程式碼現況、以及 SDLCAIP2-45/50/55 已定案的同類決策明確解決
並附理由，未留待 developer 或後續工單自行決定。
