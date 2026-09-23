# 設計文件 — SDLCAIP2-44 Design System｜基礎建設

## 對應需求規格

`docs/PRD.md` 的 `## SDLCAIP2-44：Design System｜基礎建設` 段落（G1 已核准版本），共 9 個 Gherkin
scenario：token 導入、`.btn`/`.card`/`.section-title .badge` 改用 token、新增未套用的
`.input` class、header 移除裝飾性 icon、header RWD 拆列（桌面單列／手機兩列）、範圍外畫面不受影響。

## 介面/API 契約

無，本 Story 不涉及對外 API 變更。純前端靜態資源（HTML/CSS）調整，`src/frontend` 無建置流程，
不產生任何新的後端端點或請求/回應格式。

## 資料模型

無新增資料模型。

## 現況確認（讀碼結果，供後續章節引用）

- `src/frontend/index.html` 第 8–20 行既有 `:root` 定義了 `--bg: #F8FAFC`、`--border: #E2E8F0`
  等變數，被 `#drop-zone`、`.stage-item`、`.action-table`、`.seg-row` 等**範圍外**選取器大量使用。
- `docs/design-system/tokens.css` 的 `:root` 定義了**同名但不同值**的 `--bg: #F6F5F3`、
  `--border: #E4E3DF`（見下方「關鍵技術決策」的衝突處理）。
- 確認全檔案目前**沒有任何 `@media` 規則**（已用 grep 逐一核對，非僅採信規格文字）。
- 現有 `.btn`（第 57–70 行）、`.card`（第 39–41 行）、`.section-title .badge`（第 100–101 行）、
  `<header>`（第 199–206 行）的確切結構如規格所述；`.btn-outline` 目前語意等同 design-system
  Button 元件的「次要按鈕」（白底＋邊框＋主文字色）。
- `#modified-badge`、`#low-confidence-badge`、view-history 第 382 行的「📜 歷史紀錄」section-title
  icon，皆與本票的 `.section-title .badge` / header icon 修改**目標選取器不同**，明確排除在外。

## 關鍵技術決策

1. **`--bg`/`--border` 命名衝突的解法：全部新 token 以 `--ds-` 前綴加入既有 `:root` 區塊，不觸碰
   任何既有變數名稱。**
   理由：既有 `--bg`/`--border`（及 `--primary`/`--card`/`--text`/`--muted` 等）被大量範圍外
   選取器直接引用；若把 `tokens.css` 的 `:root` 內容原樣貼入同一個 `:root`，會靜默覆寫這些值，
   違反 AC9（範圍外畫面不得有非預期視覺變化）。改用前綴後兩組變數並存、互不干擾，且日後
   SDLCAIP2-45~50 逐頁調整時可以持續沿用 `--ds-*`，不必重做這個決策。
   具體對照表（加進既有 `:root` 區塊內，緊接在既有變數之後，不刪除/不修改既有變數）：
   `--ds-bg`, `--ds-surface`, `--ds-border`, `--ds-border-strong`, `--ds-text-primary`,
   `--ds-text-secondary`, `--ds-text-placeholder`, `--ds-ink-100`~`--ds-ink-400`,
   `--ds-badge-bg`, `--ds-badge-border`, `--ds-badge-text`, `--ds-focus-ring`,
   `--ds-font-sans`, `--ds-font-mono`, `--ds-space-1`~`--ds-space-8`,
   `--ds-radius-sm`/`--ds-radius-md`/`--ds-radius-pill`,
   `--ds-control-h-desktop`/`--ds-control-h-mobile`,
   `--ds-header-h-desktop`/`--ds-header-h-mobile`,
   `--ds-container-max`, `--ds-breakpoint-mobile`。
   完整數值見 `docs/design-system/tokens.css`（本票直接照搬其 `:root` 內的值，只加前綴，不更動
   任何數值）。AC1 要求「載入 tokens.css 定義的完整 token 集合」，以此方式滿足——完整集合都
   進來了，只是用不衝突的變數名承載，而非用 `<link>` 直接載入外部檔案（見下一點）。

