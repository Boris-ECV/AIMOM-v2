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

## SDLCAIP2-17：已保留會議紀錄詳情頁編輯 UI

### 使用者故事

As a 已登入的系統使用者, I want 在已保留會議紀錄的詳情頁切換到編輯模式並儲存修改, so that 我可以在事後修正會議紀錄內容而不需重新上傳錄音。

### 驗收條件（Gherkin，摘要）

- 詳情頁提供編輯模式切換
- 儲存成功後畫面顯示最新內容（呼叫 PATCH /api/meetings/{meeting_id}）
- 儲存失敗時保留使用者輸入
- 編輯時遇到 404 顯示錯誤

### 範圍外

* 編輯後立即重新匯出（依賴已完成的 SDLCAIP2-29，不阻塞本故事）
* 逐字稿內容的編輯
* 刪除會議紀錄
* 歷史列表與唯讀詳情頁本身的實作（見依賴）
* 多人同時編輯的衝突偵測

### 依賴

* SDLCAIP2-19（已完成，PATCH 端點）
* SDLCAIP2-32（本故事在其詳情頁基礎上加入編輯模式）

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

## SDLCAIP2-29：已保留會議紀錄匯出 API（依 meeting_id 匯出 docx/pdf）

### 使用者故事

As a 團隊成員, I want 依已保留會議紀錄的 meeting_id 匯出 docx/pdf, so that 我不需要透過原始 job_id（6 小時後即過期）就能取得已保留紀錄的正式文件。

### 情境緣由

本 Story 是從 SDLCAIP2-19（已保留會議紀錄編輯 API）的設計階段拆分出來的既有系統缺口，經 HUMAN-INPUT SDLCAIP2-25 確認獨立處理（Option 2）。現況：`src/export.py` 的 `/export/{job_id}` 只讀取 `jobstore`（以 `job_id` 為鍵、6 小時 TTL 的暫存 job 狀態）；「保留」流程操作的是完全獨立的 Meetings 表（`user_id`＋`meeting_id` 為鍵、14 天 TTL），`keep_meeting()` 保留時會產生全新的 `meeting_id`，與原始 `job_id` 無任何欄位保留對應關係。即使不編輯，單純保留後想匯出已保留的紀錄，現有系統也做不到——這個缺口獨立於「編輯」語意，從保留功能上線起就存在。

### 驗收條件（Gherkin）

```gherkin
Scenario: 依 meeting_id 匯出已保留會議紀錄
  Given 使用者已保留一筆會議紀錄（擁有 meeting_id）
  When 使用者呼叫新的匯出端點（例如 GET /export/meetings/{meeting_id}?format=docx）
  Then 回傳依該筆 Meetings 表資料產生的 docx/pdf 檔案；文件標題使用該筆紀錄的 title，
       檔案名稱使用 {meeting_id}.docx/pdf（沿用既有 job_id 檔名慣例，避免 title 含特殊字元造成 Content-Disposition 問題）

Scenario: 匯出不存在或非本人擁有的會議紀錄
  Given meeting_id 不存在，或屬於另一位使用者
  When 使用者呼叫匯出端點
  Then 回傳 404（與既有 GET/DELETE/PATCH /meetings/{meeting_id} 一致，不使用 403）

Scenario: 編輯後重新匯出反映最新內容（銜接 SDLCAIP2-19 AC3）
  Given 使用者已透過 PATCH /meetings/{meeting_id}（SDLCAIP2-19）編輯過會議紀錄
  When 使用者呼叫依 meeting_id 的匯出端點
  Then 匯出檔案內容為編輯後的最新版本
```

### 範圍外

* 依 job_id 匯出（`/export/{job_id}`）既有行為不變，本 Story 只新增依 meeting_id 的匯出路徑，不修改/移除既有端點
* 匯出格式以外的功能（如批次匯出、匯出排程）

---

## SDLCAIP2-31：[SECURITY] 講者重新命名輸入框渲染未轉義使用者輸入，DOM-based XSS 風險

### 使用者故事

As a user of the transcript editing page, I want the speaker-rename input rows to safely render any speaker label or previously-entered name — including ones containing special HTML/attribute characters — so that a malicious or unusual speaker label/name cannot break out of the HTML attribute context and execute arbitrary script in my browser.

### 驗收條件（Gherkin）

```gherkin
Scenario: Normal speaker label and name render unchanged
  Given speaker label is "SPEAKER_A" and name is "Alice"
  When rendering speaker-rename input row
  Then speaker label displays as "SPEAKER_A" and name input value is "Alice", both unmodified

---

Scenario: Speaker label containing HTML/attribute special characters is neutralized
  Given speaker label contains special characters like "<>\"&" or similar HTML/attribute delimiters
  When rendering speaker-rename input row in HTML attribute context
  Then characters are escaped/neutralized to prevent attribute-boundary breakout and script execution

---

Scenario: Previously-entered speaker name containing special characters is neutralized
  Given previously-entered speaker name contains special characters like "<script>" or "test&oops" or 'break"out'
  When rendering name input value and speaker labels in transcript body
  Then characters are escaped to render as literal text, not markup or attribute delimiters

---

Scenario: Existing correctly-escaped renderings elsewhere are unaffected
  Given transcript body rendering is already correctly escaped
  When this fix is applied to speaker-rename input rows
  Then no regression in other parts of the application — transcript body and other existing escaped content remain unaffected
```

### 範圍外

* Changes to `esc()` escaping behavior beyond adding double-quote escaping needed to close this specific vector
* Backend speaker-label generation/validation changes
* Transcript body rendering changes (already correctly escaped)
* Broader refactor of `renderTranscript()` beyond the two injection points

