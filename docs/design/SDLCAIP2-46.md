# 設計文件 — SDLCAIP2-46 Design System｜處理進度畫面 view-progress

## 對應需求規格

`docs/PRD.md` 的 `## SDLCAIP2-46` 段落（G1 已核准版本），共 9 個 Gherkin scenario：`<h2>` 移除
emoji（AC1）、三個 `.stage-icon` 移除 emoji 但保留 class 命名讓 JS 照常運作、三態仍需可靠底色
深淺等非文字視覺分辨（AC2）、`.stage-icon.done/.active/.waiting`／`.progress-bar`／
`.progress-bar-wrap` 的 background/color/border 改用 `--ds-*` 灰階 token、不可用
`--primary`/`--success`/`--warning`/`--danger` 或寫死色碼（AC3）、`#view-progress` 內文字
font-family 皆為 `var(--ds-font-sans)`（AC4）、`.stage-list`/`.stage-item` 間距改用 `--ds-space-*`
（AC5）、`#progress-message` 套用 Badge 樣式（人類已在 SDLCAIP2-53 決議選項 A，AC6）、取消按鈕不變
且與 badge 視覺明確不同（AC7）、輪詢 JS 行為/id/class 命名不變（AC8）、其他畫面不受影響（AC9）。

## 現況確認（讀碼結果，供後續章節引用）

- `src/frontend/index.html` 第 407–440 行：`#view-progress` 只有一個 `.card`，內含
  `<h2 style="font-size:1.2rem;margin-bottom:8px;">⚙️ 處理中...</h2>`、
  `<p id="progress-message" style="color:var(--muted);font-size:.875rem;margin-bottom:20px;">`
  （inline style，無 CSS class）、`.progress-bar-wrap`/`.progress-bar`、`.progress-pct`、
  `.stage-list`（三個 `.stage-item`，各含 `.stage-icon waiting/active/done` id
  `icon-uploaded`/`icon-transcribed`/`icon-done`，內容為 📤/🎙️/✨ 三個 emoji 字元；
  `.stage-label`/`.stage-msg`）、以及 `.btn.btn-outline.btn-sm`「取消」按鈕。
- 第 161–176 行為對應 CSS：`.stage-icon.done{background:#DCFCE7;color:var(--success)}`、
  `.stage-icon.active{background:#DBEAFE;color:var(--primary)}`、
  `.stage-icon.waiting{background:var(--bg);color:var(--muted)}`（皆未設 `border`）；
  `.progress-bar-wrap{background:var(--border)}`；`.progress-bar{background:var(--primary)}`；
  `#progress-message{font-size:.9rem;color:var(--muted);margin-top:12px}`（此條 CSS 目前被 HTML
  inline style 完全覆蓋，實際未生效——inline style 優先權高於外部樣式表同層級選取器）。
- JS `updateProgressUI()`（第 1206–1222 行）：只對 `#progress-bar`/`#progress-pct`/
  `#progress-message` 的 `style.width`/`textContent` 賦值，並用 `icon.className = 'stage-icon ' +
  狀態字串` 整段覆寫三個 icon 的 class；**完全沒有讀寫 icon 的 `textContent`／`innerHTML`**，移除
  icon 內的 emoji 字元對 JS 邏輯零風險（AC8 成立的程式碼證據）。`s.message || ''` 顯示訊息可能為
  空字串，對應 `#progress-message` 可能呈現「空白徽章」的邊界情況（見決策 4）。
- 全檔案 grep 確認 `.stage-label`/`.stage-msg`/`.progress-pct`/`.progress-bar`/
  `.progress-bar-wrap`/`.stage-icon`/`#progress-message` 皆只出現在 `#view-progress` 範圍內
  （第 161–176 行定義、第 407–440 行使用、第 1206–1222/1629 行 JS 操作），非跨頁共用 class，
  故本票可直接在既有選取器上改寫屬性，不需要額外的 `#view-progress` 前綴來避免波及其他畫面
  （AC9 對應到「維持選取器範圍原樣，只換屬性值」而非「重新限定選取器範圍」）。
