# 設計文件 — SDLCAIP2-66 管理者白名單資料表與管理 API（含 infra）

## 對應需求規格
G1 定稿版（2026-10-07 通過，見工單 SDLCAIP2-66 描述；SDLCAIP2-63 的子 Story A）：
新增 DynamoDB 資料表 `${local.name_prefix}-allowed-users`（PK = `email`），
並提供管理者專用 CRUD API `GET/POST /api/admin/allowed-users`、
`DELETE /api/admin/allowed-users/{email}`；同步補齊 IAM 與 Lambda 環境變數。
**登入檢查（`src/auth.py` 的 `ALLOWED_EMAILS` 環境變數邏輯）本 Story 完全不動**，
新資料表此階段不被 auth 讀取；改讀 DB、`/api/me` 的 `last_login`、移除
`ALLOWED_EMAILS`、前端 UI（SDLCAIP2-64）、稽核紀錄、多環境、快取皆屬 SDLCAIP2-67 或範圍外。

### 現況（已讀取程式碼確認）
- `src/admin.py`：`router = APIRouter()`，無 prefix，路由寫完整子路徑
  （`@router.get("/admin/usage", ...)`，以 `Depends(require_admin)` 保護）；
  `src/app.py` 以 `app.include_router(admin_router, prefix="/api")` 掛載，
  **不**套 `_auth_dep`（admin 自己依賴 `require_admin`，其內部依賴 `get_current_user`）。
- `src/auth.py`：`require_admin` 角色非 admin → 403；`get_current_user` 無/壞 token → 401；
  `_get_allowed_emails()` 讀 `config.ALLOWED_EMAILS`。以上全部沿用、不修改。
- `src/config.py`：`DYNAMODB_MEETINGS_TABLE` / `DYNAMODB_LLM_USAGE_TABLE` / `DYNAMODB_JOBS_TABLE`
  皆為 `os.getenv("DYNAMODB_..._TABLE", "aimom-...")`，區域用 `config.COGNITO_REGION`。
- DynamoDB 存取慣例（`usage.py` / `db.py` / `jobstore.py`）：模組內 `_resource()`
  （`boto3.resource("dynamodb", region_name=config.COGNITO_REGION)`）、`_table()`、
  `ensure_*_table_exists()`：`list_tables()` 遇 `AccessDeniedException` 視為「已由 IaC 建好」直接 return，
  其他 `ClientError` 往上拋；表不存在才 `create_table(... PAY_PER_REQUEST)` + waiter（僅本機/moto 實際作用，
  因 Lambda 角色刻意不授予 ListTables/CreateTable）。
- `infra/iam.tf` `DynamoDBAccess` 現有 actions：GetItem/PutItem/Query/Scan/DeleteItem/UpdateItem
  （**已足夠**，不需新增 action）；resources 目前為 `aws_dynamodb_table.meetings.arn`、
  `.llm_usage.arn`、`.jobs.arn`。
- `infra/lambda.tf` env 區塊已有 `DYNAMODB_MEETINGS_TABLE` / `DYNAMODB_LLM_USAGE_TABLE` / `DYNAMODB_JOBS_TABLE`
  （等號對齊風格）；`ALLOWED_EMAILS = var.allowed_emails` 已存在（SDLCAIP2-61），保持不動。
- 測試基礎（已讀 `src/tests/conftest.py`、`test_usage_admin.py`）：見「關鍵技術決策」末段「測試做法」。
- 跨元素樣式耦合測試：本 Story 無前端/樣式變更，不適用。

## 介面/API 契約

三條路由皆寫在 `src/admin.py` 既有 `router` 上（沿用無 prefix、完整子路徑寫法），
皆 `Depends(require_admin)`；最終路徑為 `/api/admin/allowed-users[...]`。

共同行為：無 token / token 無效 → 401（`get_current_user`）；非 admin → 403（`require_admin`），
且 403/401 在進入 handler 之前發生，資料表不被讀寫；DynamoDB 任何例外 → 5xx（見決策 4），絕不回成功。