### 依賴

無（found during SDLCAIP2-18 code review, independently schedulable）

---

## SDLCAIP2-32：已保留會議紀錄歷史列表與詳情唯讀瀏覽 UI

### 使用者故事

As a 已登入的系統使用者, I want 瀏覽自己保留過的會議紀錄列表並點入查看完整內容, so that 我可以在不重新上傳錄音的情況下回顧過去的會議紀錄。

### 驗收條件（Gherkin，摘要）

- 歷史列表顯示已保留的會議紀錄（呼叫 GET /api/meetings）
- 無任何已保留紀錄時顯示空狀態
- 點擊列表項目導向該筆紀錄的詳情頁（呼叫 GET /api/meetings/{meeting_id}）
- 詳情頁以唯讀方式顯示完整內容（標題、逐字稿、會議紀錄）
- 詳情頁遇到 404 時顯示錯誤並可返回列表

### 範圍外

* 編輯會議紀錄內容（見 SDLCAIP2-17）
* 刪除會議紀錄
* 從詳情頁重新匯出
* 歷史列表的分頁/排序/搜尋
* 新增「保留此次紀錄」的觸發 UI

### 依賴

無（後端 GET /api/meetings、GET /api/meetings/{meeting_id} 已完成，見 SDLCAIP2-19）

---

## SDLCAIP2-33：轉錄語言改用 AssemblyAI 自動偵測，取代寫死的中文

### 使用者故事

As a 使用者, I want 系統自動偵測會議錄音的語言（不再寫死中文），並在偵測信心不足時看到明確提示, so that 我能處理非純中文（或中英夾雜）的會議錄音，同時知道何時該自行覆核逐字稿的準確度。

### SDK 確認證據

- `assemblyai==0.64.33`（已安裝版本）的 `TranscriptionConfig.language_detection: Optional[bool]` — 設為 True 啟用自動語言偵測，取代現行 `language_code="zh"`。
- `TranscriptionConfig.language_confidence_threshold` — 若設定此值，AssemblyAI 會在低於門檻時讓整個轉錄失敗，因此本票不使用此參數。
- `BaseTranscript.language_confidence: Optional[float]`（0.0～1.0）— 轉錄完成後回傳的信心分數，透過 `transcript.json_response.get("language_confidence")` 取得。

### 驗收條件（Gherkin，摘要）

- 啟用語言自動偵測（language_detection=True，不設定 language_confidence_threshold）
- 既有 speech_models/speaker_labels 設定不受影響
- 語言偵測信心過低（<0.5）時，job 狀態標記低信心旗標，前端以既有 #modified-badge 樣式的持續性警示顯示提示，不觸發重試
- 信心正常時不顯示提示

### 範圍外

* 信心過低時的自動重試、換模型重試、或阻擋使用者繼續操作
* 設定 AssemblyAI 端的 language_confidence_threshold 讓其直接回傳錯誤
* 讓使用者手動指定轉錄語言
* 對信心分數做趨勢分析/記錄到 metrics 儀表板

### 依賴

無新增依賴，沿用既有 assemblyai SDK（已確認版本支援上述欄位）

---

## SDLCAIP2-35：匯出功能的四種格式應整合為單一選單

### 使用者故事

As a 使用本系統的使用者, I want 將匯出會議紀錄的四種格式（Markdown、純文字、Word、PDF）整合成單一選單, so that 匯出介面更簡潔，不需要一次看到四顆並排的匯出按鈕。

### 驗收條件（Gherkin）

```gherkin
Feature: 匯出功能整合為單一選單

  Scenario: 結果頁面的匯出控制項為單一下拉選單加確認按鈕
    Given 會議紀錄已產生
    When 使用者進入結果畫面
    Then 匯出控制項為單一下拉選單加確認按鈕，不再顯示四顆並排按鈕

  Scenario: 下拉選單選項與預設值
    Given 使用者在結果畫面
    When 查看匯出下拉選單
    Then 選單含有 Markdown、純文字、Word、PDF 四個選項
    And 預設選取為 Markdown

  Scenario: 點擊匯出按鈕呼叫對應的既有匯出函式
    Given 使用者選定某個匯出格式
    When 使用者點擊「匯出」按鈕
    Then 依選取的格式呼叫對應的既有匯出函式（exportMarkdown()/exportPlainText()/exportServerFile('docx')/exportServerFile('pdf')）
    And 匯出檔案正確產生

  Scenario: 既有四個匯出函式邏輯不變，僅改觸發方式
    Given 既有的四個匯出函式（exportMarkdown/exportPlainText/exportServerFile）
    When 本 Story 的變更合併
    Then 四個函式本身的邏輯與內容格式完全不變，僅改變觸發方式（從直接點擊四顆按鈕改為選單後點確認）
```

### 範圍外

* 不變更任何匯出檔案的產生邏輯或內容格式
* 不新增任何新的匯出格式
* 不處理歷史紀錄詳情頁（view-history-detail）的匯出功能——該頁面目前完全沒有匯出按鈕或邏輯，屬既有缺口
* 不變更後端 /api/export/{jobId} API 介面

### 依賴

無強制依賴；SDLCAIP2-15（已完成）的模板選擇下拉選單為 UI 慣例參考來源

---

## SDLCAIP2-34：從管理者儀表板返回上傳頁後，上傳按鈕錯誤顯示「上傳中」

### 使用者故事

