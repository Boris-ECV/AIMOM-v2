# PRD v2 — 會議錄音自動轉會議紀錄系統（雲端化擴充）
**文件版本：** v1.0
**建立者：** ba-agent（需求訪談）
**建立時間：** 2026-07-13T18:30:00
**工單：** TASK-007
**狀態：** ✅ Approved
**前版依據：** `poc-sdlc-copilot2` MVP（本機 FastAPI POC，AssemblyAI + 可切換 LLM 引擎），該專案維持不變、獨立作為本機 POC 參考

---

## 變更紀錄

| 版本 | 日期 | 說明 |
|------|------|------|
| v1.0 | 2026-07-13 | 初版。從本機 MVP 進化為 AWS Serverless 正式版，新增歷史紀錄、多格式匯出、登入、成本儀表板 |

---

## 一、背景與目標

### 背景

MVP（`poc-sdlc-copilot2`）已驗證核心流程可行：上傳錄音 → AssemblyAI 轉錄+說話者識別 → LLM 摘要整理 → 匯出 Markdown。目前為本機單人測試版本，沒有登入機制、沒有歷史紀錄、只有一種匯出格式，且部署方式僅限本機執行。

團隊決定將此 POC 正式化為小團隊可用的雲端服務，並選擇 **AWS Lambda 為核心運算平台**，以低成本、免維運為優先考量。本專案（**AIMOM**）為此正式開發的獨立 codebase，`poc-sdlc-copilot2` 保留作為本機 POC 對照，不再修改。

### 目標

在維持 MVP 核心轉錄/摘要能力的基礎上：
1. 讓使用者可以選擇保留會議紀錄，並在 14 天內隨時查閱
2. 提供多格式匯出（不只 Markdown）
3. 導入登入機制與角色權限，符合團隊內部治理需求
4. 讓管理者掌握 AI 服務的成本與用量
5. 整套系統以 AWS Serverless 架構部署，維持小團隊使用下的低成本

### 成功指標

- 沿用 MVP 的效能指標（2 小時會議 < 10 分鐘完成）
- 歷史紀錄查詢回應 < 2 秒
- 到期資料 100% 自動清除，無需人工介入
- 小團隊（預估 <20 人）月用量下，AWS 各項服務盡量落在免費額度或極低成本內

---

## 二、目標用戶

| 角色 | 描述 | 主要需求 |
|------|------|---------|
| **一般使用者**（會議主持人/與會成員） | 需登入才能使用系統 | 上傳、查詢自己保留的會議紀錄、匯出多格式 |
| **管理者** | 白名單 email 認定的內部管理者 | 監控 LLM 引擎使用量與成本 |

**使用場景：** 團隊內部共用，需登入（Google 帳號），非公開服務。

---

## 三、核心功能需求（FR）

延續 MVP 既有的 FR-01～FR-07（上傳、轉錄、發言人識別、AI 摘要、結果編輯、AI 引擎設定），本版新增／變更如下：

### FR-08：登入與身分驗證（新增）

- 全站所有功能皆須登入，採 **Google 第三方登入（OAuth，透過 Amazon Cognito User Pool 聯合 Google IdP）**
- 登入後以 email 判斷角色：
  - 屬於**白名單 email** → 管理者角色
  - 其他已登入使用者 → 一般使用者角色
- 未登入者導向登入頁，無法存取任何 API

### FR-09：會議紀錄歷史（新增）

- 每次轉錄+摘要處理完成後，使用者可選擇：
  - **保留**：進入「歷史紀錄」清單，可隨時查閱
  - **刪除**：不進入歷史紀錄，本次結果不再保存
- **音檔一律於處理完成後刪除**（不論是否選擇保留會議紀錄），前端須明確提示使用者「錄音檔已刪除，僅保留文字紀錄」
- 保留的會議紀錄（僅文字：逐字稿+摘要）**最長保存 14 天**，到期自動刪除
- 使用者可在到期前，於歷史紀錄清單中**手動提前刪除**任一項目
- 使用者僅能查看**自己**上傳/保留的歷史紀錄，無法看到其他使用者的資料

### FR-10：多格式匯出（取代原 FR-06，擴充範圍）

- 支援匯出格式：**Markdown（既有）／純文字（.txt）／Word（.docx）／PDF**
- 純文字：**前端瀏覽器端**直接產生（Blob 下載），無需呼叫後端
- Word／PDF：**後端產生**（`python-docx` 產生 .docx；`reportlab` 產生 PDF），透過 API 回傳檔案
- 匯出功能在「處理完成當下」與「歷史紀錄清單中的保留項目」皆可使用

