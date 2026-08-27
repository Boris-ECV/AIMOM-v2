# TASK-003 前端需求規格
**建立者：** ba-agent | **時間：** 2026-07-09T13:09:00
**參考 PRD：** `docs/requirements/TASK-001-prd.md`

---

## 功能需求

### FR-01：錄音上傳介面
- 拖拽區域（Drag & Drop）+ 點選按鈕兩種上傳方式
- 顯示選取檔名、大小、預估時長
- 前端驗證：僅接受 .mp3/.wav/.m4a，提示檔案限制
- 上傳中顯示 spinner，完成後自動導向進度頁

### FR-02：處理進度顯示
- 顯示 4 個處理階段：上傳(10%) → 轉錄(40%) → 識別(65%) → 整理(100%)
- 進度條動態更新（輪詢 /api/status/{job_id}，每 2 秒一次）
- 顯示目前階段說明文字（來自 status.message）
- 完成後自動跳轉結果頁

### FR-03：會議紀錄結果頁
- 4 個顯示區塊：
  1. **摘要**（文字段落）
  2. **待辦事項**（owner / task / due 三欄表格）
  3. **決定事項**（條列清單）
  4. **討論重點**（議題標題 + 摘要，可展開）
- Tab 切換：紀錄 / 逐字稿
- 逐字稿：時間戳 + 發言人 + 文字三欄顯示

### FR-04：發言人重命名
- 逐字稿頁面上方顯示發言人清單
- 點擊發言人標籤 → 輸入框可修改名稱
- 修改後即時更新整頁所有對應發言人文字

### FR-05：Inline 編輯
- 摘要、待辦事項、決定事項可雙擊進入編輯模式
- 編輯完按 Enter 或點空白處儲存
- 右上角「已修改」徽章提示未匯出的修改

### FR-06：匯出 Markdown
- 按鈕觸發下載 `.md` 檔案
- 檔名格式：`YYYYMMDD-meeting-notes.md`
- 包含：標題、日期、摘要、Action Items、決定事項、逐字稿

---

## 技術規格

- 純 HTML + CSS + Vanilla JS（無框架，單一 `index.html`）
- 後端 API Base URL：`http://localhost:8000`
- 狀態管理：`window.meetingState` 全域物件
- 輪詢：`setInterval` 每 2 秒 GET /api/status/{job_id}
- 本地狀態：localStorage 儲存 job_id，刷頁不遺失

---

## 非功能需求
- NFR-01：頁面載入 < 2 秒（純靜態）
- NFR-02：進度更新延遲 ≤ 2 秒
- NFR-03：支援 Chrome / Firefox / Edge（最新版）
- NFR-04：桌面優先，min-width: 1024px
