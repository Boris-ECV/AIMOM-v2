# PRD — 會議錄音自動轉會議紀錄系統
**文件版本：** v2.3
**建立者：** ba-agent（需求訪談）
**建立時間：** 2026-07-09T11:55:00
**最後更新：** 2026-08-04T14:30:00（v2.3 — AI 會議紀錄新增會議資訊（日期/時間/地點/參與者）欄位，未提及不臆測；action_items 的 owner/due 未提及不臆測；摘要長度依會議長度放寬至 300-500 字）
**工單：** TASK-001
**狀態：** ✅ Approved

---

## 變更紀錄

| 版本 | 日期 | 說明 |
|------|------|------|
| v1.0 | 2026-07-09 | 初版，使用 OpenAI Whisper + pyannote.audio |
| v2.0 | 2026-07-09 | 語音轉錄 + 說話者識別改用 AssemblyAI，移除 pyannote 依賴 |
| v2.1 | 2026-07-13 | AI 摘要整理預設引擎改為 **GitHub Models**（OpenAI 相容端點，搭配 GitHub Copilot Business/Enterprise 帳號），OpenAI GPT-4o 保留為可切換選項；修正 AssemblyAI 模型代號 `universal-3-pro` → `universal-3-5-pro`（對應 SDK API 變更，`speech_model` 單數參數已棄用，改用 `speech_models` 陣列）；AssemblyAI transcript 刪除（隱私需求）已於 TASK-006 完成實作 |
| v2.2 | 2026-08-04 | AI 摘要引擎新增 **Bedrock proxy** 可切換選項，預設改為 `bedrock-proxy`；支援透過 OpenAI 相容端點呼叫 Bedrock proxy，並保留 GitHub Models / OpenAI GPT-4o / Groq / Gemini 切換；修正 Lambda 環境變數值前後空白會導致 LLM 端點驗證失敗的問題 |
| v2.3 | 2026-08-04 | AI 會議紀錄新增 **會議資訊**（日期/時間/地點/參與者）欄位，逐字稿未提及一律不臆測，結果頁面提供可編輯欄位供使用者手動填寫/修正；`action_items` 的 owner/due 未明講時同樣不可臆測，維持空字串；摘要長度由固定 100-200 字改為依會議長度彈性調整（可放寬至 300-500 字） |

---

## 一、背景與目標

### 背景

團隊日常有大量會議，但會議紀錄製作耗時且容易漏記待辦事項與決議。
目前以人工方式整理，效率低、品質不穩定。

### 目標

建立一套 **Web 介面的 AI 輔助系統**，讓使用者上傳本地會議錄音檔，
系統自動完成語音轉文字、發言人識別、摘要整理，輸出結構化的 Markdown 會議紀錄。

### 成功指標（MVP）

- 一場 2 小時以內的會議，從上傳到產出紀錄 < 10 分鐘
- 會議紀錄涵蓋：摘要、待辦事項、決定事項（自動識別）
- 發言人區段正確率 > 80%（中英混合場景）

---

## 二、目標用戶

| 角色 | 描述 | 主要需求 |
|------|------|---------|
| **會議主持人** | 負責開會與跟進行動項目 | 快速取得 Action Items，分派給成員 |
| **與會成員** | 需要回顧會議內容 | 確認自己的待辦事項與決議 |
| **主管 / 利害關係人** | 未出席但需要摘要 | 快速了解會議結論與決定事項 |

**使用場景：** 團隊內部共用（非企業級多租戶，MVP 階段單一部署）

---

## 三、核心功能需求（FR）

### FR-01：錄音檔上傳

- 支援格式：MP3、WAV、M4A（常見錄音格式）
- 最大長度：2 小時
- 最大檔案大小：上限 **2GB**（AssemblyAI 支援最大 5GB，本系統限制 2GB）
- 介面：Web 拖拽上傳 or 點選上傳
- ✅ v2.0：移除 25MB 分段限制（原 Whisper API 限制），無需前端分段邏輯

