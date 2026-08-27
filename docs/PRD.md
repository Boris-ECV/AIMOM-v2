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
