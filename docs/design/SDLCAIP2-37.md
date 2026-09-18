# 設計文件 — SDLCAIP2-37 會議紀錄結果頁面操作區塊視覺風格不一致、排列凌亂

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-37）：`#view-result` 右上角操作區塊（模板
選單、匯出格式選單、匯出按鈕、清除暫存、新錄音）樣式不一致且排列無分組。
四條 Gherkin AC：AC1 匯出格式選單樣式須與 `#template-select`（SDLCAIP2-36
已修復）一致；AC2 匯出按鈕樣式須與清除暫存／新錄音按鈕一致且移除
`.btn-success`；AC3 清除暫存／新錄音須靠右分組並與其他控制項有明顯間距
區隔；AC4 既有匯出行為（SDLCAIP2-35 既有測試）不受影響。純 HTML/CSS 修
正，不涉及後端或匯出邏輯。

## 介面/API 契約
無對外 HTTP API 變更。契約範圍限定在 `src/frontend/index.html` 的
`<style>` 區塊（新增一條 CSS 規則）與 `#view-result` 內操作區塊的 DOM 結構
（拆分 `.btn-row` 為左右兩個子分組、新增/變更部分 `id`／`class`）。

### 現況（`src/frontend/index.html`）

CSS（第 114-115 行，SDLCAIP2-36 已建立）：
```css
#template-select { font-size: .9rem; padding: 8px 10px; border: 1px solid var(--border);
                    border-radius: 6px; color: var(--text); font-family: inherit; }
```

HTML（第 296-314 行）：
```html
<div class="btn-row" style="align-items:center;">
  <span id="modified-badge">● 未儲存修改</span>
  <span id="low-confidence-badge">⚠ 偵測到的語言信心水準較低，逐字稿可能不夠準確</span>
  <label style="font-size:.8rem;color:var(--muted);">模板
    <select id="template-select"></select>
  </label>
  <button class="btn btn-outline btn-sm" id="regenerate-btn" onclick="regenerateSummary()">🔄 重新產生</button>
  <label style="font-size:.8rem;color:var(--muted);">匯出格式
    <select id="export-format-select">
      <option value="markdown">Markdown</option>
      <option value="plaintext">純文字</option>
      <option value="docx">Word</option>
      <option value="pdf">PDF</option>
    </select>
  </label>
  <button class="btn btn-success btn-sm" id="export-confirm-btn" onclick="exportSelectedFormat()">⬇ 匯出</button>
  <button class="btn btn-outline btn-sm" onclick="cleanupAndReset()">🗑 清除暫存</button>
  <button class="btn btn-outline btn-sm" onclick="showView('view-upload')">+ 新錄音</button>
</div>
```
注意：`cleanup-btn` / `new-recording-btn` 目前**沒有 `id` 屬性**（AC2/AC3 引
用的 `#cleanup-btn`、`#new-recording-btn` 目前不存在於 DOM）。

### 變更後

CSS，緊接第 115 行 `#template-select` 規則之後新增一條規則，選取器鎖定
`#export-format-select`，屬性值逐字沿用 `#template-select`（與其沿用
`.meeting-info-grid input` 的方式相同）：
```css
#export-format-select { font-size: .9rem; padding: 8px 10px; border: 1px solid var(--border);
                         border-radius: 6px; color: var(--text); font-family: inherit; }
```

HTML，第 296-314 行整段改為兩個並列的 `.btn-row` 子容器（沿用既有
`.btn-row` class 的 `display:flex;gap:10px;flex-wrap:wrap`，不新增排版用
CSS class，僅用 inline style 做一次性分組定位，與 SDLCAIP2-36 決策 1 的既
有慣例一致）：
```html
<div class="btn-row" style="align-items:center;">
  <div class="btn-row" id="result-action-group-content" style="align-items:center;">
    <span id="modified-badge">● 未儲存修改</span>
    <span id="low-confidence-badge">⚠ 偵測到的語言信心水準較低，逐字稿可能不夠準確</span>
    <label style="font-size:.8rem;color:var(--muted);">模板
      <select id="template-select"></select>
    </label>
    <button class="btn btn-outline btn-sm" id="regenerate-btn" onclick="regenerateSummary()">🔄 重新產生</button>
    <label style="font-size:.8rem;color:var(--muted);">匯出格式
      <select id="export-format-select">
        <option value="markdown">Markdown</option>
        <option value="plaintext">純文字</option>
        <option value="docx">Word</option>
        <option value="pdf">PDF</option>
      </select>
    </label>
    <button class="btn btn-outline btn-sm" id="export-confirm-btn" onclick="exportSelectedFormat()">⬇ 匯出</button>
  </div>
  <div class="btn-row" id="result-action-group-reset" style="align-items:center;margin-left:auto;">
    <button class="btn btn-outline btn-sm" id="cleanup-btn" onclick="cleanupAndReset()">🗑 清除暫存</button>
    <button class="btn btn-outline btn-sm" id="new-recording-btn" onclick="showView('view-upload')">+ 新錄音</button>
  </div>
</div>
```

