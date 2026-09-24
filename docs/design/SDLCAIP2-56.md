# 設計文件 — SDLCAIP2-56 Design System｜逐字稿分頁（發言人重命名區 + 逐字稿列表）套用設計系統

## 對應需求規格

`docs/PRD.md` 中 SDLCAIP2-56 段落（G1 已核准版本，第二輪通過，第一輪因「發言人重命名區要求
灰階、不可留 success 綠色」被退回，已於本文件 AC2 落實），從 SDLCAIP2-49（view-result）拆出，
僅涵蓋 `#view-result` 「🎙️ 逐字稿」分頁（`#tab-transcript`）內的發言人重命名區
（`#speaker-rename-area`）與逐字稿列表（`#transcript-container`/`.seg-*`）。共 6 個 AC：

- AC1：`<h4>🎤 發言人重命名（點擊輸入框修改名稱）</h4>`（約第 534 行）→ 文字移除「🎤 」前綴。
- AC2：`#speaker-rename-area`（約第 300–306 行對應實際 318–320 行，現況 `background:#F0FDF4`、
  `border:1px solid #BBF7D0`、`h4 { color: var(--success) }`）→ 背景/邊框改 `--ds-*` 灰階
  token，不留綠色/強調色；`h4` 顏色在 `--ds-text-primary` 或 `--ds-text-secondary` 二選一，
  附理由；圓角 `--ds-radius-md`；`.rename-row input` 邊框 `--ds-border-strong`、圓角
  `--ds-radius-sm`、高度 `--ds-control-h-desktop`（手機 `--ds-control-h-mobile`）；送出按鈕
  `#submit-speaker-names-btn` 維持共用 `.btn`/`.btn-primary`/`.btn-sm`，不另立新樣式。
- AC3：`#transcript-container`/`.seg-*`（約第 289–297 行對應實際 306–315 行，僅
  view-result 使用）：`.seg-row` 邊框 `--ds-border`；`.seg-time` 顏色
  `--ds-text-secondary`、字體 `--ds-font-mono`；`.seg-text` 顏色 `--ds-text-primary`、
  行高比照 Body token。
- AC4：`.speaker-chip` 背景色指派邏輯（`renderTranscript()` 內依 `data-identity` 決定顏色）
  不變（這是資料識別用色，非裝飾）；只套用 `--ds-radius-pill` 與 caption 字級。需確認 chip
  文字在動態背景色上仍清晰可辨。
- AC5（回歸）：<480px `.seg-row` 的時間/講者/文字三者不得重疊或截斷，允許改為垂直堆疊，須明確
  指定堆疊方式。
- AC6（回歸）：`submitSpeakerNames()` 參數不變；`#rename-rows` 子元素 id/class/`onchange`
  綁定不變。須檢查 `renderTranscript()`/rename-row 渲染是否寫入行內樣式覆蓋本票 CSS，並揭露
  結果。

範圍外（明確不處理）：標題/操作列/Tabs（SDLCAIP2-54）、卡片（SDLCAIP2-55）、共用
`.card`/`.btn` 本體、`.speaker-chip` 顏色指派邏輯本身、匯出檔案樣式、全站 header。
`view-history-detail` 的逐字稿為純 `<pre>` 文字，不受影響（見下方現況確認）。

## 現況確認（讀碼結果，供後續章節引用）

- `src/frontend/index.html` 第 306–315 行：`#transcript-container`（`max-height:500px;
  overflow-y:auto`）、`.seg-row`（flex row，`border-bottom:1px solid var(--border)`）、
  `.seg-time`（`min-width:80px; color:var(--muted)`）、`.seg-speaker`（`min-width:100px`）、
  `.speaker-chip`（`border-radius:999px; font-size:.75rem; font-weight:600`）、`.seg-text`
  （`flex:1; line-height:1.5`）。Grep 確認這組 class 全檔案僅在 view-result 使用一次，非全站
  共用，AC3/AC4 可直接改共用本體，不需要 `#view-result` 前綴隔離。
- 第 317–324 行：`#speaker-rename-area`（`background:#F0FDF4; border:1px solid #BBF7D0;
  border-radius:8px`）、`#speaker-rename-area h4`（`color:var(--success)`）、`.rename-row`
  （flex row）、`.rename-row input`（`border:1px solid var(--border); border-radius:5px;
  padding:5px 10px; font-size:.85rem; flex:1; max-width:200px`）。同樣全檔案僅一處使用，可
  直接改共用本體。
