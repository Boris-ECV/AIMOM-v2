# TASK-005 需求文件

## 背景

TASK-004 已將後端轉錄流程改為 AssemblyAI（轉錄與說話者識別合併為單一 API 呼叫）。
前端目前處理流程雖已部分調整（`doUpload()` 已移除獨立 diarize 呼叫），
但 `loadResults()` 仍殘留呼叫 `/api/diarize` 以取得逐字稿分段，
與 AC「callStep 不再呼叫 /api/diarize」不符，需修正。

## 功能需求

- FR-01：上傳完成後的處理流程僅呼叫 `/api/transcribe` → `/api/summarize` 兩個步驟，不再呼叫 `/api/diarize`。
- FR-02：進度頁面顯示 3 個階段（上傳完成 → AssemblyAI 處理中 → AI 整理完成），不再顯示獨立的「發言人識別」階段。
- FR-03：`/api/transcribe` 回傳的逐字稿分段（含 speaker 欄位）需保存於前端狀態（`state.segments`），供結果頁與逐字稿頁使用，不再於載入結果時重新呼叫 `/api/diarize`。
- FR-04：發言人重新命名、Inline 編輯、Markdown 匯出等既有功能不受影響。

## 非功能需求

- NFR-01：前端變更不得影響既有 API 契約（`/api/diarize` 端點仍保留於後端以維持向下相容，僅前端不再呼叫）。
- NFR-02：進度輪詢邏輯（setInterval）不需改動，僅調整顯示文字與百分比對應。

## 使用者故事

作為使用者，我想要在處理進度頁面看到與實際後端流程一致的階段顯示，
以便正確理解目前處理到哪個步驟，不被過時的「發言人識別」階段誤導。

## 流程說明

1. 使用者上傳錄音檔 → `doUpload()`
2. 依序呼叫 `/api/transcribe`（內含說話者識別，回傳 segments）→ `/api/summarize`
3. `loadResults()` 直接使用步驟 2 儲存於 `state.segments` 的資料渲染逐字稿頁面，不再呼叫 `/api/diarize`
4. 使用者可於結果頁進行發言人重命名、Inline 編輯、匯出 Markdown

## 資料需求

- 輸入：無新增，沿用既有 `/api/transcribe` 回傳的 `segments`（`start`, `end`, `text`, `speaker`）
- 輸出：無新增，僅調整前端狀態管理方式

## 邊界條件

- 若 `/api/transcribe` 回傳空 segments，結果頁應顯示「無逐字稿內容」而非呼叫 diarize 補救。
- 舊版瀏覽器快取（若有殘留呼叫 `/api/diarize` 的行為）不在此次修正範圍內（僅原始碼修正）。

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-09T18:10:00 | orchestrator | 建立工單，放入 backlog（depends_on TASK-004） |
| 2026-07-13T11:52:00 | ba-agent | 需求分析完成，撰寫需求文件；移動工單至 design/ |
