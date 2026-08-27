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
