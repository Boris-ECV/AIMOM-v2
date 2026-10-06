# 設計文件 — SDLCAIP2-62 前端文案簡化與視覺微調（登入頁/處理中頁/頁首對齊/次要按鈕）

## 對應需求規格
G1 定稿版 AC1-AC4（2026-10-06 核准）：
- AC1：登入頁文案簡化（移除 🔐 icon、移除「請先登入才能使用」整行）
- AC2：處理中頁面文案簡化（`src/summarize.py:195`）
- AC3：頁首導覽列靠右修正（非管理者身分下右側群組未靠右對齊）
- AC4：`.btn-outline` 改淡灰底色，視覺權重需低於 `.btn-primary`

範圍外：後端 API/商業邏輯（AC2 僅為字串文案變更，不涉及行為）、`.btn-primary` 樣式、
e2e 測試範圍（留給 Testing 階段宣告）。

## 介面/API 契約
無新增對外 API。本 Story 僅修改既有靜態 HTML/CSS 與一處後端字串常數，具體異動點如下
（行號依 G1 核准時讀到的程式碼版本，developer 實作時請以實際 diff 內容比對為準，而非
硬性依賴行號）：

### AC1 — `src/frontend/index.html` 約 524-525 行
```html
<!-- Before -->
<h2 style="font-size:1.2rem;margin-bottom:8px;">🔐 會議錄音轉紀錄系統</h2>
<p>請先登入才能使用</p>

<!-- After -->
<h2 style="font-size:1.2rem;margin-bottom:8px;">會議錄音轉紀錄系統</h2>
```
（`<p>請先登入才能使用</p>` 整行刪除，其餘兄弟元素如 `<button>`、`#auth-error` 不動）

### AC2 — `src/summarize.py` 第 195 行
```python
# Before
update_progress(job_id, "summarizing", 70, "正在 AI 整理會議紀錄...")
# After
update_progress(job_id, "summarizing", 70, "正在整理會議紀錄...")
```
純字串常數變更，`update_progress` 函式簽章與呼叫方式不變，不影響其他呼叫點。

### AC3 — `src/frontend/index.html` 約 68-69 行（桌面 CSS）與 82-93 行（手機 media query）
```css
/* Before（約 68-69 行） */
.header-secondary { display: contents; } /* 桌面：讓子元素直接參與 header 的 flex 排版，維持單列 */
#admin-dashboard-btn { margin-left: auto; }

/* After */
.header-secondary {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-left: auto; /* SDLCAIP2-62: 錨點改放在一定會被渲染的容器本身，見關鍵技術決策 1 */
}
/* #admin-dashboard-btn 的 margin-left:auto 規則整條移除 */
```
手機 media query 區塊（約 82-93 行）`.header-secondary` 覆寫新增一行：
```css
@media (max-width: 479px) {
  .header-secondary {
    display: flex;
    order: 3;
    flex-basis: 100%;
    width: 100%;
    margin-left: 0; /* 新增：手機版已獨占一整列，取消桌面版的 auto 推擠 */
    align-items: center;
    gap: var(--ds-space-2);
    overflow-x: auto;
    background: rgba(0,0,0,0.14);
    padding: var(--ds-space-2) var(--ds-space-3);
  }
  .header-secondary #current-user-email { white-space: nowrap; }
}
```
HTML 結構（`<header>` 內部 markup，約 532-541 行）不需變動，`admin-dashboard-btn` 的
`style="display:none;"` 顯示/隱藏邏輯（JS 第 969 行）也不需變動。

### AC4 — `src/frontend/index.html` 約 148-150 行
```css
/* Before */
.btn-outline { background: var(--ds-surface); color: var(--ds-text-primary);
               border: 1px solid var(--ds-border-strong); }
.btn-outline:hover { background: var(--ds-badge-bg); }

/* After */
.btn-outline { background: var(--ds-bg); color: var(--ds-text-primary);
               border: 1px solid var(--ds-border-strong); }
.btn-outline:hover { background: var(--ds-badge-bg); }
```
僅改一行（base background token），hover 規則不動。此 class 為全站共用（16 處使用），
不建立 scoped override，見關鍵技術決策 3。