具體變更點：
1. `#export-format-select`：新增上述 CSS 規則（AC1）。標記本身不變（不動
   `<option>` 內容）。
2. `#export-confirm-btn`：`class` 由 `btn btn-success btn-sm` 改為
   `btn btn-outline btn-sm`（AC2）。`onclick`、`id`、按鈕文字不變。
3. `cleanup-btn`／`new-recording-btn`：補上 `id="cleanup-btn"` /
   `id="new-recording-btn"`（目前缺失，AC2/AC3 斷言依賴這兩個 id 才能選取
   元素）。`class`、`onclick`、文字不變。
4. 外層 `.btn-row` 拆成兩個子 `.btn-row`：左側分組（`modified-badge`、
   `low-confidence-badge`、`template-select`、`regenerate-btn`、
   `export-format-select`、`export-confirm-btn`）與右側分組
   （`cleanup-btn`、`new-recording-btn`），右側分組加 `margin-left:auto`
   把整組推到容器最右（AC3）。
5. `#regenerate-btn` 的樣式與位置（左側分組內、原本相對順序）不變，符合
   範圍外排除項。

### 狀態碼
不涉及。純前端視覺/標記變更，不影響任何 API 呼叫或既有匯出行為
（AC4：`exportSelectedFormat()`、`exportMarkdown`／`exportPlainText`／
`exportServerFile` 的 JS 邏輯與呼叫參數不變）。

## 資料模型
無新增/變更資料模型。

## 關鍵技術決策

1. **`#export-format-select` 採獨立 ID 選擇器、屬性值逐字複製
   `#template-select`，而非抽出共用 class（如 `.result-select`）。**
   沿用 SDLCAIP2-36 決策 2 已建立的慣例（獨立 ID 規則優先於共用 class，
   保持關注點分離、變更影響面最小）；即使現在有兩個 select 需要相同樣
   式，CONSTITUTION「避免不必要的抽象層」原則下，兩處重複尚不構成需要
   抽出共用 class 的門檻，且維持與既有慣例一致比引入新抽象更重要。

2. **`#export-confirm-btn` 直接把 `class` 從 `btn-success` 換成
   `btn-outline`，不新增第三種按鈕樣式。** `.btn-outline` 已是清除暫存／
   新錄音按鈕使用的樣式，AC2 要求三者逐項相等，換成既有 class 是最小改
   動且天然保證屬性完全相等（不需要另外新增 CSS 規則、不會有數值謄寫誤
   差的風險）。`.btn-success` 規則本身予以保留在 `<style>` 內不刪除——
   分析已確認目前無其他使用處，但刪除該規則不是 AC 要求的範圍，保留不
   影響任何驗收條件，避免非必要的額外 diff。

3. **右側分組使用 `margin-left:auto` 推到容器最右，而非固定像素
   margin。** `.btn-row` 外層容器（第 291 行）為 `display:flex`，
   `margin-left:auto` 是 flexbox 慣用手法，能在「不換行」前提下（AC3 前
   提條件本身即隱含容器有剩餘寬度）保證右側分組與左側分組間的間距，必然
   大於或等於容器剩餘寬度，而右側分組內部（`.btn-row` 預設 `gap:10px`）
   兩顆按鈕彼此間距固定為 10px；只要測試在合理寬度（不觸發換行）下執行，
   分組間距必然大於固定 10px 的組內間距，滿足 AC3 兩個不等式，且不需要
   為此新增專屬 CSS class。

4. **補上 `cleanup-btn`／`new-recording-btn` 這兩個目前缺失的 `id`
   屬性。** 這不是新增功能或改變行為，純粹是讓 AC2/AC3 明確要求比對的
   `#cleanup-btn`／`#new-recording-btn` 選擇器在 DOM 中實際存在；`class`、
   `onclick`、按鈕文字皆不變，不影響既有任何測試或行為。

5. **左右分組沿用既有 `.btn-row` class（而非新增 `.btn-group-left` /
   `.btn-group-right` 之類的新 class），僅用 inline style 做
   `margin-left:auto` 這一次性排版調整。** 與 SDLCAIP2-36 決策 1 一致：
   元件視覺樣式進 `<style>` 區塊、一次性容器排版用 inline style；兩個子
   容器需要的排版（flex + gap）恰好與既有 `.btn-row` 完全相同，重複使用
   該 class 比新增等價的 class 更符合 CONSTITUTION「避免不必要的抽象
   層」。

## 開放設計問題（定稿時必須為空）
無。CSS 規則、class 置換、分組結構與新增的兩個 id 均可直接從 ticket 描述
的四條 AC 與既有程式碼（`.btn`、`.btn-outline`、`.btn-row`、
`#template-select`）推定，未發現規格未決的產品決策。
