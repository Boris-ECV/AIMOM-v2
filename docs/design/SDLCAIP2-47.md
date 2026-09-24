# 設計文件 — SDLCAIP2-47 Design System｜上傳畫面 view-upload

## 對應需求規格

`docs/PRD.md` 的 `## SDLCAIP2-47` 段落（G1 已核准版本），共 8 個 Gherkin scenario：`#view-upload
.card` 沿用 SDLCAIP2-44 token（回歸）、`<h2>` 移除 emoji、`#drop-zone`／`#upload-btn` 內 `<svg>`
移除（僅留文字，disabled/reset 行為不變）、`#drop-zone` 邊框/圓角/hover/dragover 改用 `--ds-*`
token、`#file-info`／`.fname` 背景與文字色改用 `--ds-*` token、`#upload-btn` 延續全域
`.btn`/`.btn-primary`（回歸）、手機版（<480px）控制項高度/卡片內距沿用全域既有規則（回歸）、
其他畫面與 header 不受影響、`#upload-error` 維持 `var(--danger)`（回歸）。

## 現況確認（讀碼結果，供後續章節引用）

- `src/frontend/index.html` 第 380–404 行：`#view-upload` 只有一個 `.card`，內含 `<h2>📤 上傳
  錄音檔</h2>`、`#drop-zone`（含一個 `<svg>` + `<strong>` + `<p>`）、`#file-input`（`display:none`，
  不套 `.input`）、`#file-info`（含 `.fname` + `#file-meta`）、`#upload-btn`（`.btn.btn-primary`，
  含一個 `<svg>` + 文字「開始處理」）、`#upload-error`。
- 第 117–128 行：`#drop-zone` 現用 `var(--border)`（邊框色）、`var(--radius)`（圓角，10px）、
  hover/dragover 用 `var(--primary)`（邊框）+ `#EFF6FF`（背景）；`#drop-zone svg` 另有一條獨立
  規則（`width/height/color/margin-bottom`）；`#file-info` 背景 `#EFF6FF`；`.fname` 用
  `font-weight:600; color: var(--primary)`。
- 第 132–158 行：`.btn`/`.btn-primary`/`.btn:disabled` 已在 SDLCAIP2-44 改為 `--ds-*` token（含
  手機版 `height: var(--ds-control-h-mobile); width:100%`），`#upload-btn` 未額外覆寫任何屬性，
  直接繼承。
- 第 113–115 行：`.card` 手機版 `padding: var(--ds-space-5)` 已是 SDLCAIP2-44 全域規則，
  `#view-upload .card` 未被覆寫，直接繼承。
- JS 第 1089–1092 行 `doUpload()`：`btn.disabled = true; btn.textContent = '上傳中...'` ——
  用 `.textContent` 整段覆寫按鈕內容，移除 `<svg>` 後此行為不受影響（`.textContent` 本來就會
  連同 svg 子節點一併清掉，目前寫法與 svg 是否存在無關）。第 1627–1628 行 `resetState()` 同理，
  `disabled = true; textContent = '開始處理'`。確認 AC3「disabled/reset 行為不變」對程式碼零風險。
- 全檔案 grep 確認 `var(--primary)`/`#EFF6FF`/`var(--border)`/`var(--radius)` 在 `#drop-zone`／
  `#file-info`／`.fname` 之外，也被 `.stage-icon.active`（進度畫面）等**範圍外**選取器使用，
  本票僅針對 `#drop-zone`／`#file-info`／`.fname` 這三個選取器新增覆寫，不觸碰共用變數本身
  （與 SDLCAIP2-44 決策 1「不覆寫既有變數，只新增 `--ds-*` 前綴變數」一致，故不會影響範圍外畫面）。

## 介面/API 契約

無，本 Story 不涉及對外 API 變更。純前端靜態資源（HTML/CSS）調整，`src/frontend` 無建置流程，
不產生任何新的後端端點或請求/回應格式；`doUpload()`/`resetState()` 等既有 JS 邏輯不變動。

## 資料模型

無新增資料模型。

## 關鍵技術決策

