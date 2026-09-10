# AIMOM-v2 產品需求文件

AIMOM-v2 導入 sdlc-agent-framework 後的產品需求紀錄。每個 Story 通過 G1（需求定稿）後，其使用者故事與驗收條件會逐條記錄於此，作為活的需求文件。

---

## SDLCAIP2-2：健康檢查端點 v2

### 使用者故事

As a sdlc-agent-framework 的維運/驗證角色（本工單為 Phase C 冒煙測試專用，非真實終端使用者需求）, I want 在 AIMOM-v2 這個既有專案疊加框架的目錄結構下，新增一個極簡單、低風險、公開（不需認證）的健康檢查端點 `/api/health-check-v2`, so that 可以驗證 sdlc-agent-framework 能否正確走完 Backlog → Refining → G1 → Designing → G1b → Ready → In Progress → Testing → In Review → G2 → Done 全流程，並遵守既有程式碼慣例（router 檔案分割、`Depends(get_current_user)` 認證排除規則、`conftest.py` 的 auth/DynamoDB mock 慣例），驗證通過後才排真正的功能開發 Story。

### 驗收條件（Gherkin）

```gherkin
Feature: 健康檢查端點 v2

  Scenario: 未認證使用者呼叫健康檢查端點
    Given 使用者未帶任何認證 token
    When 使用者發送 GET 請求到 /api/health-check-v2
    Then 回應狀態碼應為 200
    And 回應 JSON 應包含 "status": "ok"
    And 回應 JSON 應包含非空的 "version" 欄位

  Scenario: 端點不需要 Cognito 認證
    Given /api/health-check-v2 路由定義
    When 檢視其路由設定
    Then 該路由不應依賴 Depends(get_current_user)
```

---

## SDLCAIP2-4：建立 Node.js + Playwright e2e 測試骨架（本機後端 + moto mock）

### 使用者故事

As a AIMOM-v2 開發團隊, I want 建立最小可行的 Node.js 工具鏈與 Playwright e2e 測試骨架，並提供一個可對「本機啟動後端 + moto mock DynamoDB」執行的示範 smoke 測試, so that 之後任何 Story 在測試階段宣告「需要 e2e」時，有可執行、非 skip 的測試骨架可以直接擴充撰寫案例，滿足 G2 gate 的 `e2e_declared_and_honored` 條件。

### 驗收條件（Gherkin）

```gherkin
Feature: Node.js + Playwright e2e 測試骨架

  Scenario: 安裝與設定存在
    Given repo 根目錄尚無 Node.js 工具鏈
    When 開發者執行 npm install（於 package.json 所在目錄）
    Then package.json 的 devDependencies 含 @playwright/test，且 npx playwright test --list 可成功列出至少 1 個測試，不需額外手動設定即可執行

  Scenario: smoke e2e 測試對本機後端執行並通過
    Given 本機以既有 conftest.py 的模式（moto mock_aws 模擬 DynamoDB、dependency override 跳過真實 Cognito 登入）啟動的 FastAPI 後端、以及可存取的 src/frontend/ 靜態頁面
    When 執行 npx playwright test tests/e2e/smoke.spec.ts（或等效指令）
    Then 該測試實際執行（非 skip）且通過，驗證前端首頁可載入，並可對後端既有端點（例如 /api/health）取得成功回應

  Scenario: 不影響既有 Python 後端工具鏈
    Given 既有 pytest src/tests 與 ruff check . 指令
    When 新增的 package.json / playwright.config.ts / node_modules 加入 repo
    Then pytest src/tests -q 與 ruff check . 的執行結果與行為不受影響（package.json 僅含 devDependencies，不修改 src/ 下任何檔案）
```

---

## SDLCAIP2-5：CI 整合：新增獨立的 e2e job 到 GitHub Actions

### 使用者故事

As a AIMOM-v2 開發團隊, I want 在 .github/workflows/ci.yml 新增一個獨立的 e2e job，自動執行 SDLCAIP2-4 建立的 Playwright 測試, so that 每次 PR 都能自動看到 e2e 測試結果，且此新 job 不阻擋既有 quality job（pytest/ruff）的合併判定。

### 驗收條件（Gherkin）