### GET `/api/admin/allowed-users`
- 200：JSON 陣列，依 `email` 升冪排序（Python `sorted`，因 Scan 無序）。
  ```json
  [
    {"email": "a@example.com", "last_login": null},
    {"email": "b@example.com", "last_login": "2026-10-01T08:30:00Z"}
  ]
  ```
- 每個元素僅兩欄：`email`(str)、`last_login`(ISO-8601 UTC 字串或 `null`)。表中無 `last_login` 屬性即 `null`。
  `last_login` 以字串原樣儲存、原樣回傳（本 Story 不寫入它；寫入由 SDLCAIP2-67 負責，格式約定為 `YYYY-MM-DDTHH:MM:SSZ`）。
- Scan 需處理分頁（`LastEvaluatedKey` 迴圈），避免 1MB 截斷漏資料。空表回 `[]`。

### POST `/api/admin/allowed-users`
- Request body：`{"email": "<string>"}`，以 Pydantic model `AllowedUserCreate` 驗證：
  1. `field_validator("email", mode="before")`：非 str 直接交由型別驗證失敗；str 則 `strip().lower()`。
  2. 格式驗證：正則 `^[^@\s]+@[^@\s]+\.[^@\s]+$`（單一 `@`、網域含 `.`、無空白）；
     不符 → `ValueError` → FastAPI 預設 **422**，**不寫入**（驗證發生於 handler 之前）。
- 回應：
  - 新增 → **201** `{"email": "<normalized>", "last_login": null}`
  - 已存在 → **200** `{"email": "<normalized>", "last_login": <既有值或 null>}`（冪等，**不覆寫**既有項目，保留既有 `last_login`）
- 實作：`put_item(Item={"email": e}, ConditionExpression="attribute_not_exists(email)")`；
  成功 → 回 201；`ClientError` code 為 `ConditionalCheckFailedException` → 改 `get_item` 取既有 `last_login` 回 200。
  不用「先 get 再 put」（有 race 且多一次往返）。

### DELETE `/api/admin/allowed-users/{email}`
- 成功 → **204**（無 body）。email 不在清單 → **404**（`{"detail": "找不到此 email"}`）。
- 實作：`delete_item(Key={"email": e}, ConditionExpression="attribute_exists(email)")`；
  `ConditionalCheckFailedException` → 404。
- path 參數正規化：與 POST 同一個函式 `normalize_email()`（strip + lowercase），
  故 `DELETE /api/admin/allowed-users/Foo@Example.com` 會刪 `foo@example.com`。
  `@` 的 URL 編碼：Starlette 會先對 path 做 percent-decode 再比對/注入 path 參數，
  因此 `a@example.com` 與 `a%40example.com` 兩種寫法收到的 `email` 值相同（`a@example.com`），handler 不需額外 `unquote`
  （額外 unquote 反而會對含 `%` 的輸入雙重解碼）。DELETE 的 path 參數**不**做格式驗證：
  格式不符的字串不可能存在於表中，直接走條件刪除得 404，語意一致且不增加規格外的 422 分支。
  normalize 後為空字串（例如 `/allowed-users/%20`）同樣走條件刪除 → 404（空字串不能作 DynamoDB key，
  需先在 handler 判斷 `if not e: raise HTTPException(404)`，避免 DynamoDB `ValidationException` 變成 500）。

## 資料模型

新增資料表 `aws_dynamodb_table.allowed_users`（`infra/dynamodb.tf`，比照既有表風格與 tags）：

| 項目 | 值 |
|---|---|
| name | `"${local.name_prefix}-allowed-users"` |
| billing_mode | `PAY_PER_REQUEST` |
| hash_key | `email`（S），無 range key、無 GSI、無 TTL |
| item 屬性 | `email`(S, 小寫正規化)；`last_login`(S, ISO-8601 UTC，可缺；本 Story 不寫入) |

```hcl
resource "aws_dynamodb_table" "allowed_users" {
  name         = "${local.name_prefix}-allowed-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "email"

  attribute {
    name = "email"
    type = "S"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
```

其他 infra / config 變更（確切內容）：
- `infra/iam.tf`：`DynamoDBAccess.resources` 清單新增一項
  `aws_dynamodb_table.allowed_users.arn,`（接在 `aws_dynamodb_table.jobs.arn,` 之後；actions 不變）。
