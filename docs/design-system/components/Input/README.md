# Input（文字輸入框／下拉選單）

表單欄位的標準樣式，涵蓋文字輸入框與下拉選單。

## 規格

- 一律搭配 `<label>`（使用 `for` 對應 `id`），不單獨放 placeholder 當作標籤。
- 高度：桌面 `control-h-desktop`（40px）、手機 `control-h-mobile`（44px）。
- 邊框：`border-strong`，圓角 `radius-sm`。
- Label 文字樣式：`caption`（桌面）／`caption-mobile`（手機），顏色 `text-secondary`。
- Placeholder 顏色固定為 `text-placeholder`，不使用一般文字色，避免使用者誤以為已經填寫。
- Focus：2px `focus-ring` 外框、`outline-offset: 2px`。這是必要規則，原稿版本完全沒有 focus 樣式，鍵盤使用者無法辨識目前所在欄位。

## 版面規則

- 桌面版多欄位並排時使用 grid（例如日期／時間／地點三欄），欄位間距 `space-4`（20px）。
- 手機版一律收成單欄，欄位垂直間距 `space-3`（16px）。
- 欄位寬度在手機版一律 `width:100%`，並設定 `box-sizing:border-box` 避免 padding 撐破容器寬度。