As a AIMOM 使用者, I want 從管理者儀表板返回上傳頁面後看到正確的上傳按鈕狀態, so that 我不會被誤導認為上傳仍在進行中。

### 驗收條件（Gherkin）

```gherkin
Scenario: 返回上傳頁後按鈕狀態已重置
  Given 使用者成功完成一次上傳並進入管理者儀表板
  When 使用者點擊「返回上傳頁」返回到上傳頁面
  Then 上傳頁面的上傳按鈕應顯示「上傳」（未禁用），不再錯誤顯示「上傳中...」

Scenario: 正常上傳流程中按鈕狀態表現正確
  Given 使用者在上傳頁面
  When 使用者選擇檔案並點擊上傳按鈕開始上傳
  Then 上傳期間按鈕應正確顯示「上傳中...」並被禁用
  And 上傳成功或失敗時按鈕應自動重置為「上傳」並恢復可用

Scenario: 上傳失敗時按鈕狀態已正確重置
  Given 使用者嘗試上傳檔案但上傳因故失敗
  When 上傳錯誤被後端或網路層捕獲
  Then 按鈕應自動重置為「上傳」並恢復為可用狀態
```

### 範圍外

* 變更上傳流程的整體邏輯或步驟
* 重構上傳功能模組
* 新增其他頁面導航路徑的相應按鈕狀態管理
* 修改上傳按鈕的 UI 樣式或文案

---

## SDLCAIP2-36：會議模板選擇區塊的視覺風格與頁面不一致

### 使用者故事

As a AIMOM 使用者, I want 會議模板選擇下拉選單的視覺風格與結果頁面其他表單控制項保持一致, so that 整個頁面有統一的設計感，不會因為一個控制項突兀而影響使用體驗。

### 驗收條件（Gherkin）

```gherkin
Feature: 下拉選單視覺風格一致性

  Scenario: 下拉選單具有與輸入欄位一致的邊框與圓角
    Given #template-select 下拉選單已套用 CSS 樣式
    When 頁面在結果檢視中呈現
    Then #template-select 的 border、border-radius、color、font-family 應與 .meeting-info-grid input 的設定相同

  Scenario: 下拉選單在聚焦狀態表現一致
    Given 使用者點擊下拉選單獲得焦點
    When 下拉選單進入 :focus 狀態
    Then 視覺效果應與其他表單控制項的聚焦狀態一致（包括 outline、box-shadow 等）

  Scenario: 下拉選單選項值與功能不變
    Given 下拉選單的現有功能（模板選擇、重新產生會議紀錄）
    When 套用視覺風格調整後
    Then 模板選擇邏輯、可選值、重新產生機制完全不變
```

### 範圍外

* 變更下拉選單的模板選擇邏輯或功能
* 修改其他下拉選單或表單控制項
* 變更模板選項值或新增選項
* 變更「重新產生」按鈕的行為

---

## SDLCAIP2-39：會議紀錄結果頁操作按鈕排列在特定寬度下會換行，且部分按鈕圖示與文字混雜

### 使用者故事

As a 使用中的會議紀錄使用者, I want 結果頁上方的操作列（模板選單、重新產生、匯出格式、匯出、清除暫存、新錄音）在任何合理畫面寬度下都維持同一排、不換行，且「重新產生」「匯出」「清除暫存」三顆按鈕只顯示文字, so that 我能快速找到並點擊正確的操作按鈕，不被凌亂的換行版面或圖示/文字混雜干擾。

### 驗收條件（Gherkin）

```gherkin
Scenario: AC1 寬螢幕下操作列維持單排不換行
  Given 使用者已進入 view-result（會議紀錄結果頁）
  And 瀏覽器視窗寬度為 1280px（桌面常見寬度）
  When 觀察 #result-action-group-content 與 #result-action-group-reset 內所有元素
  Then 所有元素的 bounding box top 座標相同（同一排），沒有任何元素換到第二排

Scenario: AC2 窄螢幕下操作列仍維持單排（改為可橫向捲動，不換行）
  Given 使用者已進入 view-result（會議紀錄結果頁）
  And 瀏覽器視窗寬度縮小至 480px
  When 觀察外層容器（第 293 行 flex 容器）與其內所有按鈕/選單元素
  Then 所有元素的 top 座標仍相同（沒有任何元素換到第二排）
  And 外層容器可透過水平捲動（overflow-x）看到超出可視範圍的元素

Scenario: AC3 清除暫存／新錄音靠右對齊，其餘控制項靠左
  Given 使用者已進入 view-result 且視窗寬度足以容納整排不觸發橫向捲動（例如 1280px）
  When 比較 #result-action-group-reset（內含 #cleanup-btn、#new-recording-btn）與 #result-action-group-content 的水平位置
  Then #result-action-group-reset 位於容器最右側（與 SDLCAIP2-37 既有 margin-left:auto 行為一致）
  And #result-action-group-content 內的模板選單、#regenerate-btn、匯出格式選單、#export-confirm-btn 維持靠左、原有相對順序不變

Scenario: AC4 重新產生／匯出／清除暫存三顆按鈕只顯示文字，不顯示圖示
  Given 使用者已進入 view-result
  When 讀取 #regenerate-btn、#export-confirm-btn、#cleanup-btn 的按鈕文字內容
  Then #regenerate-btn 文字為「重新產生」（不含「🔄」）
  And #export-confirm-btn 文字為「匯出」（不含「⬇」）
  And #cleanup-btn 文字為「清除暫存」（不含「🗑」）

Scenario: AC5 既有匯出／重新產生／清除暫存行為不受影響（回歸測試）
  Given 使用者已進入 view-result 且已有轉錄結果
  When 使用者點擊 #regenerate-btn、選擇匯出格式後點擊 #export-confirm-btn、或點擊 #cleanup-btn
  Then 對應的既有 JS 行為（regenerateSummary()、exportSelectedFormat()、cleanupAndReset()）與呼叫參數維持不變，功能不因本次純視覺變更而改變
```