- `docs/design-system/README.md` 色彩表：`ink-100~400` 用途為「頁首、主要按鈕、**目前分頁**」；
  `badge-bg`/`badge-border`/`badge-text` 用途為「狀態標籤專用，刻意做得比按鈕更安靜」——這兩組
  token 的既有語意分別對應本票「目前正在進行的階段」與「已完成、只是安靜陳列的狀態」，是決策 1
  選色的依據（見下）。`docs/design-system/components/Badge/` 與第 189–199 行
  `.section-title .badge` 是既有的 Badge 樣式範例，AC6 明講不可修改該規則本體，本票另外對
  `#progress-message` 套用同一組視覺 token。

## 介面/API 契約

無，本 Story 不涉及對外 API 變更。純前端靜態資源（HTML/CSS）調整，`src/frontend` 無建置流程，
不產生任何新的後端端點或請求/回應格式；輪詢邏輯與 `updateProgressUI()`/`cancelJob()` 等既有 JS
不變動（AC8）。

## 資料模型

無新增資料模型。

## 關鍵技術決策

1. **`.stage-icon.waiting/.active/.done` 三態分別對應「空心（waiting）／實心深色（active）／
   安靜淺灰實心（done）」三種灰階填色＋邊框組合，不新增任何文字或符號取代原本的 emoji。**

   ```css
   .stage-icon.waiting { background: var(--ds-surface); color: var(--ds-text-secondary);
                          border: 1px solid var(--ds-border-strong); }
   .stage-icon.active { background: var(--ds-ink-100); color: var(--ds-bg);
                         border: 1px solid var(--ds-ink-100); }
   .stage-icon.done { background: var(--ds-badge-bg); color: var(--ds-badge-text);
                       border: 1px solid var(--ds-badge-border); }
   ```

   理由：
   - AC2 明講三態「仍可靠底色深淺等非文字視覺分辨」，且範圍外／設計系統原則 3（不使用裝飾性
     圖示）不允許用新的替代符號（例如打勾字元）填補移除 emoji 後的空缺；因此三個 icon 維持
     空內容 `<div>`，純靠 CSS 背景／邊框分辨，不產生新文案（不落入「新增文案」範圍外項目）。
   - `active` 選用 `--ds-ink-100`：README 色彩表明講 `ink-100~400` 用途包含「目前分頁」，
     語意上與「目前正在進行的階段」一致，也呼應決策 3（`.progress-bar` 同樣選用
     `--ds-ink-100`），讓「目前階段」在 icon 與進度條上使用同一個視覺權重，幫助使用者一眼對應。
   - `done`（已完成但不是目前焦點）選用 `--ds-badge-bg`/`--ds-badge-border`/`--ds-badge-text`：
     README 明講 badge 系列 token 的既有語意就是「狀態標籤，比按鈕更安靜」，完成態不需要再搶
     視覺焦點，用同一套「安靜狀態」語彙描述最貼切，也與決策 4 的 `#progress-message` badge
     共用同一組 token，維持頁面內一致。
   - `waiting`（尚未開始）選用 `--ds-surface`（與卡片背景相同，近乎「隱形」）＋
     `--ds-border-strong`（控制項邊框深階）：呈現「空心尚未填入」的視覺意象，三態底色深淺依序
     為 `surface`（最淺）→ `badge-bg`（淺灰）→ `ink-100`（最深），滿足 AC2「底色深淺可分辨」；
     原本沒有 `border` 屬性的三個規則，依 AC3 要求「background/color/border 改用 `--ds-*`」
     一併補上 `border`——`waiting`/`done` 用邊框讓填色偏淺時仍有清楚輪廓，`active` 邊框色與
     背景同色（純粹讓元素在 `border-box` 尺寸計算上與其他兩態一致，避免因為多一圈邊框而尺寸
     跳動）。
   - `color` 屬性（原本是 emoji 字元的顏色）雖然三個 icon 現在都是空內容、視覺上不生效，仍依
     AC3 文字要求一併改為 `--ds-*` token（而非留著 `var(--success)` 等舊變數死值），避免未來
     若 icon 內容恢復（例如加入可存取性用的螢幕閱讀器文字）時繼承到不合規的顏色。

