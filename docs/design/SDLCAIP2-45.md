# 設計文件 — SDLCAIP2-45 Design System｜管理者儀表板頁 view-admin

## 對應需求規格

`docs/PRD.md` 的 `## SDLCAIP2-45` 段落（G1 已核准版本），共 6 個 Gherkin scenario：`.card`
沿用 SDLCAIP2-44 既有 token（回歸檢查）、`.action-table` 在 view-admin 範圍內改用 `--ds-*`
token 但不得修改共用 class 本體、`<h4>依日期</h4>`／`<h4>依使用者</h4>` 套用 design-system
字體 token、表格在手機（<480px）不得橫向撐破版面、無裝飾性 icon（回歸檢查）、範圍外頁面
（view-upload/progress/result/history）不得有非預期視覺變化。

## 現況確認（讀碼結果，供後續章節引用）

- `src/frontend/index.html` 第 331–346 行：`#view-admin` 只有一個 `.card`，內含
  `.section-title`（含返回按鈕）+ 兩組「`<h4>` + `<table class="action-table">`」（依日期／
  依使用者，`tbody` id 分別為 `admin-by-date-tbody`／`admin-by-user-tbody`），無任何 icon。
- 第 238–244 行：`.action-table` 共用 class 定義，目前用舊版 `--bg`/`--border`/`--muted`
  變數（非 `--ds-*`），且第 469、504、560 行確認同一個 class 也被 view-result（待辦事項表）與
  view-history（歷史列表表）使用——證實它是真正跨頁共用的 class，不能整包改掉。
- 第 11–48 行 `:root`：SDLCAIP2-44 已加入完整 `--ds-*` token（顏色、字體家族、`space-1~8`、
  `radius-sm/md/pill`、`control-h-*`、`header-h-*`、`container-max`、`breakpoint-mobile: 480px`）。
  **但這組 token 目前只有 `--ds-font-sans`/`--ds-font-mono`（字體家族），沒有字級/字重/行高的
  CSS 變數**——`tokens.json` 的 `type.groups`（Heading/Body/Mono）數值目前是以文件形式存在，
  尚未被搬進 `index.html` 的 `:root`。本票沿用 SDLCAIP2-44 已建立的模式，直接把需要的具體數值
  寫進新規則（如 `.btn`/`.input` 現有做法：`font-size: 14px; font-weight: 500;` 直接寫死，
  未定義成獨立 CSS 變數），不在本票額外新增字級 token 變數（範圍外，見決策 2）。
- `docs/design-system/tokens.json` 的 `type.groups` 只有 Heading（h1/h1-mobile/h2/h2-mobile）、
  Body（body/body-mobile/caption/caption-mobile/label-button）、Mono 三組，**沒有 h3/h4 這個
  層級**。`.section-title`（例如「LLM 用量與成本彙總」）在 view-admin 目前語意上相當於卡片內的
  一級標題，但本票 AC3 明確只針對 `<h4>依日期</h4>`／`<h4>依使用者</h4>` 這兩個表格前的子標題，
  `.section-title` 本身的字體 token 化不在本票規格內，維持現狀不動。
- `docs/design-system/README.md`「RWD 規則」表格目前沒有針對「表格」這個元件類型的手機版規格
  （只有頁首、工具列、多欄表單、控制項高度、卡片內距、長字串換行），且
  `docs/design-system/components/` 底下沒有 Table README——證實 AC4 的手機表格技術是本票需要
  自行決定、事後才回補進 design-system 的未收錄元件（README 第 68 行「請先依本文件規則自行組合，
  再回頭補進本系統」正是這個情境）。
- SDLCAIP2-44 header 手機版（第 82–93 行 `.header-secondary`）已用 `overflow-x: auto` 讓次要
  導覽在窄螢幕橫向捲動而不換行/不撐破版面——本票 AC4 沿用同一手法（見決策 3）。

## 介面/API 契約

無，本 Story 不涉及對外 API 變更。純前端靜態資源（HTML/CSS）調整，`src/frontend` 無建置流程，
不產生任何新的後端端點或請求/回應格式；`admin-by-date-tbody`/`admin-by-user-tbody` 的資料填入
邏輯（JS fetch/render）不變動。

## 資料模型

無新增資料模型。

## 關鍵技術決策