- `infra/lambda.tf`：env 區塊新增
  `DYNAMODB_ALLOWED_USERS_TABLE = aws_dynamodb_table.allowed_users.name`（置於 `DYNAMODB_JOBS_TABLE` 之後；
  既有行的對齊空格不需動，新行自行排版即可）。
- `src/config.py`：在 DynamoDB 區塊新增
  `DYNAMODB_ALLOWED_USERS_TABLE = os.getenv("DYNAMODB_ALLOWED_USERS_TABLE", "aimom-allowed-users")`。
- 不改 `variables.tf`、`ci.yml`（無新 Terraform 變數；`ALLOWED_EMAILS` 串接已在 SDLCAIP2-61 完成）。

### 新模組 `src/allowed_users.py`（資料存取層，供 SDLCAIP2-67 重用）
完全比照 `usage.py` / `db.py` 慣例：

```python
def normalize_email(raw: str) -> str            # strip().lower()
def _resource() / _table()                       # boto3 resource + config.DYNAMODB_ALLOWED_USERS_TABLE
def ensure_allowed_users_table_exists() -> None  # 同 ensure_usage_table_exists：AccessDenied 略過；
                                                 # 不存在才 create_table(KeySchema email HASH, PAY_PER_REQUEST)
def list_users() -> list[dict]                   # Scan(分頁) → [{"email","last_login"|None}] 依 email 排序
def add_user(email: str) -> tuple[dict, bool]    # 條件 put；回 (item, created)；已存在時 created=False 並帶既有 last_login
def remove_user(email: str) -> bool              # 條件 delete；True=已刪，False=原本不存在
```
- 每個公開函式開頭呼叫 `ensure_allowed_users_table_exists()`（同既有模組）。
- 錯誤：`ConditionalCheckFailedException` 在模組內轉為回傳值（`created=False` / `False`）；
  其他 `ClientError`/`BotoCoreError` 不吞，往上拋，由 `admin.py` 轉為 5xx。
- **SDLCAIP2-67 擴充點（本 Story 不實作）**：67 可在同一模組新增
  `get_all_emails() -> set[str]`（供 auth 登入檢查）、`touch_last_login(email)`（`update_item` 只 SET `last_login`）、
  以及快取與其失效（`add_user`/`remove_user` 成功後呼叫 invalidate）。因 `admin.py` 只透過本模組函式存取資料表，
  67 無需改動路由即可加入快取失效。

## 關鍵技術決策
1. **email 格式驗證用正則而非 `pydantic.EmailStr`**：`src/requirements.txt` 無 `email-validator`，
   `EmailStr` 會要求新增相依；spec 只要求「格式驗證」，簡單正則已足夠且零新增相依。
2. **POST 冪等用條件 put（`attribute_not_exists(email)`）而非先查後寫**：單一原子操作，
   不會有 check-then-put race，且保證不覆寫既有 `last_login`（AC 明確要求）；已存在時才多一次 `get_item`。
3. **DELETE 用條件刪除（`attribute_exists(email)`）區分 204/404**：DynamoDB `delete_item` 對不存在 key 預設成功，
   不加條件就無法回 404。
4. **DynamoDB 例外 → 明確 5xx**：`admin.py` 對 `ClientError`/`BotoCoreError`（排除已處理的條件失敗）捕捉後
   `raise HTTPException(status_code=503, detail="白名單資料表暫時無法存取")`。理由：`app.py` 的全域
   `Exception` handler 雖也會回 500，但在 Starlette 中該路徑會於回應送出後重新拋出例外，
   導致 `TestClient` 預設（`raise_server_exceptions=True`）測試中直接拋例外而非得到 5xx 回應；顯式 `HTTPException`
   讓行為在正式環境與測試中一致且可斷言「回應為 5xx 且非成功」。依據 CONSTITUTION「失敗處理哲學」：
   對 DynamoDB 等外部依賴用 `try/except Exception` 轉成帶中文訊息的 `HTTPException`（此處需要比全域 500 兜底
   更精確的錯誤碼，屬該原則允許的例外），且沿用既有 `except Exception`（BLE001）慣例；先 `except HTTPException: raise` 以免吞掉 404。