### 範圍外

* 新增 CSS class
* 新增媒體查詢（media query）斷點
* 變更 #new-recording-btn 的「+」字首
* 變更按鈕的 onclick 行為或後端呼叫
* 僅限於 #view-result 操作列，不涉及其他頁面元素
* 新增專為 <375px 行動裝置的版面配置

---

## SDLCAIP2-40：會議紀錄結果頁操作區塊應回復至 SDLCAIP2-39 合併前的呈現方式

### 使用者故事

As a 使用中「會議紀錄」結果頁的使用者, I want 操作區塊（模板／重新產生／匯出格式／匯出／清除暫存／新錄音）的排版與按鈕圖示回復到 SDLCAIP2-39 合併前（SDLCAIP2-37 完成後）的樣式, so that 畫面呈現符合先前已驗收、被 SDLCAIP2-39 意外改動的預期外觀。

### 驗收條件（Gherkin）

```gherkin
Scenario: AC1 外層操作列容器不再強制單行（移除 flex-wrap:nowrap）
  Given 會議紀錄已產生，使用者進入結果頁
  When 檢視結果頁上方的操作列容器（#result-action-group 及其直接子元素）
  Then 容器應無 flex-wrap:nowrap 內聯樣式，允許內容自然換行（恢復 SDLCAIP2-37 後的預設行為）

Scenario: AC2 操作列容器不再有強制橫向捲動（移除 overflow-x:auto）
  Given 會議紀錄已產生，使用者進入結果頁
  When 檢視結果頁操作列容器的樣式
  Then 容器應無 overflow-x:auto 內聯樣式（不再有水平捲軸）

Scenario: AC3 重新產生按鈕恢復顯示「🔄」emoji 前綴
  Given 使用者進入結果頁，操作列內含重新產生按鈕
  When 讀取該按鈕的渲染文字內容
  Then 按鈕文字應包含「🔄」字符，完整文字為「🔄 重新產生」

Scenario: AC4 匯出按鈕恢復顯示「⬇」emoji 前綴
  Given 使用者進入結果頁，操作列內含匯出按鈕
  When 讀取該按鈕的渲染文字內容
  Then 按鈕文字應包含「⬇」字符，完整文字為「⬇ 匯出」或等效表示

Scenario: AC5 清除暫存按鈕恢復顯示「🗑」emoji 前綴
  Given 使用者進入結果頁，操作列內含清除暫存按鈕
  When 讀取該按鈕的渲染文字內容
  Then 按鈕文字應包含「🗑」字符，完整文字為「🗑 清除暫存」

Scenario: AC6 測試檔案刪除與核心功能迴歸
  Given SDLCAIP2-39 建立的 tests/e2e/action-bar-nowrap.spec.ts 檔案
  When 本 Story 的變更合併且 CI 執行全套測試（pytest + playwright）
  Then 該檔案應已被 git revert 刪除；全套測試（pytest + playwright）應在 CI 通過
```

### 範圍外

* `src/export.py` 與字型檔案的任何修改（屬 SDLCAIP2-38 範圍）
* 手動重寫操作列佈局邏輯（必須使用 `git revert` 提交回復 SDLCAIP2-39 的 commit）
* 修改按鈕的 onclick、id、class 或 JS 事件處理（僅限視覺回復，功能不變）

---

## SDLCAIP2-41：頁首標題應移除麥克風圖示，並維持點擊可回到首頁

### 使用者故事

As a 系統使用者, I want 頁首標題不要顯示麥克風圖示、且點擊標題文字可以回到首頁, so that 頁首視覺更簡潔一致，且我能隨時透過點擊標題快速返回首頁操作畫面。

### 驗收條件（Gherkin）

```gherkin
Scenario: 頁首不再顯示麥克風圖示
  Given 使用者已登入並看到系統主畫面
  When 使用者觀察頁首左上角標題區域
  Then 標題「會議錄音轉紀錄系統」左側不應顯示麥克風圖示（不應存在該 svg 元素）

Scenario: 點擊頁首標題可回到首頁
  Given 使用者已登入並目前位於任一非首頁畫面（例如歷史紀錄畫面或處理結果畫面）
  When 使用者點擊頁首「會議錄音轉紀錄系統」標題文字
  Then 畫面應切換回首頁（上傳/首頁畫面，即 view-upload）
```

---

## SDLCAIP2-42：會議紀錄結果頁操作區塊排列應維持同排且靠右對齊，並移除三顆按鈕圖示

### 使用者故事

As a 使用完成逐字稿轉錄後查看「會議紀錄」結果頁的使用者, I want 結果頁上方操作列（模板／重新產生／匯出格式／匯出／清除暫存／新錄音）在任何視窗寬度下都維持同一排、不整排換行，且「清除暫存」「新錄音」靠右對齊、「重新產生」「匯出」「清除暫存」三顆按鈕只顯示文字, so that 我在不同螢幕寬度下都能穩定、一致地找到並操作這些功能按鈕，不因排版跳動或圖示佔位而分心。

### 驗收條件（Gherkin）