### FR-02：語音轉文字（Transcription）

- 語言：**中英混合**（繁體中文 + 英文，台灣口音）
- AI 引擎：**AssemblyAI**（v2.0 預設，取代 OpenAI Whisper）
  - 模型：`universal-2`（預設）或 `universal-3-5-pro`（可設定，v2.1 修正代號）
  - 費用：$0.15/hr（universal-2）/ $0.21/hr（universal-3-5-pro）
  - v2.1：SDK API 變更，`TranscriptionConfig` 改用 `speech_models`（陣列）取代已棄用的 `speech_model`（單一列舉）
- 輸出：帶時間戳的逐字稿（含發言人標記，一次 API 完成）
- ✅ v2.0：轉錄與說話者識別**合併為單一 API 呼叫**

### FR-03：發言人識別（Speaker Diarization）

- **✅ v2.0：由 AssemblyAI 原生提供，無需額外工具**（移除 pyannote.audio 依賴）
- 費用：**+$0.02/hr**（加購 Speaker Identification add-on）
- 自動識別不同發言人，以 `SPEAKER_A / SPEAKER_B / SPEAKER_C...` 標記
- 使用者可在結果頁面**手動修改發言人名稱**
- 顯示格式：
  ```
  [00:03:25] 發言者 A：我們下週要完成這個功能...
  [00:03:40] 發言者 B：好，我來負責前端部分。
  ```
- ✅ v2.0：移除 PYANNOTE_ENABLED / HuggingFace Token 等設定

### FR-04：AI 會議紀錄整理

- 根據逐字稿，由 LLM 自動整理出結構化會議紀錄
- AI 引擎：可切換（v2.2 預設 **Bedrock proxy**（OpenAI 相容端點，預設模型 `mistral.mistral-large-3-675b-instruct`），可切回 GitHub Models / OpenAI GPT-4o / Groq / Gemini）
- 輸出包含：
  1. **🗓 會議資訊**：日期、時間、地點、參與者。這些資訊**只能**依逐字稿中明確提及的內容填寫，
     未提及一律留空（participants 為空陣列），AI 不可臆測；結果頁面提供對應欄位供使用者手動填寫/修正
  2. **📋 會議摘要**：長度依會議長短彈性調整（短會議約 100-200 字，長會議可放寬至 300-500 字），說明這場會議的主要討論方向與結論
  3. **✅ 待辦事項（Action Items）**：`負責人 - 事項描述 - 預計完成日（若有提及）`；owner/due 未明講則留空，AI 不可臆測填入人名或日期
  4. **⚖️ 決定事項（Decisions）**：本次會議確定拍板的決議
  5. **📝 討論重點**：各主要議題的討論摘要（依話題分段）

### FR-05：結果瀏覽與編輯

- Web 頁面顯示生成的會議紀錄
- 使用者可**直接在頁面上編輯**（inline edit）後下載
- 支援切換顯示模式：`會議紀錄` / `逐字稿`

### FR-06：匯出 Markdown

- 下載按鈕，將最終會議紀錄匯出為 `.md` 檔案
- 檔名格式：`YYYYMMDD-meeting-notes.md`

### FR-07：AI 引擎設定

- 透過 `.env` 設定檔管理 API Key 與模型選擇
- 支援切換：
  - 語音辨識 + 說話者識別：`assemblyai`（v2.0 預設）
  - 文字整理：`bedrock-proxy`（v2.2 預設，OpenAI 相容 proxy 端點）/ `github-models` / `openai-gpt4o` / `groq` / `gemini`