- 第 533–540 行（HTML）：`#speaker-rename-area` 為 `#tab-transcript` 內、`.card` 之外的獨立
  區塊（`style="display:none"` 由 JS 控制顯示），內含 `<h4>`、`#rename-rows`（空
  `<div>`，由 JS 填入）、一段提示 `<p>`（`color:#64748B`，本票範圍外，不動）、
  `#submit-speaker-names-btn`（`class="btn btn-primary btn-sm"`，共用樣式）。
- `renderTranscript()`（第 1335–1377 行）：
  - 發言人重命名列：`rows.innerHTML += '<div class="rename-row"><label>...</label><input
    type="text" value="..." onchange="renameSpeaker(...)" placeholder="輸入真實姓名"></div>'`
    ——**未寫入任何行內 `style`**，只設 `type`/`value`/`onchange`/`placeholder` 屬性，本票新增
    CSS 不會被行內樣式覆蓋，AC6 不受影響。`.rename-row`/`.rename-row label`/`.rename-row
    input` 這三個 class 名稱與 `#rename-rows` 容器 id 皆未變動。
  - 逐字稿列：`row.innerHTML = '<span class="seg-time">...</span><span
    class="seg-speaker"><span class="speaker-chip" style="background:${color}">...</span
    ></span><span class="seg-text">...</span>'`——**`.speaker-chip` 本身確實有一個行內
    `style="background:${color}"`**，但那正是 AC4 明講「顏色指派邏輯不變」的部分（第
    1360–1362 行 `colors` 陣列 + `spColorMap`），本票只在共用 CSS 規則中新增
    `border-radius`/`font-size`，不會與行內 `background` 衝突（不同屬性）。`.seg-time`/
    `.seg-speaker`/`.seg-text` 皆無行內樣式，本票對這三者的 CSS 修改可正常生效。
  - `submitSpeakerNames()`（第 1385–1418 行）呼叫 `apiFetch('/api/speaker-names', {method:
    'POST', body: JSON.stringify({job_id: state.jobId, speaker_names: speakerNames})})`——本票
    未修改此函式任何一行，AC6 對此的回歸確認完成。
- `docs/design-system/tokens.json`：Mono `code` 13px/18px/400（`code-mobile`
  11px/17px），用於「Job ID、逐字稿時間戳記等技術性資料」——`usage` 欄位明講涵蓋逐字稿時間戳記，
  與 AC3 `.seg-time` 完全對應。Body `body` 15px/28px/400（`body-mobile` 14px/26px/400），
  color 群組 `badge-bg`/`text-secondary`/`text-primary`/`border`/`border-strong` 定義同
  SDLCAIP2-55/47 已讀取版本。與 SDLCAIP2-45 決策 2 已定案的慣例相同：`:root` 目前沒有字級/
  行高/字重的 `--ds-*` CSS 變數，本票延續同一做法，把具體數值直接寫進規則並註解對應
  `tokens.json` 條目名稱，不新增變數。
- `src/frontend/index.html` 第 1048 行：`view-history-detail` 的逐字稿容器以
  `transcriptContainer.innerHTML = '<pre>${esc(data.transcript_text)}</pre>'` 渲染，純文字
  `<pre>`，未使用 `.seg-row`/`.seg-time`/`.seg-speaker`/`.seg-text`/`.speaker-chip`/
  `#speaker-rename-area` 任何一個 class/id，Grep 確認全檔案這組選取器只在 view-result 出現
  一次。本票變更確認不影響 `view-history-detail`。

## 介面/API 契約

無，本 Story 不涉及對外 API 變更。純前端靜態資源（HTML/CSS）調整，`src/frontend` 無建置流程，
不產生任何新的後端端點或請求/回應格式；`renderTranscript()`/`renameSpeaker()`/
`submitSpeakerNames()` 的渲染與互動邏輯不變動（見現況確認逐項核對）。

## 資料模型

無新增資料模型。

## 選取器 → 屬性 → 舊值 → 新值 對照表