### FR-11：管理者成本/用量儀表板（新增）

- 僅**管理者角色**可存取（白名單 email 驗證）
- 顯示內容：各 LLM 引擎（GitHub Models／OpenAI／Groq／Gemini）使用次數、token 用量、估算成本；依日期/使用者彙總
- 資料來源：每次呼叫 LLM 摘要時記錄一筆用量明細

### 明確排除（不在本版範圍）

- ❌ Zoom/Teams 錄影直接整合
- ❌ 批次上傳多份錄音（維持一次一個檔案）

---

## 四、非功能需求（NFR）

### NFR-05：雲端部署架構（新增，取代本機部署方式）

系統改為 **AWS Serverless 架構**，考量因素：小團隊用量小、免維運、成本盡量落在免費額度內。

| 元件 | 選型 | 原因 |
|------|------|------|
| 運算 | AWS Lambda（既有 FastAPI 透過 Mangum adapter 包裝） | 免維運、按執行付費，程式碼可最大程度沿用 MVP |
| API | API Gateway（HTTP API） | 比 REST API 便宜，功能已足夠 |
| 資料庫 | **DynamoDB**（on-demand 計費） | 原生支援 TTL（對應 14 天到期），免維運，Lambda 生態原生整合 |
| 登入 | Amazon Cognito User Pool + Google 聯合登入 | 免費額度覆蓋小團隊用量，可直接掛 API Gateway Authorizer |
| 音檔儲存 | S3（Presigned URL 直傳）＋ Lifecycle Rule 自動過期 | 避開 API Gateway/Lambda payload 大小限制（2 小時錄音遠超過 10MB），且天然符合「處理完即刪」 |
| 轉錄進度通知 | AssemblyAI **Webhook** 回呼（取代原本輪詢） | Lambda 執行時間有上限且按時間計費，長輪詢不划算 |
| 前端 | S3 + CloudFront 靜態網站 | 成本低，沿用現有單頁 HTML/JS |
| Word 匯出 | `python-docx` | 純 Python、無原生依賴，Lambda 相容 |
| PDF 匯出 | `reportlab` | 純 Python、無原生依賴（避開 weasyprint 需要 GTK3/Pango 的問題） |
| 到期清理 | DynamoDB TTL 屬性（原生功能） | 免額外排程與維運成本 |

> ⚠️ 曾評估「維持 SQLite，檔案存 S3」方案：因 S3 無檔案鎖機制，併發寫入會導致資料遺失/損毀風險，故不採用；「SQLite + EFS」雖可行但需要 Lambda 掛載 VPC，複雜度與成本皆高於 DynamoDB，故最終選擇 DynamoDB。

### NFR-06：隱私保護（延續 MVP，補充雲端情境）

- 音檔僅在處理期間存在於 S3，處理完成後主動刪除（並設定 S3 Lifecycle 作為保險）
- 會議紀錄文字保留需使用者主動選擇，且有明確 14 天上限
- 沿用 MVP 既有的 AssemblyAI transcript 刪除機制（TASK-006）

### NFR-07：成本考量（新增）

- 目標：小團隊（<20 人）月用量下，Lambda／DynamoDB／Cognito／API Gateway／S3 均落在各自免費額度或近乎免費
- 主要變動成本仍是 AssemblyAI（依錄音時數）與 LLM API（依用量，已支援低成本引擎如 Groq/Gemini/GitHub Models）

### 其餘 NFR（NFR-01～NFR-04）延續 MVP 定義，不變。

---

## 五、系統流程（更新版）

```
使用者登入（Google OAuth via Cognito）
      ↓
瀏覽器直接上傳錄音檔至 S3（Presigned URL）
      ↓
[Lambda] 觸發轉錄，呼叫 AssemblyAI（非同步）
      ↓
[AssemblyAI] 處理完成 → 呼叫 Webhook 回調 Lambda
      ↓
[Lambda] 更新 DynamoDB 狀態，刪除 S3 音檔
      ↓
[Lambda] 呼叫 LLM（GitHub Models / OpenAI / Groq / Gemini，依設定）生成會議紀錄
      ↓
[Lambda] 記錄本次 LLM 用量明細（供管理者儀表板使用）
      ↓
[前端] 顯示會議紀錄，使用者選擇「保留」或「刪除」
      ↓
若保留 → 寫入 DynamoDB（含 14 天 TTL）→ 進入歷史紀錄清單
      ↓
使用者可匯出 Markdown / 純文字（前端產生）/ Word / PDF（後端產生）
      ↓
14 天後 → DynamoDB TTL 自動刪除該筆紀錄（或使用者提前手動刪除）
```