```gherkin
Feature: e2e CI 整合

  Scenario: e2e job 存在且於 CI 可觀察
    Given .github/workflows/ci.yml 目前只有既有 quality（pytest/ruff）job
    When 本 Story 的變更合併
    Then ci.yml 新增一個獨立命名的 e2e job，於 push/PR 時觸發，執行 SDLCAIP2-4 建立的 npx playwright test 指令，並在 GitHub Actions 頁面顯示獨立的檢查結果

  Scenario: e2e job 失敗不阻擋既有 quality job 的通過判定
    Given e2e job 與既有 quality job 為兩個獨立、不互相依賴的 job
    When e2e job 因故失敗、但 quality job（pytest/ruff）本身通過
    Then PR 的 quality 檢查仍顯示綠色，e2e job 未被設為 branch protection 的必要檢查（required status check），不會連帶阻擋 PR 合併

  Scenario: e2e job 於執行測試前先確保本機後端就緒
    Given e2e job 需要一個可供 Playwright 呼叫的後端（依 SDLCAIP2-4 決定的本機 + moto mock 模式）
    When e2e job 執行
    Then job 先啟動本機後端服務並確認其已就緒（例如輪詢 /api/health 直到回應成功或逾時），才開始執行 Playwright 測試，避免因後端未啟動導致的連線錯誤被誤判為測試失敗
```

---

## SDLCAIP2-7：UI 文案調整 — 上傳頁與處理中頁面精簡措辭

### 使用者故事

As a AIMOM 使用者, I want 在「上傳錄音檔」與「處理中」頁面看到更簡潔正確的文案（移除內部技術供應商/模型名稱、修正不準確用詞）, so that 使用體驗更清楚，不會被無關的技術細節分散注意力，且隱私說明用詞更準確（系統其實完全不儲存錄音檔，而非僅「不長期」儲存）。

### 驗收條件（Gherkin）

```gherkin
Feature: 上傳與處理中頁面文案精簡

  Scenario: 上傳頁提示文字更新
    Given 使用者開啟上傳錄音檔頁面
    When 頁面載入完成
    Then 拖放區塊文字應顯示「拖放錄音檔至此，或點擊選取」
    And 隱私說明文字應顯示「本系統不會儲存您的錄音檔，處理完成後可手動清除暫存資料。」

  Scenario: 處理中頁面訊息更新且不含供應商/模型名稱
    Given 使用者已送出錄音檔並進入處理中頁面
    When 轉錄階段進行中（包含 15% 與 20% 進度點）
    Then 進度訊息應顯示「準備轉錄...」或「等待轉錄完成...」且不包含「AssemblyAI」字樣
    And 語音轉文字階段說明應顯示「處理中（轉錄 + 發言人同步完成）」且不包含「AssemblyAI」字樣
    And AI 整理階段說明應顯示「摘要與整理」且不包含「GPT-4o」字樣
```

---

## SDLCAIP2-10：建立後端 CD 自動部署（Terraform apply 自動化）

### 使用者故事

As a AIMOM-v2 的開發團隊, I want PR 合併到 main 後，後端基礎設施（Lambda 與其依賴的 infra/ 資源）能自動以 terraform apply 完成部署, so that 不需要每次手動在本機/CloudShell 執行 terraform apply，降低漏步驟或憑證/state 設定錯誤的風險。

### 驗收條件（Gherkin）

```gherkin
Feature: 後端 CD 自動部署

  Scenario: PR 合併後自動觸發非互動式 terraform apply
    Given PR 已合併到 main
    When GitHub Actions workflow 觸發
    Then 自動執行非互動式 terraform apply，重建 infra/backend.hcl（從既有 S3 state bucket/key/region），執行 terraform init + apply，更新 Lambda source_code_hash 以符合最新 src/ 版本

  Scenario: 敏感變數經由 GitHub Secrets 個別注入
    Given infra/variables.tf 定義 10 個 sensitive=true 的變數：google_client_id, google_client_secret, admin_emails, github_token, openai_api_key, groq_api_key, gemini_api_key, bedrock_proxy_base_url, bedrock_proxy_api_key, assemblyai_api_key
    When GitHub Actions workflow 執行 terraform apply
    Then 每個敏感變數經由 GitHub Secrets 個別注入為 TF_VAR_<name> 環境變數，不得在 workflow yaml 中硬寫值

  Scenario: 部署失敗於 GitHub Actions 清晰可見
    Given GitHub Actions workflow 執行 terraform apply
    When 部署因故失敗
    Then 失敗清晰顯示於 GitHub Actions 檢查結果，包含完整錯誤日誌
```

---