```gherkin
Feature: 會議紀錄結果頁操作列排版與按鈕文字

  Scenario: 寬螢幕下操作列同排不換行
    Given 使用者在寬螢幕（例如 1280px 寬）檢視「會議紀錄」結果頁（#view-result）
    When 觀察操作列（#result-action-group-content 與 #result-action-group-reset 所在的操作列容器）
    Then 模板選單、重新產生、匯出格式、匯出、清除暫存、新錄音六個元素皆顯示在同一列
    And 這六個元素的相對排列順序與現況（模板→重新產生→匯出格式→匯出→清除暫存→新錄音）一致

  Scenario: 窄螢幕下操作列仍維持同排不換行
    Given 使用者在窄螢幕（例如 480px 寬）檢視「會議紀錄」結果頁
    When 觀察操作列
    Then 模板到匯出（模板選單、重新產生、匯出格式、匯出）與清除暫存、新錄音仍維持同一列，不會整排換行成多列
    And 若內容寬度超過可視範圍，允許以水平捲動或其他不影響元素相對順序的方式呈現

  Scenario: 清除暫存與新錄音靠右對齊
    Given 使用者在任一視窗寬度下檢視結果頁操作列
    When 觀察「清除暫存」「新錄音」兩顆按鈕相對於「模板」到「匯出」區塊的位置
    Then 「清除暫存」「新錄音」兩顆按鈕應靠操作列右側對齊
    And 「模板」到「匯出」區塊維持靠左（或緊接標題區塊之後）的相對位置不變

  Scenario: 三顆按鈕僅顯示文字，不顯示圖示
    Given 使用者檢視結果頁操作列
    When 觀察「重新產生」（#regenerate-btn）、「匯出」（#export-confirm-btn）、「清除暫存」（#cleanup-btn）三顆按鈕
    Then 三顆按鈕的顯示文字分別為「重新產生」「匯出」「清除暫存」，不含任何圖示（emoji）前綴
    And 「新錄音」（#new-recording-btn）按鈕的「+ 新錄音」文字維持不變，不受本次變更影響

  Scenario: 既有按鈕行為與元素結構不受影響（回歸保護）
    Given 使用者在結果頁點擊「重新產生」「匯出」「清除暫存」「新錄音」任一按鈕
    When 按鈕被點擊
    Then 分別呼叫既有的 regenerateSummary()、exportSelectedFormat()、cleanupAndReset()、showView('view-upload') 函式，呼叫參數與現況相同
    And 操作列內所有元素的 id、class、onclick 綁定、元素數量皆與現況相同，僅 inline style（排版）與三顆按鈕的顯示文字內容改變
```

---

## SDLCAIP2-43：會議紀錄匯出 PDF 版面跑版，英文文字斷行異常且部分文字超出頁面範圍

### 使用者故事

As a 使用會議紀錄匯出功能的使用者, I want PDF 匯出版面在中英文混合內容下正確換行且不超出頁面邊界, so that 我能直接把匯出的 PDF 分享或存檔，而不需要因排版跑掉而回頭核對畫面內容或手動修正。

### 驗收條件（Gherkin）

```gherkin
Feature: 會議紀錄匯出 PDF 版面修正

  Scenario: 中英文混合的摘要/討論重點內容換行後每一行寬度不超出頁面可視範圍
    Given 一筆會議紀錄的摘要或討論重點內容包含長度足以超過單行可視寬度的中英文混合文字
    When 將該筆會議紀錄匯出為 PDF
    Then PDF 每一行文字以 NotoSansTC 字型、對應字級量測的渲染寬度皆不超過頁面可用內容寬度（頁寬扣除左右邊界）

  Scenario: 英文單字不會被從中間硬拆到下一行
    Given 會議紀錄內容中含有一個完整英文單字或英文專有名詞（例如系統名稱），且該單字所在位置接近换行邊界
    When 將該筆會議紀錄匯出為 PDF
    Then PDF 換行後，該英文單字必須完整出現在同一行內，不得被拆成兩個片段分別出現在相鄰兩行

  Scenario: 決定事項與待辦事項內容（含較長英文專有名詞）也會被正確換行，不會整行超出頁面邊界
    Given 一筆會議紀錄的決定事項或待辦事項中，任一項目文字（含前綴如「- 」「[負責人] ... （期限：...）」）長度足以超過單行可視寬度
    When 將該筆會議紀錄匯出為 PDF
    Then 該項目文字會換行顯示在多行，且每一行渲染寬度皆不超過頁面可用內容寬度

  Scenario: 純中文或短英文內容的既有匯出行為不受影響（迴歸）
    Given 一筆會議紀錄的摘要、決定事項、待辦事項、討論重點內容皆為單行可視寬度以內的短文字（中文或英文皆可）
    When 將該筆會議紀錄匯出為 PDF
    Then PDF 內容文字層（以 pypdf 抽取）仍可正確擷取到與原始內容一致的文字，不因換行邏輯調整而遺漏或重複文字
```

---

## SDLCAIP2-44：Design System｜基礎建設

### 使用者故事

As a 產品負責人, I want 全站導入 design-system 的色彩／字體／間距／圓角／尺寸 token，並將現有全站共用樣式（`<style>` 區塊中的 .btn、.card、.badge 共用 class）與全站共用 `<header>`（含移除裝飾性 icon、RWD 拆列規則）改用這些 token，同時新增一份可重用的 `.input` class 定義供後續工單沿用, so that 之後逐一調整各畫面時，都能直接沿用同一套已落地的視覺基礎，不必每張票各自重複定義。

### 驗收條件（Gherkin）