2. **`.stage-list`/`.stage-item` 的 `gap`/`padding`/`margin` 對應 `--ds-space-*`；`.stage-list`
   兩個屬性剛好整除既有 token，`.stage-item` 的 `gap`/`padding` 無精確對應值時一律「四捨五入取
   較大的 token」。**

   ```css
   .stage-list { gap: var(--ds-space-2); margin: var(--ds-space-5) 0; }
   .stage-item { gap: var(--ds-space-3); padding: var(--ds-space-3) var(--ds-space-4); }
   ```

   對照：`.stage-list` 原 `gap:12px` = `--ds-space-2`（12px，精確相符）；原 `margin:24px 0` =
   `--ds-space-5`（24px，精確相符）。`.stage-item` 原 `gap:14px` 介於 `--ds-space-2`（12px）與
   `--ds-space-3`（16px）之間、誤差相同（皆為 2px），原 `padding` 垂直方向同樣是 14px（同一
   兩難），水平方向原 18px 介於 `--ds-space-3`（16px）與 `--ds-space-4`（20px）之間、誤差同樣
   相同（皆為 2px）。理由：
   - 三處都出現「誤差相等、無法用『取最接近值』單一規則決定」的情況，故明確訂出一致的決勝
     規則「取較大者」，而非逐一各自判斷，讓 developer 之後遇到同類情況有可依循的準則，而不是
     每次都要回頭問設計文件。
   - 取較大值而非較小值：對照 README 設計原則 5「RWD 是預設需求……手機版不得出現……觸控熱區
     過小」，`.stage-item` 在手機版仍是可視內容區塊（雖非可點擊控制項），多 2px 留白對可讀性
     只有好處、沒有壞處，風險對稱情況下優先選對使用者更寬鬆的一邊。
   - 水平 padding 取 `--ds-space-4`（20px）恰好與 `.btn` 既有的 `padding: 0 20px`
     （第 135 行，同樣是 `--ds-space-4`）數值相同，維持全站「控制項／內容區塊水平內距」的既有
     觀感尺度一致，不是額外新創的數值巧合。

3. **`.progress-bar-wrap` 的 track 背景改用 `--ds-border`（分隔線語意）；`.progress-bar` 的填色
   改用 `--ds-ink-100`（與決策 1 的 `.stage-icon.active` 同一 token）。`border-radius: 4px`
   不在 AC3 列出的屬性範圍（只列 background/color/border），維持原樣不動。**

   ```css
   .progress-bar-wrap { background: var(--ds-border); }
   .progress-bar { background: var(--ds-ink-100); }
   ```

   理由：`.progress-bar-wrap` 是進度條的「軌道」，語意上等同分隔線／背景底色，README 色彩表
   `border`/`border-strong` 兩階裡「分隔線用淺」正是這個用途，選 `--ds-border`（淺階）而非
   `border-strong`。`.progress-bar` 是「目前進度」的視覺指標，語意與決策 1 的
   `active` icon 相同（都代表「現在正在發生的事」），選用同一個 `--ds-ink-100` 讓兩者在頁面上
   用同一視覺權重呼應，使用者能直覺對應「進度條走到哪、對應哪個 icon 是 active」。

4. **`#progress-message` 依 SDLCAIP2-53 人類決議（選項 A）改為 Badge 視覺；移除 HTML 第 410 行
   原有 inline style（`color`/`font-size`/`margin-bottom`），改用外部 CSS 規則整組定義，並新增
   `:empty` 規則避免顯示空徽章。**

   HTML（僅移除 `style` 屬性，id/文字內容/JS 綁定不變）：
   ```html
   <p id="progress-message"></p>
   ```
   CSS（取代第 176 行原規則）：
   ```css
   #progress-message {
     display: inline-block;
     font-family: var(--ds-font-sans);
     font-size: .875rem;
     padding: 4px 12px;
     border-radius: var(--ds-radius-pill);
     background: var(--ds-badge-bg);
     border: 1px solid var(--ds-badge-border);
     color: var(--ds-badge-text);
     margin-bottom: var(--ds-space-4);
   }
   #progress-message:empty { display: none; }
   ```
   理由：
   - 原本第 410 行 inline style 設了 `color:var(--muted)`，若只改外部 CSS 的 `color` 而不動
     inline style，inline style 的優先權永遠蓋過外部規則，AC6 會「寫了但不生效」；因此必須
     連動移除 inline style，屬性一併搬進外部規則集中管理，這是 HTML 層級的必要變更（不涉及
     JS，`textContent` 賦值邏輯不受影響）。
   - AC6 明講四個屬性（background/border/color/border-radius），但只設這四項會讓 pill 形狀的
     `border-radius: 999px` 套在一個滿版寬度、無水平內距的 `<p>` 上，視覺上只會是「兩端圓角的
     長條」而不是「徽章」，不符合「套用 Badge 樣式」的規格意圖。因此另外補上 `display:
     inline-block`（讓寬度縮到內容大小，而非佔滿整行）與 `padding: 4px 12px`
     （沿用第 189–199 行 `.section-title .badge` 既有的相同數值，保持全站唯一既有 Badge
     範例視覺一致）——這兩項是實現「Badge 樣式」在技術上必要的最小補充，不是超出規格的新產品
     決策，且未違反 AC6「無 cursor:pointer、無 hover/active」的限制。
   - `font-size` 維持原有 `.875rem`（14px），不比照 `.section-title .badge` 的 13px：AC6/AC4
     都沒有要求改字級，且原尺寸與頁面上 `.stage-msg`（.8rem）/`.progress-pct`（.85rem）的字級
     梯度已相容，改動字級屬於未被要求的額外變更，不做。
   - `margin-bottom` 原始寫死 `20px`，剛好等於 `--ds-space-4`，非 AC 強制要求 token 化，但既然
     整條規則都在重寫，直接對應既有 token 值（無精度損失、無視覺變化）維持全站一致性，順手處理。
   - 新增 `#progress-message:empty { display: none; }`：JS 第 1209 行 `s.message || ''`
     證實 `textContent` 可能為空字串，若不處理，空字串狀態下仍會渲染一顆「空白圓角徽章」
     （因為 padding/border/background 不看內容是否為空），視覺上是明顯的畫面缺陷；`:empty`
     虛擬類別在 `textContent = ''` 時會命中（沒有任何子節點），是 CSS-only 的行為修正，不需要
     改動 JS（不影響 AC8）。