## SDLCAIP2-11：建立前端 CD 自動部署（S3 sync + CloudFront invalidation）

### 使用者故事

As a AIMOM-v2 的開發團隊, I want PR 合併到 main 後，前端靜態內容能自動同步到 S3 並觸發 CloudFront invalidation, so that 不需要每次手動執行 aws s3 sync / aws cloudfront create-invalidation，縮短小改動從合併到上線的時間。

### 驗收條件（Gherkin）

```gherkin
Feature: 前端 CD 自動部署

  Scenario: infra/outputs.tf 新增 cloudfront_distribution_id 輸出
    Given infra/outputs.tf 目前的定義
    When 本 Story 的變更合併
    Then infra/outputs.tf 新增 cloudfront_distribution_id 輸出

  Scenario: 後端 job 成功後自動同步前端並觸發 CloudFront 失效
    Given SDLCAIP2-10 的後端 job 已成功執行
    When 後端 job 完成
    Then 前端 job 自動執行，同步 src/frontend/ 到 S3 bucket（搭配 cache-control: no-cache, must-revalidate），並觸發 CloudFront invalidation（--paths "/*"）

  Scenario: 前端 job 依賴後端 job 成功
    Given GitHub Actions workflow 定義了後端 job 與前端 job
    When workflow 執行
    Then 前端 job 的依賴順序明確設定為須等待後端 job 成功才執行，被 SDLCAIP2-10 阻擋

  Scenario: 部署失敗於 GitHub Actions 清晰可見
    Given GitHub Actions workflow 執行前端 job
    When 部署因故失敗
    Then 失敗清晰顯示於 GitHub Actions 檢查結果，包含完整錯誤日誌
```

---

## SDLCAIP2-15：前端會議模板選擇 UI 與匯出格式調整

### 使用者故事

As a 團隊成員, I want 在會議紀錄結果畫面選擇/切換會議模板、並在匯出的 Word/PDF 中看到對應模板的區塊排版, so that 我不需要額外手動排版就能拿到符合會議性質的紀錄文件。

### 驗收條件（Gherkin）

```gherkin
Scenario: 結果畫面提供模板下拉選單
  Given 會議紀錄已產生（沿用現行自動觸發、預設 general 模板的行為，不變更）
  When 使用者進入結果畫面
  Then 畫面顯示模板下拉選單（前端內建固定清單，對應後端 5 種模板代碼），目前套用的模板為預設選中值

Scenario: 匯出文件依 sections 陣列通用渲染
  Given 會議紀錄已用某個模板產生（sections 陣列格式）
  When 使用者匯出 Word 或 PDF
  Then 匯出文件新增「討論重點」區塊，依 sections 陣列逐一渲染標題與內容，不因模板不同而需要額外程式邏輯

Scenario: 使用者於結果畫面重新選擇模板並重新產生
  Given 會議紀錄已產生，使用者在結果畫面
  When 使用者從下拉選單選擇不同模板並點擊「重新產生」
  Then 系統重新呼叫 /api/summarize（帶入新 template 參數）並覆蓋原本的 sections
  And 產生一筆新的 LLM usage 紀錄（沿用現有 usage.py 機制，行為不變）
  And 前端 m.topics 讀取全面改為 m.sections（renderMinutes / exportMarkdown / exportPlainText 共 3 處）
```

### 範圍外

* 使用者自訂模板 UI（暫不開放）
* 舊會議紀錄的模板回溯套用——僅影響新產生的會議紀錄
* 新增後端「列出可用模板」API——前端以靜態內建清單對應後端固定 5 種模板代碼
* 變更首次自動觸發 /api/summarize 的既有時機/流程（維持轉錄完成即自動以 general 產生）

---

## SDLCAIP2-16：會議紀錄彈性區塊 schema 重構 + 內建會議模板（後端）

### 使用者故事

As a 團隊成員, I want 上傳會議錄音時可以選擇符合這場會議性質的模板（如專案進度會議、客戶會議、腦力激盪、Retro）, so that AI 產出的會議紀錄結構貼近實際需要記錄的重點，而不是每種會議都套同一種「摘要/決定/待辦」格式。

### 驗收條件（Gherkin）