```gherkin
Feature: Design System 基礎建設

  Scenario: tokens 已導入頁面
    Given 開啟 src/frontend/index.html
    Then 頁面載入 docs/design-system/tokens.css 所定義的完整 token 集合（色彩、字體、8px 間距尺、圓角、控制項/頁首尺寸、breakpoint-mobile）
    And <head> 內已加入 Noto Sans TC 與 JetBrains Mono 的 Google Fonts 連結

  Scenario: 共用 .btn 樣式改用 token
    Given 檢視 index.html 現有 <style> 區塊中的 .btn / .btn-primary / .btn-outline / .btn-sm 規則
    Then 其顏色、高度（40px/44px）、圓角、字級等數值改為引用對應 token 變數
    And 手機版（<480px）維持/補上與 Button 元件規格一致的行為（高度改用 control-h-mobile）

  Scenario: 共用 .card 樣式改用 token
    Given 檢視 index.html 現有 .card 規則
    Then 背景、邊框、圓角、內距改為引用 surface / border / radius-md / space-6 token
    And 新增手機版（<480px）內距改用 space-5（24px）的媒體查詢規則

  Scenario: 共用 badge 樣式改用 token
    Given 檢視 index.html 現有 .section-title .badge 規則
    Then 其背景、邊框、文字色改為引用 badge-bg / badge-border / badge-text token
    And 圓角改為 radius-pill、字級對齊 caption token

  Scenario: 新增可重用的 .input class（不套用到現有元素）
    Given 檢視 docs/design-system/tokens.css 已定義的 .input 規則
    Then index.html 的 <style> 區塊新增對應的 .input class 定義
    And 不修改任何現有的畫面專屬 input/select 選取器，留給後續工單各自視情況改用

  Scenario: 頁首移除裝飾性 icon
    Given 開啟已登入畫面，檢視全站共用 <header>
    Then 「管理者儀表板」「歷史紀錄」按鈕文字不再含裝飾性 icon 前綴

  Scenario: 頁首 RWD — 桌面版（≥480px）
    Given 瀏覽器視窗寬度 ≥480px
    Then 頁首維持單列，高度對應 header-h-desktop（72px）

  Scenario: 頁首 RWD — 手機版（<480px）
    Given 瀏覽器視窗寬度 <480px
    Then 頁首拆成兩列，第一列僅保留標題與登出按鈕，第二列為可橫向捲動的次要導覽列

  Scenario: 範圍外畫面視覺不受影響
    Given 本工單完成後，其餘畫面尚未被後續工單調整
    Then 這些畫面的視覺呈現與施工前相比不得有非預期改變
```

---

## SDLCAIP2-45：Design System｜管理者儀表板頁 view-admin

### 使用者故事

As a 使用管理者儀表板（view-admin）的管理者, I want 這個畫面的版面、字體、色彩、表格樣式套用 design-system 規範（沿用 SDLCAIP2-44 已建立的 `--ds-*` token）, so that 我看到的管理介面與系統其他畫面呈現一致的視覺語言，且在手機上也能正常操作。

### 驗收條件（Gherkin）

```gherkin
Feature: Design System｜管理者儀表板頁 view-admin

  Scenario: view-admin 卡片延續既有 .card token
    Given 使用者以管理者身份開啟 view-admin
    Then .card 容器的背景/邊框/圓角與其他畫面一致（沿用 SDLCAIP2-44 既有規則）

  Scenario: view-admin 內的表格改用 design-system token，且不影響其他畫面
    Given view-admin 內「依日期」「依使用者」兩個表格使用共用 class .action-table
    Then 這兩個表格的背景/邊框/文字色改為 design-system token，透過限定在 view-admin 範圍內的選取器實作
    And .action-table 共用 class 本身的定義不被修改，view-result 與 view-history 的表格外觀不變

  Scenario: 子標題套用 design-system 字體規則
    Given view-admin 內的「依日期」「依使用者」子標題目前為瀏覽器預設樣式
    Then 改為套用 design-system 字體與文字顏色 token

  Scenario: 窄螢幕（<480px）下表格不發生橫向溢出跑版
    Given 使用者以小於 480px 寬度檢視 view-admin
    Then 頁面不出現橫向捲軸，表格文字/欄位可完整閱讀

  Scenario: view-admin 內無殘留裝飾性 icon
    Given design-system 規則不使用裝飾性圖示
    Then view-admin 的卡片標題、按鈕、表格欄位皆無裝飾性 icon/emoji

  Scenario: 範圍外畫面視覺不受非預期影響
    Given view-upload/view-progress/view-result/view-history 等其他畫面
    Then 本票變更合併後，除 .action-table 共用定義保持不變所保障的表格外觀外，其餘既有樣式不受本票影響
```

---

## SDLCAIP2-47：Design System｜上傳頁 view-upload

### 使用者故事

As a 上傳會議錄音的使用者, I want 上傳頁的版面、字體、色彩與元件樣式套用 design-system 規範（沿用 SDLCAIP2-44 的 --ds-* token）, so that 首次進入系統即感受到一致、清楚的視覺，手機上也能順利操作。

### 驗收條件（Gherkin）