---

## 六、資料模型雛形（DynamoDB）

> DynamoDB 為 NoSQL，設計以「存取模式」反推 schema，非傳統關聯式正規化。

### Meetings（會議紀錄）
- PK: `user_id`　SK: `meeting_id`
- 屬性：`title`, `created_at`, `transcript_text`, `minutes_json`, `expires_at`（TTL 屬性，僅「保留」項目設定）

### Users（使用者/角色）
- PK: `email`
- 屬性：`role`（`user` / `admin`，依白名單判定）, `first_login_at`

### LLMUsage（成本/用量追蹤）
- PK: `date`　SK: `usage_id`
- 屬性：`engine`, `model`, `input_tokens`, `output_tokens`, `estimated_cost`, `user_id`, `meeting_id`

---

## 七、MVP 範圍界定（v2）

### ✅ v2 包含

| 功能 | 說明 |
|------|------|
| FR-01~07 | 延續 MVP 上傳/轉錄/發言人識別/摘要/編輯/引擎設定 |
| FR-08 | Google OAuth 登入（全站強制），角色判定（白名單 email） |
| FR-09 | 歷史紀錄（保留/刪除選擇、14 天 TTL、手動提前刪除、僅自己可見） |
| FR-10 | 多格式匯出：txt（前端）／docx／pdf（後端） |
| FR-11 | 管理者成本/用量儀表板 |
| NFR-05 | AWS Serverless 架構（Lambda/API Gateway/DynamoDB/S3/Cognito） |

### ❌ v2 不包含（後續版本可再評估）

| 功能 | 說明 |
|------|------|
| Zoom/Teams 整合 | 雲端錄影直接匯入 |
| 批次上傳 | 一次仍只能處理一個檔案 |
| 多租戶/組織架構 | 目前僅單一團隊，無跨團隊隔離需求 |

---

## 八、開放問題

| 問題 | 說明 | 狀態 |
|------|------|------|
| 白名單 email 管理方式 | 存於設定檔／環境變數，或另建 DynamoDB 表由管理者自行維護 | 待 SA 設計階段決定，建議先用環境變數（簡單），未來可遷移至 DynamoDB 表 |
| 匯出時機 | 處理完成當下即可匯出任何格式（不論是否選擇保留），或僅保留後才能匯出 | 假設：**處理完成當下即可匯出**，「保留」只影響是否進歷史紀錄，需與使用者確認 |
| AssemblyAI Webhook 安全性 | 需驗證 Webhook 來源（簽章驗證），避免偽造回呼 | 待 SA 設計階段補充 API 安全機制 |
| Lambda 冷啟動延遲 | 音檔上傳/轉錄非同步不受影響，但一般 API 請求（如查詢歷史紀錄）需評估冷啟動對使用者體感的影響 | 待效能測試後決定是否需要 Provisioned Concurrency |

---

## 九、訪談記錄摘要

| 問題 | 決策 |
|------|------|
| 歷史紀錄保存規則 | 使用者自選保留/刪除；僅保留者進歷史清單；最長 14 天 |
| 音檔留存 | 一律處理完即刪，UI 需明確提示 |
| 到期後行為 | 14 天自動刪除；清單中可隨時手動提前刪除 |
| 匯出格式 | Markdown（既有）+ 純文字 + Word + PDF |
| 匯出產生位置 | 純文字前端產生；Word/PDF 後端產生（python-docx + reportlab） |
| Zoom/Teams 整合 | 不做 |
| 登入機制 | 全站強制登入，Google 第三方驗證 |
| 角色判定 | 白名單 email 認定管理者 |
| 資料隔離 | 使用者僅能看自己的歷史紀錄 |
| 批次上傳 | 不做，維持一次一個檔案 |
| 成本儀表板 | 僅管理者可見 |
| 部署平台 | AWS Lambda，小團隊、低成本導向 |
| 資料庫選型 | DynamoDB（否決 SQLite on S3 / SQLite on EFS，因併發風險與複雜度考量） |