```gherkin
Scenario: 選擇內建模板後，AI 產出對應結構的區塊
  Given 逐字稿已產生完成
  When 使用者呼叫 /summarize 並指定 template="retro"
  Then 回傳的 minutes 含 sections 陣列，每個 section 有 title 與 content
  And section 標題符合 Retro 模板定義（例如「Keep」「Problem」「Try」）

---

Scenario: 不指定模板時維持向下相容
  Given 逐字稿已產生完成
  When 使用者呼叫 /summarize 且未帶 template 參數
  Then 系統套用預設模板「一般會議」
  And 回傳結構與現行行為相容（meeting_info、action_items 欄位不變）

---

Scenario: 指定不存在的模板代碼
  When 使用者呼叫 /summarize 並指定 template="not_exist"
  Then 回傳 400 錯誤，訊息列出可用的模板代碼清單
```

內建模板清單（G1 核准時未提出異動，採用暫定清單）：一般會議、專案進度會議、客戶業務會議、腦力激盪、Retro

---

## SDLCAIP2-18：逐字稿分頁講者命名 UI（前端）

### 使用者故事

As a 團隊成員, I want 在會議紀錄結果畫面的逐字稿分頁中為偵測到的講者輸入姓名並送出儲存, so that 我不需要理解 API 就能完成命名，且命名結果會保留在逐字稿與匯出檔案中。

### 驗收條件（Gherkin）

```gherkin
Scenario: 逐字稿分頁列出偵測到的講者標籤與命名輸入框
  Given 轉錄與摘要完成，偵測到 2 位講者
  When 使用者切換到逐字稿分頁
  Then 畫面顯示 2 個講者標籤，各自搭配一個姓名輸入框（自由輸入文字，非下拉選單）

Scenario: 送出命名後呼叫後端 API 並更新逐字稿顯示
  Given 使用者在講者姓名輸入框輸入姓名
  When 使用者點擊「送出」按鈕
  Then 前端呼叫 POST /api/speaker-names（一次送出所有已填寫的姓名對應）
  And 逐字稿顯示區的講者標籤即時替換為 API 回傳的新姓名
  And 匯出的 Markdown/純文字/Word/PDF 內容使用新姓名

Scenario: 不命名任何講者仍可正常使用會議紀錄
  Given 使用者未輸入任何講者姓名、也未點擊「送出」
  When 使用者切換分頁或匯出檔案
  Then 講者標籤維持原始 AI 標籤（SPEAKER_A 等），不受影響

Scenario: 後端回傳未知標籤時前端不報錯
  Given 使用者送出的姓名對應中包含 job 內不存在的講者標籤
  When 呼叫 POST /api/speaker-names 成功回傳 200
  Then 前端依回傳的 segments/speakers 正常更新顯示，不顯示錯誤訊息

Scenario: 畫面明確告知命名的影響範圍（依 SDLCAIP2-27 Q4 追加要求）
  Given 使用者進入逐字稿分頁的講者命名區塊
  Then 畫面需有明確提示文字，說明講者命名只會更新逐字稿分頁與匯出檔案，不會更新「會議紀錄」分頁的參與者/待辦事項負責人，避免使用者誤以為全部同步更新
```

### 範圍外

* 批次匯入/管理團隊成員姓名清單（下拉選單式選人）
* 命名後重新呼叫 /api/summarize 以更新「會議紀錄」分頁的參與者/待辦事項欄位（留待未來 Story；本 Story 僅更新逐字稿分頁與匯出檔案）
* 新增獨立的「審核」畫面/流程步驟；沿用現有 view-result 逐字稿分頁
* 跨會議聲紋辨識、已保留歷史會議改名（同 SDLCAIP2-20 範圍外）

---

## SDLCAIP2-19：已保留會議紀錄編輯 API（後端）

### 使用者故事

As a 團隊成員, I want 編輯已保留會議紀錄的內容（摘要、待辦事項、決議等，儲存在 minutes 內的欄位）, so that 我能修正 AI 誤判或補充遺漏的重點，不需要重新錄音。

### 驗收條件（Gherkin）

```gherkin
Scenario: 編輯已保留的會議紀錄
  Given 使用者已保留一筆會議紀錄
  When 使用者呼叫 PATCH /meetings/{meeting_id}，body 為完整的 minutes 物件（與 GET /meetings/{meeting_id} 回傳的 minutes 同形狀）
  Then 儲存成功，整份 minutes 內容被覆蓋為 body 內容，回傳更新後的完整會議紀錄

Scenario: 編輯不存在或非本人擁有的會議紀錄
  Given meeting_id 不存在，或屬於另一位使用者（依 DynamoDB user_id+meeting_id 複合鍵，查不到即視為不存在，不額外揭露「存在但非本人」）
  When 使用者呼叫 PATCH /meetings/{meeting_id}
  Then 回傳 404 錯誤（與既有 GET/DELETE /meetings/{meeting_id} 一致，不使用 403）
```