| 選取器 | 屬性 | 舊值 | 新值 | 對應 AC |
|---|---|---|---|---|
| `<h4>`（`#speaker-rename-area` 內） | 文字內容 | `🎤 發言人重命名（點擊輸入框修改名稱）` | `發言人重命名（點擊輸入框修改名稱）` | AC1 |
| `#speaker-rename-area` | `background` | `#F0FDF4` | `var(--ds-surface)` | AC2 |
| `#speaker-rename-area` | `border` | `1px solid #BBF7D0` | `1px solid var(--ds-border)` | AC2 |
| `#speaker-rename-area` | `border-radius` | `8px` | `var(--ds-radius-md)` | AC2 |
| `#speaker-rename-area h4` | `color` | `var(--success)` | `var(--ds-text-secondary)` | AC2 |
| `.rename-row input` | `border` | `1px solid var(--border)` | `1px solid var(--ds-border-strong)` | AC2 |
| `.rename-row input` | `border-radius` | `5px` | `var(--ds-radius-sm)` | AC2 |
| `.rename-row input` | `height` | 無（由 `padding` 撐開） | `var(--ds-control-h-desktop)`（手機 `var(--ds-control-h-mobile)`） | AC2 |
| `.rename-row input` | `padding` | `5px 10px` | `0 12px` | AC2（延伸，見決策 3） |
| `#submit-speaker-names-btn` | （無新規則） | `.btn .btn-primary .btn-sm`（共用） | 不變 | AC2 |
| `.seg-row` | `border-bottom` | `1px solid var(--border)` | `1px solid var(--ds-border)` | AC3 |
| `.seg-time` | `color` | `var(--muted)` | `var(--ds-text-secondary)` | AC3 |
| `.seg-time` | `font-family` | 無（繼承 body 字體） | `var(--ds-font-mono)` | AC3 |
| `.seg-time` | `font-size` / `line-height` | 無 | `13px` / `18px`（Mono.code） | AC3（延伸，見決策 4） |
| `.seg-text` | `color` | 無（繼承 `var(--text)`） | `var(--ds-text-primary)` | AC3 |
| `.seg-text` | `font-family` | 無（繼承 body 字體） | `var(--ds-font-sans)` | AC3（延伸，見決策 5） |
| `.seg-text` | `font-size` / `line-height` | `.875rem`（14px）/ `1.5` | `15px` / `28px`（Body.body） | AC3 |
| `.speaker-chip` | `border-radius` | `999px` | `var(--ds-radius-pill)`（值不變，999px） | AC4 |
| `.speaker-chip` | `font-size` | `.75rem`（12px） | `13px`（Body.caption） | AC4 |
| `.speaker-chip` | `background`（行內 style，逐段動態指派） | 不變 | 不變 | AC4（維持現況） |

## 關鍵技術決策

1. **AC1：`<h4>` 純文字內容變更，移除「🎤 」前綴，不動其餘文字與 HTML 結構。**
   理由：與 SDLCAIP2-44 決策 7（emoji 移除只改文字，不改其餘邏輯）同一模式，`renderTranscript()`
   未讀取或依賴此文字內容，變更零風險。

2. **AC2：`#speaker-rename-area` 完整比照 `.card`（105–112 行）現有的
   `background:var(--ds-surface); border:1px solid var(--ds-border);
   border-radius:var(--ds-radius-md)` 組合，而非另選 `--ds-badge-bg`（提示底色）等其他灰階
   token。`h4` 顏色選 `--ds-text-secondary`（不選 `--ds-text-primary`）。**

   理由：
   - `#speaker-rename-area` 在 `#tab-transcript` 內是 `.card` 之外、但視覺上具備「獨立卡片」
     所有特徵的區塊（自帶 `padding`/`border`/`border-radius`，且與下方逐字稿 `.card`
     並排出現）。`docs/design-system/README.md` 對 `badge-bg` 的定位是「狀態標籤背景」（如
     「雙擊編輯」小標籤），是給小型行內提示用的，不是給這種段落級容器用的；直接沿用 `.card`
     已定案的三個屬性組合，是「同語意、同外觀」的既有前例（與 SDLCAIP2-55 決策 4/7 對
     `.action-table th/td`、`.topic-item` 借用既有 token 組合的做法一致），比另創一組新灰階
     搭配更能維持全站一致性，且徹底符合第一輪 G1 退回意見「不可留任何綠色/強調色」的要求
     （`--ds-surface`/`--ds-border` 為中性灰階，非 `--ds-badge-bg` 這類刻意調得更「安靜」的
     次階灰，兩者都不含強調色，選前者純粹是語意對齊 `.card`）。
   - `h4` 選 `--ds-text-secondary` 而非 `--ds-text-primary`：此 `h4` 的性質是操作提示/說明
     文字（「點擊輸入框修改名稱」），與其正下方已存在、本票範圍外未變動的提示段落 `<p
     style="color:#64748B">`（第 536 行，數值已非常接近 `--ds-text-secondary`
     的 `#6B6A64`）同屬一組「操作說明」語意，而非如 `.section-title`（真正的卡片標題，用
     `--ds-text-primary`）那種內容標題。維持 `h4` 與其下 `<p>` 視覺分量相近、同屬次要說明
     文字，比把它拉到與卡片主標題同等的 `--ds-text-primary` 更符合此區塊「輔助操作區」而非
     「主要內容區」的實際角色定位。

