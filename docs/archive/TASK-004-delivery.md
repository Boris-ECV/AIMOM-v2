# AssemblyAI 遷移交付報告（TASK-004/005/006）
**建立者：** devops-agent | **時間：** 2026-07-09T18:32:30

---

## 交付狀態：✅ PASSED

## 變更摘要

| 工單 | 內容 | 狀態 |
|------|------|------|
| TASK-004 | 後端改用 AssemblyAI | ✅ |
| TASK-005 | 前端進度顯示調整（3 階段） | ✅ |
| TASK-006 | 隱私強化：transcript 自動刪除 | ✅（含於 TASK-004） |

## 修改檔案清單

| 檔案 | 變更類型 | 說明 |
|------|---------|------|
| `src/config.py` | 重寫 | 移除 Whisper/pyannote，加入 AssemblyAI 設定 |
| `src/transcribe.py` | 重寫 | assemblyai SDK，含說話者識別 |
| `src/diarize.py` | 簡化 | 讀已有 speaker 欄位，向下相容 |
| `src/progress.py` | 修改 | cleanup 加入 AssemblyAI transcript 刪除 |
| `src/requirements.txt` | 更新 | 移除 pydub/pyannote，加入 assemblyai |
| `src/.env.example` | 更新 | ASSEMBLYAI_API_KEY 設定 |
| `src/tests/test_transcribe.py` | 更新 | Mock AssemblyAI SDK |
| `src/tests/test_diarize.py` | 更新 | 測試 speaker labels 讀取 |
| `src/tests/test_progress.py` | 更新 | 測試 AssemblyAI 刪除邏輯 |
| `src/frontend/index.html` | 修改 | 3 階段進度，移除 /diarize 呼叫 |

## 成本效益

| 項目 | 改前 | 改後 |
|------|------|------|
| 30分鐘/場費用 | $0.18（OpenAI Whisper）| **$0.085（AssemblyAI）** |
| 說話者識別 | 需 pyannote（授權問題）| **原生支援** |
| 分段邏輯 | 需要（25MB 限制） | **不需要（5GB 支援）** |
| 外部依賴 | pyannote + pydub + mutagen | **assemblyai + mutagen** |

**節省 53% 費用，移除 pyannote 授權問題**

## 部署步驟

```bash
pip install -r requirements.txt   # 安裝 assemblyai
cp .env.example .env
# 填入 ASSEMBLYAI_API_KEY（從 assemblyai.com 取得）
python app.py
```