2. **不用 `<link rel="stylesheet" href=".../tokens.css">`，改為把 token 值手動同步進
   `index.html` 既有 `<style>` 區塊。**
   理由：`src/frontend` 沒有建置流程，且不確定 `docs/design-system/tokens.css` 這個路徑在
   實際部署時是否會被靜態伺服器以可存取的相對路徑提供（`docs/` 通常不在前端資源的服務範圍內）；
   直接內嵌可避免額外的路徑/CORS/404 風險，也避免額外一次網路請求。代價是失去單一真實來源，
   兩份檔案需要人工同步——已在 `index.html` 新增區塊加註解，註明「數值來源：
   `docs/design-system/tokens.json`／`tokens.css`，變更請兩邊同步更新」，把這個已知落差寫清楚，
   不留給未來的人自己發現。

3. **Google Fonts 用標準 `<link>` 載入，放在既有 `<style>` 之前。**
   於 `<head>` 加入：
   ```html
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
   ```
   即 `tokens.css` 檔頭註解裡指定的那組字重。理由：無建置流程，Google Fonts 官方標準做法
   （`<link>`）是唯一不需要額外工具鏈的選項。

4. **`.btn`/`.btn-primary`/`.btn-outline`/`.btn-sm` 手機版高度統一由基底 `.btn` 規則控制，
   不需要對 `.btn-sm` 另外寫一條 media query。**
   理由：`.btn-sm` 現有規則只覆寫 `padding`/`font-size`，並未覆寫 `height`；因此手機版媒體查詢
   內對 `.btn` 設定 `height: var(--ds-control-h-mobile)` 會自動套用到所有帶 `.btn` 基底 class
   的按鈕（含 `.btn-sm`），符合 AC2「`.btn`/`.btn-primary`/`.btn-outline`/`.btn-sm`...手機版高度
   改用 control-h-mobile」的要求，且只需要改一處，不必四個選取器各寫一次。
   對照組：`.btn` 全域手機版規則同時有 `width:100%`（沿用 tokens.css 原始定義，讓一般畫面裡
   單顆／並排按鈕在手機版變成堆疊全寬，符合 Button 元件規格）。

5. **Header 內的按鈕明確排除全域 `.btn` 手機版 `width:100%` 規則，改為 `width:auto`。**
   理由：決策 4 的全域手機版規則是為一般表單/工具列按鈕（單顆全寬或並排堆疊）設計；但 header
   的「管理者儀表板」「歷史紀錄」「登出」必須保持原本的行內按鈕尺寸，才能符合 AC7/AC8 的
   兩列/橫向捲動版型（若被拉成 `width:100%`，第二列的橫向捲動就沒有意義，且登出按鈕會把整個
   第一列撐成單欄堆疊，不符合「第一列僅標題＋登出」的並排要求）。這是規格沒有明講、但兩條
   AC（AC2 的全域按鈕手機行為 vs. AC7/AC8 的 header 兩列版型）放在一起必然衝突之處，故在此明確
   解決：新增 `header .btn { width: auto; flex: 0 0 auto; }`，只在 `header` 選取器範圍內覆寫，
   不影響其他頁面的按鈕。

