# 設計文件 — SDLCAIP2-36 會議模板選擇區塊的視覺風格與頁面不一致

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-36）：`src/frontend/index.html` 第 293
行的 `#template-select`（`<label style="font-size:.8rem;color:var(--muted);">
模板<select id="template-select"></select></label>`）是一個沒有 CSS class、
也沒有專屬樣式規則的裸 `<select>`，是頁面上唯一沒有樣式的互動元件。修正
方式：比照既有的 `.meeting-info-grid input` 慣例（border、border-radius、
color、font-family）為它補上一致的視覺樣式。純 CSS／視覺修正，**不變更**
任何邏輯、不動其他下拉選單、不變更模板選擇的行為或 `<option>` 內容。

## 介面/API 契約
本故事不涉及對外 HTTP API（無新增/變更後端端點），也不新增/變更任何 DOM
結構或 JS 函式；契約範圍限定在既有 `<style>` 區塊新增一條 CSS 規則。

### 現況

樣式區（`src/frontend/index.html` 第 107–113 行，既有的
`.meeting-info-grid input` 規則，作為本次比照的基準）：
```css
.meeting-info-grid input { font-size: .9rem; padding: 8px 10px; border: 1px solid var(--border);
                            border-radius: 6px; color: var(--text); font-family: inherit; }
```

標記（`src/frontend/index.html` 第 292–294 行，`#template-select` 目前無
對應樣式規則、也無 class）：
```html
<label style="font-size:.8rem;color:var(--muted);">模板
  <select id="template-select"></select>
</label>
```

### 變更後

在既有 `<style>` 區塊內，緊接 `.meeting-info-grid` 相關規則群組之後（第
113 行 `.meeting-info-grid input::placeholder` 之後）新增一條規則，選取器
鎖定 `#template-select`，屬性值逐字沿用 `.meeting-info-grid input`：
```css
#template-select { font-size: .9rem; padding: 8px 10px; border: 1px solid var(--border);
                    border-radius: 6px; color: var(--text); font-family: inherit; }
```

第 292–294 行的 HTML 標記本身不變（`<select id="template-select"></select>`
維持原樣，不新增 class、不改變外層 `<label>` 的 inline style）。

### 狀態碼
不涉及。純視覺變更，不影響任何 API 呼叫或既有行為。

## 資料模型
無新增/變更資料模型。本故事純粹是 CSS 樣式規則的新增，不涉及任何資料表、
欄位、索引或前端資料結構。

## 關鍵技術決策

1. **新增獨立的 `#template-select { ... }` 規則於 `<style>` 區塊，而非把
   屬性值以 inline `style="..."` 直接寫在第 293 行的 `<select>` 標籤上。**
   檢視頁面既有慣例：所有「元件層級」樣式（`.btn`、`.card`、
   `#drop-zone`、`.meeting-info-grid input` 等）都定義在共用 `<style>`
   區塊內，inline style 只用於一次性的容器排版（如 flex 對齊、間距），
   從未用於元件的視覺風格（邊框、圓角、字色）本身；第 292 行外層
   `<label>` 的 inline style 屬於這類一次性排版用法，並非反例。沿用
   `<style>` 區塊規則與頁面既有的樣式組織方式一致，也讓 `#template-select`
   之後若要再統一調整仍只需改一處。

2. **選擇 `#template-select` ID 選擇器，而非新增一個共用 class（例如把
   `.meeting-info-grid input` 規則擴充成 `.meeting-info-grid input,
   #template-select`）。** Ticket 明確排除「變更其他下拉選單」的範圍；
   `#template-select` 不屬於任何 `.meeting-info-grid` 容器內，將其併入該
   class 選擇器會讓一條規則同時承擔兩個語義不同的容器，未來修改
   `.meeting-info-grid input` 時容易誤傷本元件。獨立 ID 規則屬性值雖與
   `.meeting-info-grid input` 重複，但保持關注點分離、變更影響面最小，
   符合本故事「只修這一個元件」的範圍。

3. **屬性值逐字沿用 `.meeting-info-grid input`（`font-size: .9rem`、
   `padding: 8px 10px`、`border: 1px solid var(--border)`、
   `border-radius: 6px`、`color: var(--text)`、`font-family: inherit`），
   不額外增減任何屬性。** Ticket 明文要求「與 `.meeting-info-grid input`
   慣例一致」，這是可直接從既有程式碼讀出的具體值，不需要另行判斷或
   引入新的視覺規範。

4. **不改動 `<option>` 內容、不改動 `template-select` 的任何 JS 邏輯
   （`templateSelect` 相關程式碼，第 1091、1387 行）。** Ticket 明確排除
   「模板選擇行為」的變更；依 CONSTITUTION「範圍紀律」，只做 spec 要求的
   視覺一致性修正，不順手處理其他非本故事範圍的項目。

## 開放設計問題（定稿時必須為空）
無。CSS 規則的選擇器策略、屬性值、插入位置均可由 ticket 描述與既有
`.meeting-info-grid input` 規則直接推定，未發現規格未決的產品決策。