**注：** 原第 3 個 Scenario「編輯後重新匯出反映最新內容」已拆分至獨立 Story SDLCAIP2-29（已保留會議紀錄匯出 API），因現行系統完全沒有依 meeting_id 匯出的端點，屬於獨立於編輯語意的既有缺口。

### 範圍外

* 逐字稿原始文字編輯（僅編輯 AI 產出的會議紀錄結構，不含原始逐字稿內容修改）
* 編輯歷史/版本紀錄與 undo 功能（僅保留最新版本）
* 會議紀錄標題（title）編輯（PATCH 僅覆蓋 minutes 內容，不含 title 欄位）
* 部分欄位局部更新（partial patch）語意：本次 PATCH 一律為整份 minutes 覆蓋，不支援只送部分欄位

---

## SDLCAIP2-20：轉錄後講者姓名對應 API（後端）

### 使用者故事

As a 團隊成員, I want 在確認保留會議紀錄前，把偵測到的講者標籤對應成實際姓名（含非團隊成員的外部與會者，自由輸入文字非下拉選單）, so that 存檔後的逐字稿與會議紀錄顯示真實姓名。

### 驗收條件（Gherkin）

```gherkin
Scenario: 提交講者姓名對應後，job 的 segments 更新為指定姓名
  Given 轉錄已完成，job 內有多個講者標籤（如 SPEAKER_A, SPEAKER_B）
  When 使用者呼叫新的講者姓名對應 API，提交 {"SPEAKER_A": "王小明"}
  Then job 的 segments 中原本標記 SPEAKER_A 的項目，speaker 欄位改為「王小明」

---

Scenario: 未命名的講者維持原始標籤
  Given job 內有 SPEAKER_A 與 SPEAKER_B 兩位講者
  When 使用者只提交 {"SPEAKER_A": "王小明"} 的對應
  Then SPEAKER_B 的 segments 維持原本標籤不變

---

Scenario: 重新呼叫 /summarize 後反映新姓名
  Given 已完成講者姓名對應
  When 使用者呼叫 /summarize
  Then 回傳的 meeting_info.participants 與 action_items.owner 使用對應後的姓名（若逐字稿中有明確提及）

---

Scenario: job 尚未完成轉錄時呼叫此 API
  Given job 尚未完成 /transcribe
  When 使用者呼叫講者姓名對應 API
  Then 回傳 400 錯誤，訊息說明需先完成轉錄

---

Scenario: 提交的講者標籤與 job 內實際標籤不符
  Given job 內只有 SPEAKER_A 與 SPEAKER_B 兩位講者
  When 使用者提交 {"SPEAKER_C": "陌生人"} 的對應（job 內不存在 SPEAKER_C）
  Then API 忽略該筆不存在的標籤，不報錯，其餘存在的對應正常套用
```

### 範圍外

* 跨會議聲紋辨識、記憶講者身份（涉及生物特徵隱私法規，另案評估）
* 已保留（keep）之歷史會議的講者改名——由「會議紀錄手動編輯」相關 Story 涵蓋
* 講話片段重新歸屬（segment 級別的「這句其實是別人講的」修正）

---

## SDLCAIP2-21：補上 bedrock-proxy 定價並修正查無定價時靜默顯示 0 的問題

### 使用者故事

As a 管理者, I want 管理者儀表板的 LLM 成本彙總能正確反映正式環境實際使用的 bedrock-proxy 引擎成本、且在定價缺漏時明確標示而非靜默顯示 0, so that 我看到的成本數字是可信的，不會誤判實際花費。

### 驗收條件（Gherkin）

