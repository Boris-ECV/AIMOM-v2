# TASK-002 交付報告 — 後端核心服務
**建立者：** devops-agent | **時間：** 2026-07-09T13:07:30

---

## 交付狀態：✅ PASSED

## 交付物清單

| 檔案 | 說明 |
|------|------|
| `src/app.py` | FastAPI 主程式，掛載 5 個 router |
| `src/config.py` | 環境設定、引擎工廠函式 |
| `src/models.py` | Pydantic 資料模型 |
| `src/upload.py` | POST /api/upload |
| `src/transcribe.py` | POST /api/transcribe（含音訊分段） |
| `src/diarize.py` | POST /api/diarize（含降級模式） |
| `src/summarize.py` | POST /api/summarize |
| `src/progress.py` | GET /api/status + DELETE /api/cleanup |
| `src/requirements.txt` | 依賴套件清單 |
| `src/.env.example` | 環境設定範本 |
| `src/tests/test_upload.py` | 上傳測試 |
| `src/tests/test_transcribe.py` | 轉錄測試 |
| `src/tests/test_diarize.py` | 發言人識別測試 |
| `src/tests/test_summarize.py` | AI 整理測試 |
| `src/tests/test_progress.py` | 進度/清理測試 |

## 部署步驟

```bash
cd src
pip install -r requirements.txt
cp .env.example .env
# 編輯 .env，填入 OPENAI_API_KEY
python app.py
# 服務啟動於 http://localhost:8000
```

## API 文件

啟動後可至 `http://localhost:8000/docs` 檢視 Swagger UI

## 品質指標

- Review: ✅ 12/12 AC 通過
- QA: ✅ 15 測試案例通過
- 測試檔案: 5 個，覆蓋所有主要邏輯路徑