- ✅ v2.0：移除 `openai-whisper` / `google-speech` / `whisper-local` 選項
- 必要設定：
  ```
  ASSEMBLYAI_API_KEY=...
  ASSEMBLYAI_MODEL=universal-2        # 或 universal-3-5-pro
  ASSEMBLYAI_SPEAKER_DIARIZATION=true
  LLM_ENGINE=bedrock-proxy            # 或 github-models / openai-gpt4o / groq / gemini
  LLM_MODEL=mistral.mistral-large-3-675b-instruct
  BEDROCK_PROXY_BASE_URL=...
  BEDROCK_PROXY_API_KEY=...
  GITHUB_TOKEN=...                    # LLM_ENGINE=github-models 時使用（PAT 需 models scope）
  OPENAI_API_KEY=...                  # LLM_ENGINE=openai-gpt4o 時使用
  GROQ_API_KEY=...                    # LLM_ENGINE=groq 時使用
  GEMINI_API_KEY=...                  # LLM_ENGINE=gemini 時使用
  ```

---

## 四、非功能需求（NFR）

### NFR-01：隱私保護

- 錄音檔**僅在處理期間使用**，處理完成後自動刪除暫存
- **不長期儲存**使用者錄音於伺服器
- ✅ v2.0：AssemblyAI 資料隱私政策：音檔上傳後處理，預設 72 小時後自動刪除；可呼叫 `DELETE /transcript/{id}` 即時刪除
- API 傳送給 AssemblyAI / OpenAI 的資料，遵循其 API 使用條款

### NFR-02：效能

- 1 小時錄音，轉錄完成時間 < **3 分鐘**（AssemblyAI 比 OpenAI Whisper 快）
- 頁面回應時間 < 2 秒（非 AI 處理階段）
- 顯示處理進度條（避免使用者等待時不知狀態）
- ✅ v2.0：AssemblyAI 非同步 API，後端以輪詢方式（每 3 秒）取得進度

### NFR-03：技術規格

- **後端**：Python FastAPI
- **前端**：HTML/CSS/JavaScript（單一 index.html）
- **語音轉錄 + 說話者識別**：**AssemblyAI SDK**（v2.0，取代 OpenAI Whisper + pyannote）
- **AI 摘要整理**：OpenAI GPT-4o（可切換）
- **部署**：本地執行（`python app.py`），或 Docker 容器化

### NFR-04：可用性

- 支援現代瀏覽器（Chrome / Firefox / Edge / Safari）
- 單一使用者操作，非多人同時使用（MVP 階段）

---

## 五、系統流程

```
使用者上傳錄音檔
      ↓
[後端] 接收檔案，存入暫存路徑
      ↓
[AssemblyAI] 上傳音檔至 AssemblyAI，取得 transcript_id
      ↓
[AssemblyAI] 非同步處理（轉錄 + 說話者識別 同一次 API）
      ↓  後端每 3 秒輪詢 GET /transcript/{id}
[AssemblyAI] 處理完成 → 取得逐字稿 + 說話者標記
      ↓
[GPT-4o] 根據逐字稿生成：摘要 / Action Items / 決定事項 / 討論重點（v2.1：預設呼叫 GitHub Models，可切回 OpenAI GPT-4o）
      ↓
[前端] 顯示會議紀錄 + 提供編輯
      ↓
使用者編輯後，下載 Markdown
      ↓
[後端] 刪除暫存錄音檔 + 呼叫 AssemblyAI DELETE /transcript/{id}
```

---

## 六、MVP 範圍界定

### ✅ MVP 包含（v1.0 / v2.0）

| 功能 | 說明 | v2.0 變更 |
|------|------|---------|
| FR-01 | 本地上傳 MP3/WAV/M4A，最大 2 小時 | 檔案上限提升至 2GB |
| FR-02 | 語音轉文字（中英混合） | 改用 AssemblyAI |
| FR-03 | 發言人識別（A/B/C 標記）+ 手動改名 | 改用 AssemblyAI 原生，移除 pyannote |
| FR-04 | LLM 整理會議紀錄（4 大區塊） | v2.1：預設引擎改為 GitHub Models，OpenAI 保留可切換 |
| FR-05 | Web 結果頁面 + inline 編輯 | 不變 |
| FR-06 | 匯出 Markdown | 不變 |
| FR-07 | .env 設定 AI 引擎 | v2.1：新增 GITHUB_TOKEN / LLM_ENGINE=github-models |
| NFR-01 | 暫存處理，不長期儲存 | 加入 AssemblyAI transcript 刪除 |
| NFR-03 | Python FastAPI + HTML | 不變 |

