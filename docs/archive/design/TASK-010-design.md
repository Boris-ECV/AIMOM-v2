# TASK-010 系統設計 — 多格式匯出（Word/PDF/純文字）

## 架構說明

- **Word/PDF**：後端產生。新增 `src/export.py`，讀取 `tmp/{job_id}/minutes.json`，
  使用 `python-docx` 產生 `.docx`，`reportlab` 產生 `.pdf`。
- **純文字**：前端直接由畫面上已渲染的內容組字串產生 Blob 下載，不呼叫後端（沿用既有 Markdown 匯出的模式）。

## 中文字型方案

PDF 中文顯示採用 reportlab 內建 CID 字型 `MSung-Light`（繁體中文，Adobe 標準 CID 字型，
不需外部字型檔案、Lambda 環境可直接使用，避免 `weasyprint` 需要原生 GTK/Pango 相依套件的問題）。

## 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/export/{job_id}?format=docx` | 產生並回傳 Word 檔 |
| GET | `/api/export/{job_id}?format=pdf` | 產生並回傳 PDF 檔 |

## 前端變更

新增三個按鈕：「匯出純文字」「匯出 Word」「匯出 PDF」，與既有「匯出 Markdown」並列。