1. **`.action-table` 的 view-admin 專屬樣式一律用 `#view-admin .action-table th` /
   `#view-admin .action-table td` 這種「視圖 id 前綴」選取器覆寫，絕不修改第 238–244 行
   `.action-table`/`.action-table th`/`.action-table td` 本體規則。**
   理由：AC2 明講「僅限 view-admin 範圍內套用」，且共用本體同時被 view-result／view-history
   使用（見上方現況確認）；若直接改本體，AC9（範圍外頁面不得有非預期視覺變化）必破。CSS
   選取器特異性上 `#id .class` (0,1,1) 高於 `.class` (0,1,0)，可直接覆寫且不需要 `!important`。
   只覆寫「顏色/邊框/字體」這三類與 design-system 相關的屬性，`padding`/`border-collapse`/
   `tr:last-child` 等結構屬性維持繼承自共用本體，不重複定義：
   ```css
   #view-admin .action-table th {
     background: var(--ds-badge-bg);
     color: var(--ds-text-secondary);
     border-bottom: 1px solid var(--ds-border);
     font-family: var(--ds-font-sans);
     font-size: 13px;
   }
   #view-admin .action-table td {
     color: var(--ds-text-primary);
     border-bottom: 1px solid var(--ds-border);
     font-family: var(--ds-font-sans);
     font-size: 13px;
   }
   ```
   顏色對照：`th` 背景改用 `--ds-badge-bg`（design-system 對「安靜的標籤/表頭底色」的既有用途，
   見 `docs/design-system/README.md` 色彩表 `badge-bg` 說明），文字改用 `--ds-text-secondary`
   （次要文字色，符合表頭在灰階系統裡的次要層級）；邊框統一改 `--ds-border`；字級選用
   `tokens.json` Body 群組的 `caption`（13px/18px/400），因為 13px 最貼近共用本體現有的
   `.8rem`（≈12.8px）視覺密度，且 caption 的語意（「欄位標籤、次要說明文字」）與表格資料列的
   資訊密度相符，`body`（15px）在多欄表格會顯得過鬆。`td[contenteditable="true"]` 的黃色
   編輯狀態樣式（`#FEFCE8`/`--warning`）在 view-admin 未被使用（此頁表格唯讀），不需處理，
   維持共用本體定義即可。

2. **不新增獨立的字級/字重 CSS 變數（如 `--ds-font-size-caption`），沿用 SDLCAIP2-44 的既有
   做法：具體數值直接寫在規則裡，並在旁邊註解標明對應 `tokens.json` 的哪個 style 條目。**
   理由：目前 `:root` 的 `--ds-*` 集合刻意只涵蓋顏色/間距/圓角/尺寸/字體家族（決策依據見
   SDLCAIP2-44 設計文件決策 1），字級細節目前全部用行內數值（`.btn`/`.input` 皆是如此）；
   本票延續同一慣例以維持一致性，是否要把 `type.groups` 全部搬成 CSS 變數是更大範圍的
   design-system 基礎建設決策，不屬於本票（單一頁面套用）的範圍，也不應該在這裡臨時擴大。

3. **`<h4>依日期</h4>` / `<h4>依使用者</h4>` 套用 `tokens.json` Body 群組的 `label-button`
   樣式（14px/20px/字重 500），而非 Heading 群組的 `h2`。**
   理由：`tokens.json` 沒有 h3/h4 層級（見現況確認），必須從既有兩組（Heading／Body）裡選一個
   語意最接近的既有樣式，不能無中生有一組新字級。這兩個 `<h4>` 是「表格前的分類小標籤」，
   功能上更接近「短促、次要的標示文字」而非「章節標題」——卡片本身已經有 `.section-title`
   （視覺上等同卡片的 h2 標題），若 `<h4>` 也套用 `h2`（18px/600）會在同一張卡片內產生兩層
   看起來一樣重的標題，造成視覺層級混淆。`label-button`（14px/500）介於 `caption`（13px/400）
   與 `h2` 之間，粗細足以當作小節標籤、但明顯輕於卡片主標題，是最貼近語意的既有選項。
   `tokens.json` 沒有 `label-button` 的手機版尺寸（只有 Heading/Body 的 body/caption/h1/h2
   才有 `-mobile` 變體），因此手機版沿用同一數值，不另外寫 media query——這是 token 集合本身的
   既有限制，不是本票遺漏。
   ```css
   #view-admin h4 {
     font-family: var(--ds-font-sans);
     font-size: 14px;
     line-height: 20px;
     font-weight: 500;
     color: var(--ds-text-secondary);
     margin: var(--ds-space-3) 0 var(--ds-space-2);
   }
   ```
   顏色選 `--ds-text-secondary`（而非 `--ds-text-primary`）：呼應「小節標籤」語意，與
   `.section-title .badge`（同樣用 `--ds-text-secondary`/`--ds-badge-text`）的次要層級一致。
   間距選 `--ds-space-3`（16px，上）/`--ds-space-2`（12px，下）：對照
   `docs/design-system/README.md` 間距表「`space-2`：欄位 label 與輸入框的垂直間距」，
   `<h4>` 之於其後的表格，語意上正是「標籤之於其後內容」，直接沿用既有間距 token 的既有用途，
   不新創數值。