## 資料模型
無新增資料模型。

## 關鍵技術決策

1. **AC3 的 `margin-left:auto` 錨點改放在 `.header-secondary` 容器本身，而非其子元素**——
   根因是 `#admin-dashboard-btn { margin-left: auto }` 把「推到最右」的職責放在一個
   `display:none` 時會被整個移出 flex 排版的子元素上，該元素一旦不渲染，margin 規則
   自然無從生效，史上沒有其他規則接手。容器 `.header-secondary` 無論內部哪個子按鈕
   顯示/隱藏都一定會被渲染，是此處唯一穩定的錨點。
2. **`.header-secondary` 桌面版 `display` 由 `contents` 改為 `flex`**——`display:contents`
   的元素依規範會被瀏覽器當作「不存在的盒子」，margin/padding 等盒模型屬性一律被忽略
   （CSS Display Level 3），這正是決策 1 無法簡單地把 `margin-left:auto` 搬到
   `.header-secondary` 原樣式上的原因；改成真正的 `flex` 容器（內部用 `gap` 維持原本
   `contents` 時三個子元素之間的視覺間距）後，`margin-left:auto` 才能在 header 的主軸
   上生效，同時容器內部仍是一列，不影響原本「管理者身分」已經正確的排列順序。
3. **手機 media query 另外補上 `.header-secondary { margin-left: 0 }`**——手機版
   `.header-secondary` 本來就用 `flex-basis:100%` / `width:100%` 獨占一整列，若沿用桌面
   版新加的 `margin-left:auto`，在某些瀏覽器的 flex 主軸計算下可能把列內內容整個往右推
   擠出可視範圍（該列另有 `overflow-x:auto`），因此手機版明確歸零，與現有「手機版自成
   一列」的版型慣例一致。
4. **AC4 的淡灰色選用既有 token `--ds-bg`（`#F6F5F3`），而非新增 token**——該 token 已在
   `header` 的文字色（`color: var(--ds-bg)`，深底白字場景）中使用，語意上就是
   design-system 既有的「中性淺色」；沿用它可避免為單一元件新增一個僅用一次的顏色
   常數。`.btn-outline:hover` 維持原本 `var(--ds-badge-bg)`（`#EFEEEA`，略深一階）不變，
   使 base 與 hover 兩階仍保有可辨識的深淺差異（原本 base 是純白 `--ds-surface`，若保留
   hover 不動、只動 base，deeper-on-hover 的視覺回饋邏輯沒有被破壞）。
5. **`.btn-outline` 全站套用，不建立 scoped override**——spec 明確指出這是全站共用 class
   （16 處使用），且與 `.btn-primary` 的視覺權重對比是通用設計語言的一部分，不是結果頁
   專屬需求；這與 SDLCAIP2-44 既有「`.btn` 家族走 design-system token、全站統一」的慣例
   一致，沒有理由在此開特例做 scoped override（過度設計／不必要的抽象層，見
   CONSTITUTION 範圍紀律與程式碼風格）。
6. **AC1/AC2 純文案刪減，不引入任何新結構或 CSS**——兩者都是「移除既有內容」而非「新增
   行為」，依 CONSTITUTION 範圍紀律，直接依 spec 刪除對應文字即可，不需要額外設計決策。

## UI 原型
已建立 `docs/design/SDLCAIP2-62-prototype.html`——獨立靜態檔案，不依賴後端、不需要
server，可直接用瀏覽器開啟。內容涵蓋：
- 登入頁簡化後樣貌（AC1：無 icon、無副文案）
- 處理中頁「正在整理會議紀錄...」文案徽章（AC2）
- 頁首四種狀態並列展示（AC3）：桌面‧管理者／桌面‧非管理者／手機‧管理者／手機‧非
  管理者——手機版用 CSS Container Query（`container-type: inline-size` + `@container`）
  固定模擬 375px 寬容器，不受實際瀏覽器視窗寬度影響，讓審核者不必手動縮放視窗即可
  同時看到四種組合
- `.btn-primary` 與新版 `.btn-outline`（淡灰底）並列展示，含 hover 提示文字說明兩階
  灰階的差異

## 開放設計問題（定稿時必須為空）
無。
