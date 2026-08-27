# TASK-010 交付報告 — 多格式匯出

## 完成內容

- `src/export.py`：`GET /api/export/{job_id}?format=docx|pdf`，後端使用 `python-docx`/`reportlab` 產生檔案並以 `StreamingResponse` 回傳（附正確 `Content-Disposition`）
- PDF 中文顯示：採用 reportlab 內建 CID 字型 `MSung-Light`，經測試可正常顯示繁體中文，不需外部字型檔
- `app.py`：掛載 `export_router`
- `frontend/index.html`：新增「匯出純文字」（前端 Blob 直接產生）、「匯出 Word」「匯出 PDF」（呼叫後端 API）三個按鈕
- `tests/test_export.py`：4 項測試（docx 成功、pdf 成功且驗證 PDF magic bytes、找不到資料 404、不支援格式 400）

## 測試結果

```
31 passed（全專案，含既有 27 項）
```

## 驗收對應（PRD FR-10）

| AC | 狀態 |
|----|------|
| Word 匯出（後端） | ✅ python-docx |
| PDF 匯出（後端，中文正常顯示） | ✅ reportlab + MSung-Light CID 字型 |
| 匯出內容涵蓋摘要/待辦/決定事項 | ✅ |
| 純文字匯出（前端） | ✅ Blob 直接下載 |
| 找不到資料回 404 | ✅ |
| 單元測試 | ✅ 4 項通過 |

## 已知限制

- PDF 內容未涵蓋逐字稿全文（僅摘要/決定/待辦事項），與 Markdown/純文字匯出內容範圍不同；如需完整逐字稿版本可於下版擴充
- 匯出僅支援目前處理中之 `job_id`（暫存資料），尚未支援對歷史紀錄（`meeting_id`）直接匯出，可作為後續小增強