4. **手機版（<480px）表格不橫向撐破版面，採「捲動容器」策略：每個 `<table class="action-table">`
   外包一層新 class `.ds-table-scroll`（`overflow-x: auto`），並在 `#view-admin` 範圍內於手機
   斷點給 `.action-table` 一個 `min-width`，而不是讓欄位自動縮小硬塞。**
   理由：
   - 沿用 SDLCAIP2-44 header 次要導覽已驗證過的同一手法（`overflow-x: auto` 包一層容器），
     維持全站「遇到手機版塞不下的橫向內容，用捲動而非硬縮」的一致模式，不另外發明新技巧。
   - 表格與 header 導覽的差異：header 導覽的每個項目寬度可以不設下限（文字多短都行）；表格
     若不設 `min-width`，瀏覽器預設行為是把每欄硬擠到極窄，導致 AC4 真正要避免的「文字擠壓、
     內容看不清楚」問題——即使技術上沒有「橫向溢出頁面」，也違反可用性。因此額外加
     `min-width`，強制欄位保留可讀寬度，由捲動容器負責超出部分的橫向捲動，而不是讓表格本身
     溢出 `<body>`（後者才是真正會撐破版面／出現非預期頁面級橫向卷軸的情況）。
   - 新增 `.ds-table-scroll` 是全新 class，只用在本票新加的 wrapper `<div>` 上，不影響
     `.action-table` 本體或任何既有選取器，符合 AC2「不修改共用 class 本體」與 AC9（範圍外
     頁面不受影響）。
   ```css
   .ds-table-scroll { width: 100%; overflow-x: auto; }
   @media (max-width: 479px) {
     #view-admin .action-table { min-width: 560px; }
   }
   ```
   `min-width: 560px` 的推算：現有 5 欄（日期/使用者、呼叫次數、Input Tokens、Output Tokens、
   估算成本），每欄依現有 `padding: 10px 14px` 抓一個可讀下限（數字/日期欄約 90–130px），
   加總取整估算值；非精確科學數字，developer 實作時若實測後發現略需調整（例如 ±40px），
   在不影響「捲動而非硬縮」這個策略本身的前提下可自行微調，不需要回頭改設計文件。
   HTML 變更（僅 `#view-admin` 內兩個 `<table>`，結構/id 不變，只加一層 wrapper）：
   ```html
   <h4>依日期</h4>
   <div class="ds-table-scroll">
     <table class="action-table"> ... （原內容不變，含 tbody id="admin-by-date-tbody"） ... </table>
   </div>
   <h4>依使用者</h4>
   <div class="ds-table-scroll">
     <table class="action-table"> ... （原內容不變，含 tbody id="admin-by-user-tbody"） ... </table>
   </div>
   ```

5. **AC1（`.card` 沿用 SDLCAIP2-44 token）與 AC5（無裝飾性 icon）不需要任何程式碼變更，本設計
   文件把它們列為回歸斷言（regression assertion），而非待實作項目。**
   理由：`.card` 是 SDLCAIP2-44 已全站遷移的共用 class，view-admin 的 `.card` 本來就繼承該
   規則，未被本票任何選取器改動；view-admin 現有標記（第 331–346 行）本來就沒有任何 emoji/icon
   字元。測試階段應針對這兩點寫「維持現狀」的回歸驗證，不應誤解成需要新增樣式。

## UI 原型

`docs/design/SDLCAIP2-45-prototype.html` —— 可直接在瀏覽器開啟的靜態原型，重現 view-admin 的
`.card` + `.section-title` + 兩組「`<h4>` + 捲動包裝表格」結構，套用上述決策 1/3/4 的具體 CSS。
原型內同時提供「桌面寬度」（900px 容器）與「手機寬度」（360px 容器，模擬 <480px 斷點）兩個並排
預覽區塊，並列出對照說明（表頭底色／文字色 token 來源、`<h4>` 字級 token 來源、手機版捲動觸發
方式），讓人類在 G1b 審核時不必自行縮放瀏覽器視窗即可同時看到兩種版型；也可另外用瀏覽器
DevTools 縮窄視窗驗證真實斷點行為。

## 開放設計問題（定稿時必須為空）

無。`.action-table` 範圍隔離（決策 1）、字級 token 選用（決策 2/3）、手機表格技術（決策 4）、
AC1/AC5 的回歸性質（決策 5），皆已依現有規格與程式碼／design-system 文件明確解決並附理由，
未留待 developer 或後續工單自行決定。