```gherkin
Feature: Design System｜上傳頁 view-upload

  Scenario: view-upload 卡片延續既有 .card token
    Given 使用者開啟上傳頁（view-upload）
    Then .card 容器的背景/邊框/圓角與其他畫面一致（沿用 SDLCAIP2-44 既有規則）

  Scenario: 上傳頁標題移除 emoji
    Given 使用者檢視 view-upload 頁面標題
    When 查看標題文字內容
    Then 標題應顯示「上傳錄音檔」，不含裝飾性 emoji（原本的「📤」應被移除）

  Scenario: 拖放區與上傳按鈕內移除裝飾性 SVG icon
    Given 使用者檢視上傳頁的拖放區與上傳按鈕
    When 觀察其中的 SVG icon 元素
    Then 拖放區與上傳按鈕內應無裝飾性 SVG icon
    And 按鈕的 disabled/reset 行為保持不變

  Scenario: 拖放區邊框、圓角、hover-dragover 改用 --ds-* token
    Given 使用者檢視上傳頁的拖放區（#drop-zone）
    When 檢視其 CSS 屬性
    Then 邊框、圓角、hover-dragover 狀態改用 --ds-* 灰階 token（不再使用 var(--border)/var(--radius)/var(--primary)/#EFF6FF）

  Scenario: 已選檔案區塊背景與文字色改用 --ds-* token
    Given 使用者選擇檔案後，已選檔案區塊（#file-info/.fname）顯示
    When 檢視該區塊的 CSS 屬性
    Then 背景色與文字色改用 design-system token

  Scenario: 上傳按鈕延續全域 .btn/.btn-primary token
    Given 使用者檢視上傳頁的上傳按鈕
    When 檢視其樣式
    Then 按鈕延續 SDLCAIP2-44 定義的全域 .btn/.btn-primary token（不另外定義頁面專屬樣式）

  Scenario: 窄螢幕（<480px）下維持既有 RWD
    Given 使用者以小於 480px 寬度檢視 view-upload
    Then 按鈕顯示為全寬、卡片內距維持現有 RWD 規則，不出現非預期的橫向捲軸

  Scenario: 其他畫面與 header 不受影響，#upload-error 維持紅色
    Given view-progress/view-result/view-history 等其他畫面已套用 design-system
    When 本 Story 的變更合併後
    Then 其他畫面視覺不因本票而改變；#upload-error 元素維持紅色（design-system 無錯誤色票，不在本工單擴充 token）
```

### 範圍外

* 共用 class 本體（.card/.btn 等）——SDLCAIP2-44 已定義
* 上傳/轉錄後端與 API
* 「多欄表單窄螢幕單欄堆疊」（view-upload 沒有多欄表單，不適用）
* #upload-error 錯誤色不改灰階（design-system 無錯誤色票，不在單頁工單擴充 token）
* 隱藏的 #file-input 不套用 .input
* 不建新建置流程

### 依賴

* SDLCAIP2-44（已合併）
* docs/design-system/

### 狀態

G1 approved 2026-09-24 → Designing

---

## SDLCAIP2-50：Design System｜歷史紀錄列表頁 view-history

### 使用者故事

As a 查看歷史紀錄列表的使用者, I want 畫面的版面、字體、色彩與列表樣式套用 design-system 規範, so that 瀏覽過去會議紀錄清單時與系統其他畫面視覺一致。

### 驗收條件

- AC1：.card 沿用既有 token（回歸）
- AC2：#history-table 表格：th 背景 --ds-badge-bg、th 文字 --ds-text-secondary、td 文字 --ds-text-primary、th/td 下框線 --ds-border、字體 --ds-font-sans，以 #view-history 前綴選取器實作、不改 .action-table 共用本體
- AC3：空清單提示文字色 --ds-text-secondary，以 #view-history .empty-state 實作、不改共用本體
- AC4：「歷史紀錄」標題移除 📜
- AC5：<480px 表格不造成頁面級橫向捲軸且欄位可讀（技術手法由設計文件決定）
- AC6：點擊列開啟詳情頁行為不變（回歸）
- AC7：空狀態顯示/隱藏邏輯不變（回歸）
- AC8：其他畫面的 .action-table/.empty-state/.card 不受影響（回歸）

### 範圍外

* 共用樣式與頁首（SDLCAIP2-44）
* /api/meetings 查詢/分頁行為
* 修改 .action-table/.empty-state/.card 共用本體
* .section-title 本體字級/字色 token 化（沿用 SDLCAIP2-45 先例）
* view-history-detail（SDLCAIP2-48）與 view-result（SDLCAIP2-49）
* docs/design-system/ 文件

### 依賴

* SDLCAIP2-44（已合併）
* SDLCAIP2-45（已合併，#view-xxx .action-table 覆寫模式與 .ds-table-scroll）

### 狀態

G1 approved 2026-09-24 → Designing

---

## SDLCAIP2-46：Design System｜轉錄進度頁 view-progress

### 使用者故事

As a 等待轉錄進度的使用者, I want 進度頁的版面、字體、色彩與狀態提示樣式套用 design-system 規範，等待期間畫面風格與其他頁面一致，狀態提示清楚、不會誤認為可點擊按鈕, so that 我能清楚了解轉錄進度狀況且不被誤導操作。

### 驗收條件（Gherkin）