1. **`#drop-zone`／`#file-info`／`.fname` 一律用選取器覆寫對應屬性的 `--ds-*` token，不修改
   `.card`/`.btn` 共用 class 本體，也不修改 `--border`/`--primary`/`--radius` 等既有變數本身。**
   理由：與 SDLCAIP2-45 決策 1 同一模式——這三個變數仍被範圍外選取器（如
   `.stage-icon.active`）使用，直接改變數值會違反 AC8（其他畫面不受影響）；改用「選取器覆寫
   單一屬性」只影響本票明確列出的目標。完整對照表：

   | 選取器 | 屬性 | 舊值 | 新值（`--ds-*`） | 理由 |
   | --- | --- | --- | --- | --- |
   | `#drop-zone` | `border-color`（含在 `border` 簡寫內） | `var(--border)` | `var(--ds-border-strong)` | `#drop-zone` 是可點擊的互動容器（等同「大型輸入框」），design-system 色彩表定義「`border`/`border-strong` 兩階：分隔線用淺、控制項邊框用深」，`.btn`/`.input` 皆用 `border-strong`，`#drop-zone` 屬控制項語意應比照 |
   | `#drop-zone` | `border-radius` | `var(--radius)`（10px） | `var(--ds-radius-md)`（10px） | 數值本來就與 `radius-md` 完全相同；`#drop-zone` 是卡片內的大型內容區塊而非按鈕/輸入框，語意上更接近 `radius-md`（卡片）而非 `radius-sm`（按鈕/輸入框），且恰好無視覺變化 |
   | `#drop-zone:hover`, `#drop-zone.dragover` | `border-color` | `var(--primary)` | `var(--ds-ink-100)` | design-system 無強調色（原則 1：灰階為主），`ink-100` 是 token 集合裡用於「主要按鈕、目前分頁」等互動/強調狀態的既有色階，語意上與「使用者正在拖放檔案」的主動互動狀態一致 |
   | `#drop-zone:hover`, `#drop-zone.dragover` | `background` | `#EFF6FF` | `var(--ds-badge-bg)` | `badge-bg` 是 token 集合裡既有的「安靜中性提示底色」，`.btn-outline:hover` 已用同一 token 表達「輕量互動反饋」，沿用同一語意避免新創一次性顏色 |
   | `#file-info` | `background` | `#EFF6FF` | `var(--ds-badge-bg)` | 與上一列同一 token、同一語意（提示區塊的中性底色），維持全站一致 |
   | `.fname` | `color` | `var(--primary)` | `var(--ds-text-primary)` | `.fname` 已有 `font-weight:600` 做強調，不需要再疊加「強調色」；`ink-*` 依 README 保留給「頁首、主要按鈕、目前分頁」，檔名標籤不屬於這類全站級強調元件，改用三階文字色中最深的 `text-primary` 即可達到強調效果，且符合「灰階為主」原則 |

   `#drop-zone p`（`color: var(--muted)`）、`#drop-zone strong`（`color: var(--text)`）、
   `padding`/`transition` 等結構屬性不在 AC4/AC5 列出的屬性範圍內，維持原樣不動。

2. **`#drop-zone svg { ... }`（現行第 122 行）在移除 `<svg>` 標記後成為死規則，本票明確一併刪除
   該條 CSS，不保留。**
   理由：AC3 明講移除 `#drop-zone` 內的 `<svg>`，該條規則的選取器（`#drop-zone svg`）之後永遠
   不會再命中任何元素；比照一般重構原則，被移除標記唯一引用的專屬樣式規則應隨標記一併清除，
   避免留下無法追蹤的死程式碼誤導未來的人。這與 SDLCAIP2-44 決策 7（移除 icon 只改按鈕文字，
   不改其餘邏輯）不衝突——SDLCAIP2-44 移除的是「文字前綴 emoji」，沒有對應的專屬 CSS 規則可清；
   本票移除的是有獨立 CSS 選取器的 `<svg>` 元素，情境不同，故明確決定一併刪除規則本身。
   `#upload-btn` 內的 `<svg>` 沒有專屬 CSS 選取器（樣式全部繼承 `.btn`/`.btn-primary`），移除
   標記後無對應死規則需要處理。

3. **AC1（`.card` 沿用 token）、AC6（`#upload-btn` 延續全域 `.btn`/`.btn-primary`）、AC7（手機版
   控制項高度/卡片內距沿用全域規則）、AC8（其他畫面與 header 不受影響、`#upload-error` 維持
   `var(--danger)`）不需要任何程式碼變更，本設計文件把它們列為回歸斷言，而非待實作項目。**
   理由：`.card`、`.btn`/`.btn-primary`（含手機版 `height`/`width:100%`）皆為 SDLCAIP2-44 已完成
   的全域規則，`#view-upload` 範圍內未被任何既有選取器覆寫，本票決策 1/2 也未觸碰這些選取器；
   `#upload-error` 的 `color:var(--danger)` 為 inline style，本票未變動。測試階段應針對這四點
   寫「維持現狀」的回歸驗證，不應誤解成需要新增樣式。

## UI 原型

`docs/design/SDLCAIP2-47-prototype.html` —— 可直接在瀏覽器開啟的靜態原型，重現 `#view-upload`
`.card` + `<h2>` + `#drop-zone` + `#file-info` + `#upload-btn` + `#upload-error` 結構，套用上述
決策 1/2 的具體 CSS/HTML。原型內以「Before（現況）／After（套用本票變更後）」對照方式，各自再
並排提供「桌面寬度」（900px 容器）與「手機寬度」（360px 容器，模擬 <480px 斷點）預覽區塊，
並列出對照說明（emoji 移除、svg 移除、邊框/圓角/hover/dragover/`#file-info`/`.fname` token 來源、
`#drop-zone svg` 死規則已一併刪除），讓人類在 G1b 審核時不必自行縮放瀏覽器視窗即可同時比較
變更前後、桌面/手機四種畫面；也可另外用瀏覽器 DevTools 縮窄視窗驗證真實斷點行為。

## 開放設計問題（定稿時必須為空）

無。CSS token 對照與選取範圍（決策 1）、`#drop-zone svg` 死規則處理（決策 2）、AC1/AC6/AC7/AC8
的回歸性質（決策 3），皆已依現有規格與程式碼／design-system 文件明確解決並附理由，未留待
developer 或後續工單自行決定。