```gherkin
Scenario: 新增 bedrock-proxy 定價後成本可正確估算
  Given PRICING_PER_MILLION_TOKENS 已補上 ("bedrock-proxy", "mistral.mistral-large-3-675b-instruct") 對應 (0.50, 1.50) （美元/百萬 tokens，換算自 $0.0005/1K input、$0.0015/1K output）
  When 使用 bedrock-proxy 引擎呼叫 /summarize 並產生一筆用量紀錄
  Then estimated_cost 為依實際 input_tokens/output_tokens 換算後的正確金額，不再是 0

---

Scenario: 查無定價的 engine/model 明確標記，不再靜默顯示 0
  Given 某筆用量紀錄的 (engine, model) 組合不在定價表中
  When record_llm_usage 寫入該筆紀錄
  Then 該筆紀錄新增欄位 pricing_unavailable=true，estimated_cost 維持 None（不落地為數字 0）

---

Scenario: 管理者儀表板顯示定價缺漏筆數
  Given DynamoDB 中同時存在有定價與查無定價的用量紀錄
  When 管理者呼叫 /admin/usage
  Then 回傳結果除了 total_estimated_cost 外，額外包含 pricing_unavailable_count（查無定價的筆數）與其涉及的 (engine, model) 清單
  And total_estimated_cost 的計算明確排除 pricing_unavailable 的紀錄

---

Scenario: 既有沒有 pricing_unavailable 欄位的舊資料維持相容
  Given DynamoDB 中已有舊資料且沒有 pricing_unavailable 欄位
  When summarize_usage() 讀取舊資料
  Then 視為 pricing_unavailable=false（沿用原本 estimated_cost 數字）處理，不拋錯
```

---

## SDLCAIP2-22：AssemblyAI 轉錄成本估算

### 使用者故事

As a 管理者, I want 管理者儀表板也能看到 AssemblyAI 轉錄成本（不只是 LLM 摘要成本）, so that 我看到的「總成本」是完整的，涵蓋轉錄與摘要兩個階段。

### 驗收條件（Gherkin）

```gherkin
Scenario: 轉錄完成後記錄一筆轉錄成本
  Given 音檔上傳時已知 duration_sec
  When 轉錄流程完成（segments 組裝完成）
  Then 系統依 (duration_sec / 3600) * 費率（含 diarization add-on 費率，若該次有開啟）估算成本
  And 寫入一筆用量紀錄，service 標記為 "transcription"，與現有 LLM 用量紀錄可區分

---

Scenario: 診斷模型/add-on 組合尚未支援定價
  Given ASSEMBLYAI_MODEL 或 add-on 設定不在目前定價對照表中
  When 轉錄完成要記錄成本
  Then 該筆紀錄標記 pricing_unavailable=true（比照 SDLCAIP2-21 的作法），estimated_cost 不落地為 0

---

Scenario: 管理者儀表板同時顯示轉錄與摘要成本
  Given 資料庫中同時有 transcription 與 summarization 兩種用量紀錄
  When 管理者呼叫 /admin/usage
  Then 回傳結果分別列出 transcription 與 summarization 的小計成本，以及兩者合計的總成本

---

Scenario: duration_sec 缺失時不強行估算
  Given 某筆轉錄紀錄找不到 duration_sec（例如舊資料或例外流程）
  When 嘗試記錄轉錄成本
  Then 不寫入該筆成本紀錄，並標記 pricing_unavailable=true，不做無依據的猜測
```

---

## SDLCAIP2-23：登入白名單控管（ALLOWED_EMAILS）

### 使用者故事

As a 系統管理者, I want 只有白名單內的 email 能登入使用系統, so that 任何擁有 Google 帳號的人都不能未經授權存取系統、消耗 AssemblyAI/LLM 額度。

### 驗收條件（Gherkin）

```gherkin
Scenario: email 在白名單內，正常登入
  Given ALLOWED_EMAILS 設定為 "a@example.com,b@example.com"
  When 使用者以 a@example.com 完成 Google 登入並呼叫需驗證的 API
  Then 請求正常處理，回傳 200

---

Scenario: email 不在白名單內，拒絕存取
  Given ALLOWED_EMAILS 設定為 "a@example.com"
  When 使用者以 c@example.com（合法 token，但不在白名單）呼叫需驗證的 API
  Then 回傳 403，訊息說明此帳號未被授權使用本系統

---

Scenario: ALLOWED_EMAILS 留空時維持向下相容
  Given ALLOWED_EMAILS 未設定或為空字串
  When 任何合法 token 的使用者呼叫需驗證的 API
  Then 不做白名單限制，行為與目前一致（允許所有合法登入的使用者）

---

Scenario: 管理者也必須同時在白名單內
  Given ADMIN_EMAILS 含 admin@example.com，但 ALLOWED_EMAILS 未包含 admin@example.com（且 ALLOWED_EMAILS 非空）
  When admin@example.com 嘗試登入
  Then 回傳 403（管理者身份不自動繞過白名單檢查）
```

---
