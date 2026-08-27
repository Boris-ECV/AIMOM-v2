# 設計文件 — SDLCAIP2-2 健康檢查端點 v2

## 對應需求規格
G1 已核准的需求規格（本 ticket 描述）：新增公開（無需認證）的健康檢查端點
`/api/health-check-v2`，回傳 `{"status": "ok", "version": <非空字串>}`，
狀態碼 200；路由定義不得依賴 `Depends(get_current_user)`。範圍外明確排除：
不修改既有 `/api/health`、不引入新套件/前端變更、不做真實服務健康檢查、
version 字串來源交由設計/開發階段依既有慣例決定。

## 介面/API 契約

新增端點，方法與既有 `/api/health` 完全一致的形狀：

```
GET /api/health-check-v2
```

- 認證：無（不掛 `Depends(get_current_user)`，也不透過
  `app.include_router(..., dependencies=_auth_dep)` 掛載——直接以
  `@app.get(...)` 定義在 `app.py`，與現有 `/api/health` 同一種寫法）。
- 成功回應：
  - 狀態碼：`200`
  - Body（`application/json`）：
    ```json
    { "status": "ok", "version": "1.0.0" }
    ```
    - `status`：固定字串 `"ok"`（本故事範圍外不做真實依賴健康檢查）。
    - `version`：非空字串，來源見下方「關鍵技術決策」。
- 錯誤情境：本端點無業務邏輯、無外部依賴呼叫，不需要額外的
  try/except；任何未預期例外會落入 `app.py` 既有的全域
  `@app.exception_handler(Exception)`（沿用既有失敗處理慣例，不重複兜底）。
- 路由位置：直接寫在 `src/app.py`，緊鄰既有 `/api/health` 定義之後
  （不建立新的 `APIRouter` 檔案）——因為 `/api/health` 本身就是這種「掛在
  app 上、不走模組化路由檔」的例外寫法，`health-check-v2` 屬性與其相同
  （探測用、無業務邏輯），維持既有結構一致性優先於套用「一功能一路由檔」
  慣例（該慣例是給有業務邏輯的功能模組用的，見 `upload.py` /
  `transcribe.py` 等）。

## 資料模型
無新增資料模型。本端點不讀寫 DynamoDB、不新增欄位或資料表。

## 關鍵技術決策

- **version 字串來源：使用 `app.version`（FastAPI 建構時已設定的
  `FastAPI(title="Meeting Minutes API", version="1.0.0")`），不在
  `config.py` 新增 `APP_VERSION` 之類的環境變數。**
  理由：spec 範圍外註記「version 字串來源不指定，由開發階段依既有
  config.py 慣例決定」，但實際檢視 `config.py` 後，其中並無任何版本號相關
  的既有慣例可延續——唯一已存在、非空、且與「API 版本」語義相符的既有值
  是 `app.py` 建構 `FastAPI(...)` 時傳入的 `version="1.0.0"`。依
  CONSTITUTION「範圍紀律」與「避免不必要的抽象層」原則，不為此低風險探測
  端點新增一個全新的 config 讀取路徑；直接讀取執行中 app 物件已有的
  `app.version` 屬性（在同一支 `app.py` 內即可存取，例如
  `async def health_check_v2(): return {"status": "ok", "version": app.version}`）
  是風險最低、不引入新狀態來源的做法。
- **不建立獨立路由檔/`APIRouter`，直接寫在 `app.py`。**
  理由：與現有 `/api/health` 一致——探測端點無業務邏輯，`app.py` 已對
  `/api/health` 採用「直接掛在 app 上、不進 `_auth_dep` 清單」的例外寫法，
  新端點屬性相同，跟隨既有例外模式而非套用一般功能模組的路由檔慣例。
- **不新增測試檔，沿用 `src/tests/` 既有慣例交由開發階段處理。**
  本設計不涉及測試實作，僅指出：既有 `conftest.py` 的
  `_override_auth` autouse fixture會讓所有測試預設「已登入」，若要驗證
  Scenario 1（未帶 token 仍可呼叫成功）需注意——因為端點本身不掛
  `Depends(get_current_user)`，autouse fixture 覆寫與否對此端點行為無影響，
  該情境天然滿足，開發/測試階段可直接呼叫、不需特別停用 fixture。

## 開放設計問題（定稿時必須為空）
無。