```gherkin
Feature: Design System｜轉錄進度頁 view-progress

  Scenario: 卡片標題移除 emoji
    Given 使用者進入 view-progress（轉錄進度頁）
    When 檢視頁面標題
    Then 卡片標題應顯示「處理中...」，不含裝飾性 emoji（移除「⚙️」）

  Scenario: 階段圖示移除 emoji，狀態仍靠底色深淺分辨
    Given 使用者檢視 .stage-icon 元素（#icon-uploaded/#icon-transcribed/#icon-done）
    When 觀察三種狀態（waiting/active/done）的呈現方式
    Then 三個圖示不應顯示 emoji（移除「📤」「🎙️」「✨」）
    And JS 仍可設定 stage-icon 的 waiting/active/done 狀態
    And 三種狀態仍可靠底色深淺分辨，不因移除 emoji 而改變狀態識別能力

  Scenario: 進度視覺元素改用 design-system token
    Given 使用者檢視進度頁的進度條與狀態圖示
    When 檢視其 CSS 屬性
    Then .stage-icon 三種狀態、.progress-bar、.progress-bar-wrap 改用 --ds-* 灰階 token
    And 不使用 --primary/--success/--warning/--danger 或寫死色碼

  Scenario: 文字字體套用 design-system 字體規則
    Given 使用者檢視 view-progress 內的所有文字
    When 檢視其 CSS 屬性
    Then view-progress 的文字應套用 var(--ds-font-sans)

  Scenario: 間距對應 design-system token
    Given 使用者檢視 .stage-list 與 .stage-item 的間距
    When 檢視其 CSS 屬性
    Then .stage-list/.stage-item 間距改用 --ds-space-1~8 token

  Scenario: 狀態提示套用 Badge 樣式
    Given 使用者檢視 #progress-message（狀態提示區塊）
    When 檢視其視覺呈現與 CSS 屬性
    Then #progress-message 套用 Badge 樣式（--ds-badge-bg、1px solid --ds-badge-border、--ds-badge-text、--ds-radius-pill）
    And 無 cursor:pointer 與 hover 樣式
    And 不改 .section-title .badge 共用規則（依 SDLCAIP2-53 人類決策：選項 A）

  Scenario: 取消按鈕視覺明確不同於狀態提示
    Given 使用者檢視取消按鈕
    When 檢視其視覺呈現
    Then 取消按鈕沿用 .btn.btn-outline.btn-sm，與狀態提示視覺明確不同
    And onclick 行為不變

  Scenario: 輪詢行為與 JS 命名不變（回歸）
    Given 使用者進入 view-progress 並等待轉錄進度更新
    When 輪詢 updateProgressUI() 行為執行
    Then updateProgressUI() 行為、JS/id/class 命名維持現況不變

  Scenario: 其他畫面不受影響（回歸）
    Given view-upload/view-result/view-history/view-admin 等其他畫面
    When 本 Story 的變更合併後
    Then 其他畫面的視覺呈現不受本票影響，僅 view-progress 使用的選取器被改變
```

### 範圍外

* 共用樣式與頁首（.card/.btn，SDLCAIP2-44）
* 輪詢邏輯與 API
* 新增各階段狀態文案（SDLCAIP2-53 已決定採選項 A）
* 其他畫面專屬樣式與 .action-table
* docs/design-system/ 文件

### 依賴

* SDLCAIP2-44（已合併）
* SDLCAIP2-53（HUMAN-INPUT，已回答選項 A）
* docs/design-system/

### 狀態

G1 approved 2026-09-24 → Designing

---

## SDLCAIP2-55：Design System｜會議紀錄結果頁 view-result — 會議紀錄分頁卡片群（拆自 SDLCAIP2-49）

### 使用者故事

As a 查看會議紀錄結果頁「會議紀錄」分頁的使用者, I want 會議資訊、摘要、待辦事項、決定事項、討論重點五張卡片的標題、文字、表格、清單樣式套用 design-system 規範, so that 我在瀏覽與編輯會議紀錄內容時，視覺與系統其他畫面一致、清楚易讀。

### 驗收條件（Gherkin）

```gherkin
Feature: view-result 會議紀錄分頁卡片群套用 design-system

  Scenario: AC1 卡片標題套用 Heading h2 token（#view-result 前綴覆寫）
    Then #view-result .section-title 為 h2 18px/26px/600（手機 17px/24px/600）、--ds-text-primary；共用 .section-title 本體不變

  Scenario: AC2 會議資訊欄位套用 Input 元件樣式（詳情頁連帶變更）
    Then .meeting-info-grid label/input 改用 --ds-* token；<480px 單欄堆疊；onchange 綁定不變

  Scenario: AC3 摘要文字套用 Body token
    Then #summary-text 行高／顏色對應 body token；雙擊編輯提示邏輯不變

  Scenario: AC4 待辦事項表格套用 token（#view-result 前綴覆寫）
    Then #view-result .action-table th/td 比照 #view-admin；共用 .action-table 本體與 contenteditable 樣式不變

  Scenario: AC5 決定事項清單套用 token（詳情頁連帶變更）
    Then .decision-list 邊框 --ds-border；「✓」改 --ds-text-primary（原綠色）

  Scenario: AC6 討論重點手風琴套用 token（詳情頁連帶變更）
    Then .topic-item/.topic-header/.topic-body 改用 --ds-* 灰階 token；toggleTopic() 行為不變

  Scenario: AC7 窄螢幕（<480px）待辦表格不造成頁面級橫向捲軸

  Scenario: AC8 既有編輯／儲存 JS 行為不受影響（回歸）
```

### 範圍外

* 標題、操作列、Tabs（SDLCAIP2-54）；逐字稿分頁（SDLCAIP2-56）
* `.card` 共用本體；`.action-table`／`.empty-state`／`.section-title` 共用本體（只新增 `#view-result` 前綴覆寫）
* PDF/Word 匯出檔案樣式；全站共用樣式與頁首（SDLCAIP2-44）

### 依賴

* SDLCAIP2-44（已合併）；SDLCAIP2-45（已合併，前綴覆寫先例）
* SDLCAIP2-48 將沿用本票 `#view-result .section-title`／`.action-table` 的數值（SDLCAIP2-58 決議）

### 狀態

G1 approved 2026-09-24 → Designing
