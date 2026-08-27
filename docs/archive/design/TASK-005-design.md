# TASK-005 系統設計

## 架構說明

純前端修正，不涉及後端 API 變更。核心變更：
`/api/transcribe` 呼叫成功後，將回傳的 `segments`（含 speaker 欄位）直接儲存在
前端全域狀態 `state.segments` 中；`loadResults()` 改為讀取 `state.segments`，
不再另外呼叫 `/api/diarize`。`/api/diarize` 端點於後端保留（TASK-004 向下相容需求），
僅前端呼叫路徑移除。

## 模組清單

| 模組 | 檔案 | 職責 |
|------|------|------|
| 上傳流程 | `src/frontend/index.html`（`doUpload`） | 上傳後依序呼叫 transcribe→summarize，並保存 segments 至 state |
| 結果載入 | `src/frontend/index.html`（`loadResults`） | 改用 `state.segments` 渲染逐字稿，不再呼叫 diarize |
| 進度顯示 | `src/frontend/index.html`（`updateProgressUI`） | 已於前次變更完成 3 階段顯示，本次僅確認無需再調整 |

## 資料流變更

```
舊：doUpload() -> transcribe -> summarize
    loadResults() -> summarize（重複呼叫，僅取快取結果）-> diarize（取得 segments）

新：doUpload() -> transcribe（結果存入 state.segments）-> summarize（結果存入 state.minutes）
    loadResults() -> 直接使用 state.segments / state.minutes，不再呼叫任何 API
```

## DB Schema

不適用（無資料庫變更）。

## 注意事項

- `state.segments` 若在頁面重新整理後遺失（無持久化），逐字稿頁面應顯示提示訊息，
  但此為既有限制，不在本工單範圍內調整。
- 保留 `/api/diarize` 後端端點呼叫能力（供未來或其他用途），僅移除前端呼叫。