5. **路由放進既有 `admin.py` 而非新 router/檔案**：CONSTITUTION「程式碼風格」是「每功能一個 router 檔」，
   但同一原則的「安全預設」把 `/api/admin` 視為一個路由分組；`admin.py` 已是該分組、已以 `/api` 掛載且不套 `_auth_dep`，
   零改動 `app.py`，也避免新 router 漏掛 `require_admin`。資料存取邏輯則獨立成 `allowed_users.py`，不塞進路由檔。
   角色判定仍走 `ADMIN_EMAILS` 白名單環境變數（本 Story 新表只是「登入白名單」，不是角色儲存，未違反安全預設）。
6. **不改 `auth.py`、不讀新表**：spec 明確要求登入檢查此 Story 完全不變；測試須保證 `test_auth.py` 全數維持綠燈。
7. **Scan 分頁迴圈**：白名單預期很小，但 Scan 單頁 1MB 上限是正確性問題而非效能問題，成本低故一併處理。
8. **email 一律以小寫儲存**：與 `auth.py` 比對時 `email.lower()` 的慣例一致，67 切換登入檢查到 DB 時可直接比對。

### 測試做法（已讀取驗證的事實，供 developer/tester 依循）
- 使用 **moto**（`moto[dynamodb]>=5.0.0` 在 `src/requirements.txt`），非手寫 stub。`src/tests/conftest.py` 有
  `autouse` fixture `_mock_dynamodb`：`with mock_aws(): yield`，所以所有測試預設已在 moto 內，
  AWS 憑證/區域環境變數由 conftest 以 `setdefault` 設好（region `ap-northeast-1`，與 `config.COGNITO_REGION` 預設一致）。
- 另一個 `autouse` fixture `_override_auth`：`app.dependency_overrides[get_current_user] = _fake_current_user`
  （固定回 `CurrentUser(email="test-user@example.com", role="user")`），結束時 pop。
  **只覆寫 `get_current_user`，不覆寫 `require_admin`**——`require_admin` 因此會真的執行並讀取覆寫後的角色。
  既有慣例（`test_usage_admin.py::test_admin_usage_endpoint_requires_admin`）：測試內另行
  `app.dependency_overrides[get_current_user] = lambda: CurrentUser(email=..., role="admin"/"user")`，
  `finally` 中 `pop`。本 Story 的 admin 情境照此寫（`role="admin"` 覆寫 `get_current_user`），403 情境用 `role="user"`。
  「無 token → 401」情境需先 `app.dependency_overrides.pop(get_current_user, None)` 再不帶 Authorization 呼叫
  （既有 `test_auth.py` 有 25 處相關用法可參考）。
- 客戶端：`TestClient(app)`（httpx 已在 requirements）；因 conftest 已全域 `mock_aws`，不需再包一層，
  但既有測試檔也有自帶 `client` fixture 的 `with mock_aws()` 寫法，兩者皆可。
- 「DynamoDB 例外 → 5xx」測試：以 `monkeypatch.setattr` 讓 `allowed_users._table`（或 `put_item`）拋
  `botocore.exceptions.ClientError`，斷言 `status_code >= 500`（因決策 4 為顯式 503，無需 `raise_server_exceptions=False`）。
- 「table untouched」斷言：403/401/422 後直接用 `allowed_users._table().scan()` 驗證仍為空/不變。
- infra 靜態測試先例：`src/tests/test_infra_allowed_emails.py`（以 regex/yaml 解析 `infra/*.tf` 文字，
  無 terraform CLI）；本 Story 的 infra AC（資料表、IAM resources、Lambda env）可比照此寫法，
  另加 `config.DYNAMODB_ALLOWED_USERS_TABLE` 預設值 `"aimom-allowed-users"` 的測試（參考 `test_config.py`）。

## UI 原型
無，本 Story 不涉及前端 UI（僅後端 API、DynamoDB 資料表與 infra 設定；管理者白名單前端畫面屬 SDLCAIP2-64，不在本 Story 範圍）。

## 開放設計問題（定稿時必須為空）
無。