6. **Header 手機版兩列版型用 `.header-secondary` 包一層 + `display:contents`（桌面）／
   `flex-basis:100%`（手機）實作，不用 JS、不用兩份 HTML。**
   理由：`display:contents` 讓包裹用的 `<div>` 在桌面版「消失」，子元素（管理者儀表板／
   歷史紀錄／使用者信箱）直接參與 `header` 本身的 flex 排版，視覺上與目前單列结構完全一致；
   手機版媒體查詢把同一個 `<div>` 切回 `display:flex` 並給 `flex-basis:100%`，強制換到新的一行，
   達成「拆兩列」且不必維護兩份重複的按鈕 HTML/JS handler。`<h1>` 副標題（`Meeting Minutes AI`）
   在手機版隱藏，因為 Header README／AC8 明確說手機第一列「僅保留標題與登出按鈕」。
   Header 背景色由藍色（`var(--primary)`）改為 `var(--ds-ink-100)`／文字改為 `var(--ds-bg)`：
   使用者故事本文明確寫「全站共用 `<header>`...改用這些 token」，且 design-system 的核心原則
   是「灰階為主，不用強調色」，header 若維持藍色會與新採用的 `.btn`/`.card`/`.badge` 灰階色階
   不一致；Gherkin scenario 沒有另外針對背景色寫斷言，但這是「改用 token」這句話在 header 上
   唯一合理的落地方式（Header 元件 README 也明講桌面版背景用「系統選定的 ink 深淺」），故納入
   設計範圍，不視為額外發明的產品需求。

7. **移除裝飾性 icon（AC6）只改按鈕文字，不改 `onclick`/`id`/其餘 inline 邏輯。**
   `📊 管理者儀表板` → `管理者儀表板`；`📜 歷史紀錄` → `歷史紀錄`。第 382 行 view-history
   內文的「📜 歷史紀錄」section-title 明確排除（範圍外）。

8. **`.card` 的顏色/圓角/內距變更是全站共用 class，範圍外頁面「視覺會變」是預期中的變更，
   不算違反 AC9。**
   AC9「範圍外畫面視覺不得有非預期改變」指的是本票**沒有**列為目標的選取器/版面（例如
   `#drop-zone`、`.stage-item`、`.action-table` 等頁面專屬樣式）；`.card`/`.btn`/
   `.section-title .badge`/`<header>` 本身就是本票明確列出的全站共用樣式目標，它們套用到
   view-admin/upload/progress/result/history 等頁面時外觀改變是刻意的、已被 AC2-AC4/AC6-AC8
   涵蓋的結果，不是「非預期」。在 `index.html` 對應區塊加註解澄清這一點，避免後續工單誤解
   AC9 要求連這些共用 class 都不能變。

## 新增/變更的 CSS 與 HTML 規格（developer 可直接依此實作）

完整、可運行的版本見 `docs/design/SDLCAIP2-44-prototype.html`（決策 1-7 的具體 CSS/HTML 皆已
寫在該檔案並可在瀏覽器開啟驗證，包含縮窄視窗到 <480px 觀察 header 拆列）。開發時把該原型裡
`:root` 新增區塊、`.btn`/`.card`/`.section-title .badge`/`.input`/header 對應規則，原樣移植進
`src/frontend/index.html` 既有 `<style>` 區塊與 `<header>` 標記，並：
- 保留 `index.html` 既有 `:root` 內的變數不動，新增區塊接在其後。
- 保留 `admin-dashboard-btn` 現有的 `style="display:none"` inline 切換邏輯（JS 控制顯示/隱藏
  不在本票範圍，不更動）。
- `.btn` 基底規則的 `display:inline-flex; gap:8px;` 等既有結構屬性維持不變，只替換顏色/尺寸/
  圓角/字級為 `--ds-*` token；不改變既有 `:active` transform 等既有互動細節。

## UI 原型

`docs/design/SDLCAIP2-44-prototype.html` —— 可直接在瀏覽器開啟的靜態原型，涵蓋新 token
`:root` 定義、`.btn`（含 primary/outline/sm）、`.card`、`.section-title .badge`、新增未套用的
`.input`，以及 header 的完整桌面/手機兩種版型（開啟後把視窗縮到 480px 以下即可看到手機版兩列
＋橫向捲動次要導覽）。內含說明列，標明如何驗證 RWD 行為。

## 開放設計問題（定稿時必須為空）

無。規格與既有程式碼足以推導出完整設計；`--bg`/`--border` 命名衝突、header 手機版按鈕寬度與
全域按鈕手機版寬度規則的衝突、header 背景色是否改用 token，皆已在「關鍵技術決策」中明確解決
並附理由，未留待 developer 或後續工單自行決定。