### ❌ MVP 不包含（後續版本）

| 功能 | 說明 |
|------|------|
| 歷史記錄查詢 | 過去會議紀錄的儲存與搜尋 |
| 匯出 Word/PDF | 僅 Markdown，後續可加 |
| Zoom/Teams 直接整合 | 雲端錄影連接，後續版本 |
| 使用者帳號系統 | 單人使用，無需登入 |
| 批次處理多份錄音 | 一次上傳一個檔案 |

---

## 七、技術架構（v2.0）

```
┌─────────────────────────────────────────────────────┐
│                    Browser（前端）                     │
│  上傳元件 → 進度顯示 → 結果頁面（編輯 + 切換）→ 下載   │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP
┌─────────────────────▼───────────────────────────────┐
│               Python FastAPI                         │
│                                                     │
│  POST /upload         → 接收錄音，存暫存              │
│  POST /transcribe     → 上傳至 AssemblyAI，啟動轉錄   │
│  GET  /status/{id}    → 輪詢 AssemblyAI 進度          │
│  POST /summarize      → 呼叫 GPT-4o，生成會議紀錄     │
│  DELETE /cleanup/{id} → 刪除暫存 + AssemblyAI transcript│
└──────────┬───────────────────────┬──────────────────┘
           │                       │
┌──────────▼──────────┐  ┌────────▼──────────────────┐
│     AssemblyAI API  │  │  GitHub Models / OpenAI     │
│  ✅ 轉錄 + 說話者識別│  │  摘要 / Action / Decisions  │
│  universal-2 model  │  │  預設 GitHub Models         │
│  $0.085/場（30分鐘） │  │  （可切回 OpenAI GPT-4o）   │
└─────────────────────┘  └────────────────────────────┘
```

---

## 八、開放問題（v2.0 更新）

| 問題 | 說明 | 狀態 |
|------|------|--------|
| ~~Speaker Diarization 實作~~ | ~~需搭配 pyannote.audio，有授權問題~~ | ✅ v2.0 改用 AssemblyAI 原生解決 |
| ~~長音訊分段策略~~ | ~~Whisper API 25MB 限制~~ | ✅ v2.0 AssemblyAI 支援 5GB，無需分段 |
| 前端框架選擇 | 純 HTML + Fetch API（已確認） | ✅ 已決定 |
| 部署方式 | 本地 or Docker | 低優先，後續決定 |
| AssemblyAI transcript 刪除 | 處理完後需呼叫 DELETE /transcript/{id} 確保隱私 | ✅ TASK-006 已完成實作 |
| AI 摘要引擎選型 | OpenAI 額度/計費問題導致無法穩定測試 | ✅ v2.1 改預設 GitHub Models，OpenAI 保留可切換 |

---

## 九、訪談記錄摘要

| 問題 | 使用者回答 |
|------|-----------|
| 錄音來源 | 本地上傳（MP3/WAV/M4A） |
| 語言 | 中英混合（繁體中文 + 英文） |
| 輸出格式 | Markdown |
| 紀錄內容 | 摘要 + 待辦事項 + 決定事項 |
| 發言人識別 | 需要 |
| 使用者 | 團隊內部共用 |
| AI 引擎 | 可切換（設定檔配置） |
| 介面 | Web 瀏覽器 |
| 語言（開發） | Python |
| 錄音長度上限 | 2 小時 |
| MVP 範圍 | 上傳 + 轉錄 + AI 整理會議紀錄 |
| 隱私需求 | 暫存使用，不長期儲存 |