3. **`.rename-row input` 的 `padding` 一併從 `5px 10px` 改為 `0 12px`（AC2 條文未逐字列出此
   屬性，但列出的其餘四項改為視覺延伸而非另立產品決策）。**
   理由：AC2 已明講改用 `--ds-control-h-desktop`/`--ds-control-h-mobile` 固定高度，若保留原本
   `padding: 5px 10px`（上下各 5px 的內距）會與固定 `height` 互相打架，導致文字在輸入框內
   垂直置中失真；比照既有 `.input`/`.meeting-info-grid input`（SDLCAIP2-55 決策 2）已定案的
   「高度用 `height`、內距只留水平方向（`0 12px`）」模式，是套用「高度 token 化」這個 AC
   已明講意圖時的必要配套，與 SDLCAIP2-55 決策 2 對「AC 只列部分屬性、一併補上配套屬性」的
   判斷基準一致。`max-width:200px`、`flex:1` 未在 AC2 列出且與 token 化無直接關聯，維持原樣
   不動。

4. **AC3：`.seg-time` 除 `color`/`font-family` 外，一併補上 `font-size:13px;
   line-height:18px`（對應 `tokens.json` Mono.code），不只換字體家族。**
   理由：`tokens.json` Mono `code` 條目的 `usage` 明確寫「Job ID、逐字稿時間戳記等技術性資料」
   ——直接點名逐字稿時間戳記正是 `.seg-time` 這個元素。若只換 `font-family` 而不套用同一組
   `code` 字級/行高（保留舊的 `.875rem` 繼承值），會出現「換了等寬字體、卻不是
   design-system 定義的那個完整 Mono.code 樣式」的半套結果；比照 SDLCAIP2-45/55 系列「AC
   點名某個 token 名稱時，該 token 定義的完整屬性一併套用」的既定判斷基準（如 SDLCAIP2-55
   決策 1/3 對 Heading/Body token 的完整套用）。手機版未新增 `code-mobile`（11px/18px）
   media query：AC3 條文未提及手機版尺寸，且 AC5 已另外處理 <480px 的版面堆疊（決策 6），
   避免在 AC 未要求的範圍上自行擴大規格。

5. **AC3：`.seg-text` 除 `color` 外，一併補上 `font-family:var(--ds-font-sans)`，並用
   Body `body` token（15px/28px）取代原本的 `.875rem`/`line-height:1.5`。**
   理由：AC3 條文寫「line-height per body token」，`tokens.json` 的 Body `body` 是
   `font-family`+`font-size`+`line-height`+`font-weight` 四項打包定義的一組樣式，若只抽取
   `line-height` 數值（28px）套在原本的 `.875rem`（14px）字級上，會產生字級與行高比例失真
   （28px 行高配 14px 字級，行距會顯得過鬆），不是 token 的原始設計意圖；因此比照 AC1 明講
   套用「body token」時完整採用該 token 的字級+行高+字體家族（與決策 4 同一判斷基準），
   `font-weight:400` 為預設值不需額外聲明。手機版同理未新增 `body-mobile`：AC3 未提及手機版，
   AC5 已另外處理 <480px 版面（決策 6），維持窄範圍原則。

6. **AC5：<480px `.seg-row` 改為 `flex-direction: column`，讓時間/講者/文字三者垂直堆疊為三行，
   不合併成同一行、也不新增任何 HTML 結構。**
   ```css
   @media (max-width: 479px) {
     .seg-row { flex-direction: column; align-items: flex-start; gap: 6px; padding: 12px 0; }
     .seg-time { min-width: 0; }
     .seg-speaker { min-width: 0; }
     .seg-text { width: 100%; }
   }
   ```
   堆疊順序沿用既有 DOM 順序（不需要改 `renderTranscript()` 的 `row.innerHTML` 拼接順序）：
   第一行時間戳記、第二行講者 chip、第三行逐字稿文字，每行各自佔滿容器寬度、不再受
   `min-width:80px`/`min-width:100px` 擠壓，`.seg-text` 明確給 `width:100%` 確保長句正常換行
   而非被旁邊欄位擠出可視範圍。理由：現況確認已證實 `renderTranscript()` 的 `row.innerHTML`
   模板未設任何行內佈局樣式，CSS-only 的 `flex-direction` 切換可安全生效，不需 JS 配合；比照
   SDLCAIP2-45/50 決策 7「CSS-only、不動渲染結構」的既定手法，是本票能滿足「時間/講者/文字
   不得重疊或截斷」要求的最小改動路徑。三行式堆疊（而非嘗試把時間與 chip 併作一行）是刻意選擇：
   不新增 wrapper `<span>` 就無法用 flex 把兩者組成同一行又各自獨立換行，若要做到「兩行式」
   需要新增 HTML 結構，屬於範圍外的渲染邏輯變更，AC5 本身也只要求「不重疊/不截斷」，三行式已
   完整滿足此驗收標準，故不做更複雜的排版。