5. **AC7（取消按鈕不變、與 badge 視覺明確不同）與 AC8（輪詢 JS 行為/id/class 命名不變）不需要
   任何程式碼變更，本設計文件把它們列為回歸斷言，而非待實作項目。**

   理由：`.btn.btn-outline.btn-sm` 是 SDLCAIP2-44 已完成的全域規則，本票未觸碰 `.btn`/
   `.btn-outline`/`.btn-sm`，取消按鈕維持方形／有邊框／可點擊的既有外觀，與決策 4 的 pill 形
   badge（圓角 999px、`cursor` 未設為 pointer、無 hover）在形狀與互動語意上本來就明確不同，
   不需額外樣式強化差異。`updateProgressUI()`/輪詢函式（第 1206–1222 行）與相關 id/class
   完全未被本票任何決策觸碰（決策 1–4 都只改既有選取器的屬性值或移除 HTML inline
   style/emoji 文字節點，未新增/刪除/重新命名任何 id 或 class），JS 讀寫的 id 全部維持存在。

## UI 原型

`docs/design/SDLCAIP2-46-prototype.html` —— 可直接在瀏覽器開啟的靜態原型，重現 `#view-progress`
`.card` + `<h2>` + `#progress-message` + `.progress-bar-wrap` + 三個 `.stage-item`
（`.stage-icon` 分別呈現 waiting/active/done 三態）+ 取消按鈕結構，套用上述決策 1–4 的具體
CSS/HTML。原型以「Before（現況，含 emoji／舊 token）／After（套用本票變更後）」對照方式，各自
再並排提供「桌面寬度」（900px 容器）與「手機寬度」（360px 容器，模擬 <480px 斷點）預覽區塊；
每個 After 區塊同時展示三個階段皆為 waiting、中間階段 active／其餘 waiting+done、以及全部 done
三種進度快照，並列出 `#progress-message` 有文字與空字串（驗證 `:empty` 隱藏規則）兩種狀態，
讓人類在 G1b 審核時不必自行縮放瀏覽器視窗或手動觸發輪詢即可同時看到三種階段狀態、badge 樣式、
以及桌面/手機四種畫面組合；也可另外用瀏覽器 DevTools 縮窄視窗驗證真實斷點行為。

## 開放設計問題（定稿時必須為空）

無。三態 icon 灰階與邊框選色（決策 1）、`.stage-item` 間距無精確對應值時的決勝規則（決策 2）、
進度條/軌道選色（決策 3）、`#progress-message` inline style 移除與 Badge 樣式技術補充項目
（決策 4）、AC7/AC8 的回歸性質（決策 5），皆已依現有規格、SDLCAIP2-53 人類決議與程式碼／
design-system 文件明確解決並附理由，未留待 developer 或後續工單自行決定。