7. **AC4：`.speaker-chip` 只新增 `border-radius: var(--ds-radius-pill)`
   （999px，數值與舊值相同，純 token 化）與 `font-size: 13px`（Body.caption），不新增
   `font-family`、不改 `font-weight`、不改行內動態 `background` 指派邏輯。**
   理由：AC4 條文明講「only apply `--ds-radius-pill` and caption font size」，措辭比 AC2/AC3
   更窄（沒有「延伸配套屬性」的空間），故本票嚴格只動這兩項，`font-weight:600`（維持粗體以確保
   在淺色動態背景上的可讀性）與既有字體繼承維持不動；顏色指派邏輯（`colors` 陣列 +
   `spColorMap`，第 1360–1362 行）本票確認不動，符合 AC4「顏色指派邏輯不變」的明文要求。
   **legibility 確認**：`.speaker-chip` 未設 `color`，文字色繼承自 `body`/`.card` 的
   `var(--text)`（`#1E293B`，深色），現有六色色盤（`#DBEAFE`/`#FCE7F3`/`#D1FAE5`/`#FEF3C7`/
   `#EDE9FE`/`#FFE4E6`）皆為高明度淺色背景，深色文字在其上對比度充足、清晰可辨；`caption`
   （13px）比舊值（12px）字級略增大，對可讀性只有正面影響，無需額外調整文字色。

8. **AC6（回歸）不需要任何 JS 程式碼變更，本設計文件把它列為回歸斷言，而非待實作項目。**
   理由：本票所有變更皆為 CSS 規則調整 + 純文字內容變更（決策 1），未新增/刪除/更名任何
   `id`/`class`/`onchange` 綁定，`submitSpeakerNames()`/`renameSpeaker()`/`renderTranscript()`
   皆以既有 `id`/`class` 操作、不依賴 DOM 結構層級或行內樣式，已於「現況確認」段落逐項核對
   （含確認 `.speaker-chip` 唯一的行內樣式 `background` 與本票新增規則屬性不重疊）。測試階段
   應針對此點寫「維持現狀」的回歸驗證。`view-history-detail` 的 `<pre>` 逐字稿渲染路徑
   （第 1048 行）未使用本票任何一個選取器，確認不受影響。

## UI 原型

`docs/design/SDLCAIP2-56-prototype.html` —— 可直接在瀏覽器開啟的靜態原型，重現
`#speaker-rename-area`（`h4` + 2–3 位講者的 `.rename-row` + `#submit-speaker-names-btn`）與
`#transcript-container`（多筆 `.seg-row`，含時間戳記/`.speaker-chip`/逐字稿文字，2–3 位講者、
真實感中文範例內容），套用上述決策 1–7 的具體 CSS。原型以 Before（現況）/After（套用本票變更後）
× 桌面寬度（900px 容器）/ 手機寬度（360px 容器，模擬 <480px 斷點）四象限並排對照，手機
After 象限具體展示決策 6 的三行式垂直堆疊效果，確保長講者名稱與長逐字稿文字皆不會重疊或被截斷。
也可另外用瀏覽器 DevTools 縮窄視窗驗證真實斷點行為。

## 開放設計問題（定稿時必須為空）

無。`#speaker-rename-area` 灰階背景/邊框 token 選用與 `h4` 文字色二選一（決策 2，回應第一輪
G1 退回意見）、`.rename-row input` padding 配套調整（決策 3）、`.seg-time`/`.seg-text` 套用完整
token 樣式組（決策 4–5）、<480px 垂直堆疊的具體實作方式（決策 6）、`.speaker-chip` 嚴格窄範圍
套用與可讀性確認（決策 7）、AC6 的回歸性質（決策 8），皆已依現有規格、程式碼現況、以及
SDLCAIP2-44/45/47/55 已定案的同類決策明確解決並附理由，未留待 developer 或後續工單自行決定。
