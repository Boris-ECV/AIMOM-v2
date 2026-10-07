# 設計文件 — SDLCAIP2-67 登入白名單改讀 DynamoDB、/api/me 更新 last_login、移除 ALLOWED_EMAILS

## 對應需求規格
G1 定稿版（2026-10-07 通過，見工單 SDLCAIP2-67 描述；SDLCAIP2-63 的子 Story B）。決策已由人類在 SDLCAIP2-65 確認（「全部同意建議」）：
1. 登入檢查改讀 SDLCAIP2-66 建立的 allowed-users 資料表；`ADMIN_EMAILS` 內的 email（管理者）**永遠允許**、不需有表列。
   空表 → 一般使用者 403；查表失敗且無未過期快取 → fail closed（403），管理者仍可登入。
2. 記憶體快取，TTL 60 秒（具名常數），仿 `_JWKS_CACHE`；同一 container 內管理 API 處理 POST/DELETE 時立即失效該 container 的快取
   （其他 container 靠 TTL 自然過期，須在程式碼註解與本文件載明）。
3. `GET /api/me` 驗證成功後更新 `last_login`（`YYYY-MM-DDTHH:MM:SSZ`，UTC），**僅限已在表中的 email**，管理者不在表中時不可被建立列；
   只有 `/api/me` 寫入；寫入失敗不影響登入（仍 200，錯誤寫 log）。
4. 完全移除 `ALLOWED_EMAILS`（config / auth / variables.tf / lambda.tf / tfvars.example / ci.yml），舊測試改寫或移除。

範圍外：資料表與管理 API 建立（SDLCAIP2-66）、前端 UI（SDLCAIP2-64）、管理者登入時間追蹤、稽核紀錄、多環境、
移除 GitHub secret `TF_VAR_allowed_emails`（人工步驟）、更動 `ADMIN_EMAILS` 機制。

### 前置相依與部署順序（重要）
**本 Story 必須在 SDLCAIP2-66 合併且部署後才能實作/部署**：本設計依賴 66 設計文件宣告的介面——
`src/allowed_users.py` 的 `normalize_email`、`_resource()`/`_table()`、`ensure_allowed_users_table_exists()`、`list_users()`、
`add_user(email) -> (item, created)`、`remove_user(email) -> bool`，`config.DYNAMODB_ALLOWED_USERS_TABLE`，
管理路由（`src/admin.py`）僅透過上述函式存取資料表，以及資料表（hash key `email`、可選字串屬性 `last_login`）與其 IAM/Lambda env。
截至撰寫時 66 尚在 PR #362 待人工 gate，`src/allowed_users.py` 尚未在 main，developer 須待 66 合併後再從最新 main 開工。

**上線風險（rollout constraint）**：本 Story 部署後，空表會讓所有一般使用者被鎖在外面（管理者不受影響）。
部署前必須先用 66 的 API（`POST /api/admin/allowed-users`）把允許名單填入資料表；原 `ALLOWED_EMAILS` 的內容須人工遷移。

### 現況（已讀取程式碼確認）
- `src/auth.py`：`verify_token` 解 JWT 後呼叫 `_get_allowed_emails()`（讀 `config.ALLOWED_EMAILS`）；
  「集合非空且 email 不在其中」才拋 `EmailNotAllowedError`（空集合 = 全放行；且管理者若不在清單內也會被拒，`test_verify_token_admin_not_in_allowlist_still_rejected`）。
  角色以 `_get_admin_emails()`（`config.ADMIN_EMAILS` 逗號分隔、strip+lower）判定。`get_current_user` 把 `EmailNotAllowedError` 轉 403
  （`此帳號未被授權使用本系統`）、`ValueError` 轉 401。`_JWKS_CACHE = {"keys", "fetched_at"}` + `_JWKS_TTL_SECONDS = 3600` 是既有快取慣例（`time.time()` 比較）。
- `src/app.py`：`get_me`（`GET /api/me`）為 `async def`，`Depends(get_current_user)`，回 `{"email","role"}`；已有 `logger`；
  全域 `Exception` handler 回 500。`admin_router` 以 `/api` 掛載、不套 `_auth_dep`。
- `src/config.py` 第 56 行 `ALLOWED_EMAILS`；`infra/variables.tf` 第 32–37 行 `variable "allowed_emails"`；`infra/lambda.tf` 第 66 行
  `ALLOWED_EMAILS = var.allowed_emails`；`infra/terraform.tfvars.example` 第 9 行；`.github/workflows/ci.yml` 第 123 行 `TF_VAR_allowed_emails`。
- `infra/iam.tf` `DynamoDBAccess` actions 已含 `GetItem/PutItem/Query/Scan/DeleteItem/UpdateItem`（已逐行確認 35–40 行），
  66 會把 `aws_dynamodb_table.allowed_users.arn` 加進 resources → **`UpdateItem`（touch last_login）與 `Scan`（讀白名單）已被涵蓋，本 Story 的 infra 變更只有「移除」，無新增**。
- 測試現況（已讀取）：`src/tests/conftest.py` 有 autouse `_mock_dynamodb`（`mock_aws()`）與 `_override_auth`（`get_current_user` 覆寫為
  `test-user@example.com`/`user`）。因此只有**繞過覆寫、真的走 `verify_token`** 的測試受影響，即 `src/tests/test_auth.py`（其餘檔案的
  `dependency_overrides.pop` 皆為 finally 清理或 `test_lambda_handler.py` 的免登入 health-check 路徑，不經 `verify_token`；`e2e_server.py` 亦覆寫 `get_current_user`）。
  autouse `mock_aws` 下白名單表預設為空 → 沒種資料的非管理者登入會變 403（見「測試遷移計畫」）。
- 跨元素樣式耦合測試：無前端/樣式變更，不適用。

## 介面/API 契約
對外 HTTP 契約僅 `GET /api/me` 的副作用與 403 判定規則變更，回應格式不變。

### `GET /api/me`
- 200 `{"email": "<token 的 email>", "role": "user"|"admin"}`（不變；**不回傳** last_login）。
- 認證順序（`get_current_user` → `verify_token`）：JWT 驗證失敗 → 401；通過後：
  - email（lower）在 `ADMIN_EMAILS` → role=admin，**不讀資料表**，直接通過；
  - 否則以白名單集合判定：在集合內 → 通過；不在（含空表）→ 403 `此帳號未被授權使用本系統`；查表失敗且無未過期快取 → 同樣 403（fail closed）。
- 通過後 handler 呼叫 `allowed_users.touch_last_login(user.email)`：email 在表中才更新 `last_login`；不在表中（含管理者）靜默略過、不建立列。
  該寫入的任何例外皆被捕捉並 `logger.exception`，**回應仍為 200**。
- 其他端點一律不寫 `last_login`（`touch_last_login` 只在 `get_me` 呼叫）。
- 66 的 `GET /api/admin/allowed-users` 已會回傳 `last_login`，本 Story 讓該欄位開始有值，路由無需修改。

### 內部介面（`src/allowed_users.py` 新增，66 檔案的擴充）
```python
CACHE_TTL_SECONDS = 60          # 具名常數；quote：其他 container 最多 60 秒後才看到變更

def get_all_emails() -> frozenset[str]
    # 回傳白名單 email 集合（小寫）。快取命中（age < CACHE_TTL_SECONDS）直接回傳，不碰 DynamoDB。
    # 未命中 → ensure_allowed_users_table_exists() + list_users() 取 email → 存入快取。
    # 查表任何例外直接往上拋（不回傳過期快取）；由 auth 層轉成 fail closed。
def invalidate_cache() -> None  # 立即清除本 container 快取
def touch_last_login(email: str, now: datetime | None = None) -> bool
    # update_item(Key={"email": normalize_email(email)},
    #             UpdateExpression="SET last_login = :t",
    #             ConditionExpression="attribute_exists(email)",
    #             ExpressionAttributeValues={":t": "<YYYY-MM-DDTHH:MM:SSZ>"})
    # now 缺省 datetime.now(timezone.utc)，格式 strftime("%Y-%m-%dT%H:%M:%SZ")。
    # 成功 True；ConditionalCheckFailedException（不在表中）→ False（不是錯誤、不記 log）；其他例外往上拋。
```
`add_user` / `remove_user`（66 已存在）改為在 `try/finally` 的 `finally` 呼叫 `invalidate_cache()`（見決策 4），因此 **`src/admin.py` 不需任何修改**。

### `src/auth.py` 變更（確切內容）
- 刪除 `_get_allowed_emails()`；`EmailNotAllowedError` docstring 改為「email 不在 allowed-users 資料表（且非管理者）」。
- 新增 `import logging`、`import allowed_users`，`logger = logging.getLogger(__name__)`。
- 新增：
  ```python
  def _load_allowed_emails() -> frozenset[str]:
      """讀白名單；任何失敗 fail closed（回空集合），並記錄錯誤。"""
      try:
          return allowed_users.get_all_emails()
      except Exception:  # noqa: BLE001
          logger.exception("讀取 allowed-users 資料表失敗，一般使用者登入將被拒絕（fail closed）")
          return frozenset()
  ```
- `verify_token` 尾段（取代原第 98–103 行）：
  ```python
  email_lc = email.lower()
  role = "admin" if email_lc in _get_admin_emails() else "user"
  if role != "admin" and email_lc not in _load_allowed_emails():
      raise EmailNotAllowedError(email)
  return CurrentUser(email=email, role=role)
  ```
  先算 role，管理者短路、完全不碰 DB（DB 掛掉時管理者仍可登入，才能用 66 的 API 修復名單）。
- `get_current_user`、`require_admin` 不變。

### `src/app.py` 變更
```python
@app.get("/api/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    try:
        allowed_users.touch_last_login(user.email)
    except Exception:  # noqa: BLE001
        logger.exception("更新 last_login 失敗（不影響登入）: %s", user.email)
    return {"email": user.email, "role": user.role}
```
（`import allowed_users`；email/role 直接來自 dependency 回傳的 `CurrentUser`，handler 不再讀表 → 無二次 DB 讀取。）

### 移除 `ALLOWED_EMAILS`（確切刪除範圍）
- `src/config.py`：刪第 56 行（`ADMIN_EMAILS` 行保留）。
- `infra/variables.tf`：刪 `variable "allowed_emails" { ... }` 整塊（第 32–37 行）及其後一個空行。
- `infra/lambda.tf`：刪第 66 行 `ALLOWED_EMAILS            = var.allowed_emails`（其餘 env 行不動）。
- `infra/terraform.tfvars.example`：刪第 9 行 `allowed_emails = ...`。
- `.github/workflows/ci.yml`：刪 terraform apply step env 的第 123 行 `TF_VAR_allowed_emails: ${{ secrets.TF_VAR_allowed_emails }}`。
- 不改 `infra/iam.tf`（UpdateItem 已含）。GitHub secret 之後由人類手動刪除（範圍外）。

## 資料模型
無新增資料模型。沿用 66 的資料表 `${local.name_prefix}-allowed-users`（hash key `email`，小寫）；
本 Story 開始寫入既有的選用屬性 `last_login`（S，`YYYY-MM-DDTHH:MM:SSZ`，UTC），僅以條件更新（`attribute_exists(email)`）寫入既有項目，
不新增欄位/索引/表。快取為 process 內記憶體（見下），不持久化。

### 快取結構（`allowed_users.py`，仿 `_JWKS_CACHE`）
```python
_CACHE: dict = {"emails": None, "fetched_at": 0.0, "generation": 0}
_CACHE_LOCK = threading.Lock()
```
- 命中條件：`_CACHE["emails"] is not None and time.time() - _CACHE["fetched_at"] < CACHE_TTL_SECONDS`。
- 讀取流程：鎖內檢查命中並記下 `generation`；未命中則**鎖外**查表（不在鎖內做網路 I/O）；取得結果後鎖內檢查
  `generation` 未變才寫入快取（否則只回傳本次結果、不寫快取），避免「查表進行中被 invalidate」後把舊資料寫回。
- `invalidate_cache()`：鎖內 `emails=None`、`fetched_at=0`、`generation += 1`。
- 空集合（空表）也快取（`frozenset()` 不是 `None`），避免空表時每次登入都打 DynamoDB；查表**失敗**不寫快取（下次請求重試）。

## 關鍵技術決策
1. **管理者短路在 DB 讀取之前**：先算 role，admin 直接放行。理由：AC 要求管理者永遠可登入，且 DB 故障時管理者必須還能進來修復；也省一次讀取。
2. **快取放 `allowed_users.py` 而非 `auth.py`**：快取的寫入者（`add_user`/`remove_user`）與讀取者同模組，invalidate 不需 `admin.py` 反向 import `auth`，
   也避免循環相依（`auth` → `allowed_users` 單向）。命名/TTL 模式仿 `_JWKS_CACHE`/`_JWKS_TTL_SECONDS`。
3. **fail closed 且不回傳過期快取**：spec 為「無未過期快取」才 fail closed，故過期後查表失敗一律 403（管理者除外）；不做 stale-while-error，
   符合 CONSTITUTION 安全預設（拒絕為預設）。失敗以 `logger.exception` 記錄；`auth` 層用 `except Exception`（BLE001）把外部依賴失敗轉為明確結果。
4. **invalidate 放在 `add_user`/`remove_user` 的 `finally`，一律失效（含 `created=False`、404/`False`、甚至例外）**：
   這兩條不是無害路徑——別的 container 可能已改過表，本 container 快取可能已過時；例外時寫入結果不確定。失效成本僅多一次查表，
   正確性優先；且 admin.py 零修改，不可能漏呼叫。**跨 container 一致性**：Lambda 多個 container 各有獨立記憶體，
   其他 container 不會被通知，最多 `CACHE_TTL_SECONDS`（60 秒）後才看到新增/移除——此限制須寫進 `allowed_users.py` 快取區塊的註解（developer 必加）。
5. **同步 boto3 呼叫留在 `async def` 內，不用 threadpool**：`verify_token` 本就是同步（`requests.get` JWKS 也同步）、`usage.py`/`db.py` 等既有 handler 慣例亦同；
   快取命中時為純記憶體，未命中每 60 秒一次單頁 Scan（小表，毫秒級）。改 threadpool 需改 `verify_token` 簽章並破壞既有測試，得不償失。
   已知取捨：DynamoDB 故障時 boto 逾時重試會拖慢請求，上限受 Lambda timeout（30s）約束，接受。
6. **thread-safety 用 `threading.Lock` + generation 計數**：Lambda 單 container 通常序列處理，但本機 uvicorn/threadpool 同步 handler 可能併發；
   鎖範圍極小、I/O 在鎖外，generation 防 invalidate 競態（見快取結構）。
7. **`touch_last_login` 用條件更新 `attribute_exists(email)`**：`update_item` 預設 upsert，沒有條件會替不在表中的管理者建立只含 `last_login` 的幽靈列
   （等於偷偷把管理者加入白名單）。條件失敗以回傳 `False` 表達「不在表中」，不當錯誤。
8. **失敗隔離在 `get_me`（呼叫端）而非 `touch_last_login` 內**：函式只吞「不在表中」這個預期結果；真正的 DynamoDB 錯誤往上拋，
   由 `/api/me` 處 `except Exception` 記 log 並仍回 200（AC 明定）。理由：函式本身語意清楚、可單獨測例外；與 66 `allowed_users` 的「不吞非條件錯誤」慣例一致。
9. **email 比對一律小寫**：token email `lower()` 與表中小寫 key 比對；`touch_last_login` 內用 66 的 `normalize_email`。
   （`CurrentUser.email` 維持 token 原樣大小寫，回應格式不變。）
10. **行為變更需明載**：舊邏輯「空 ALLOWED_EMAILS = 全放行」「管理者不在清單內仍被拒」兩者都消失；新邏輯「空表 = 一般使用者全拒、管理者永遠過」。屬 spec 明定，非設計新增。
11. **`ensure_allowed_users_table_exists()` 於 `get_all_emails`/`touch_last_login` 內呼叫**：與 66/既有模組慣例一致（Lambda 上因無 ListTables 權限會被 AccessDenied 略過）。
    **不在 `verify_token` 熱路徑額外加呼叫**：快取命中時完全不碰 AWS。

## 測試遷移計畫（已逐檔讀取；所有受影響測試皆在下列清單，其餘 `src/tests/` 檔案不受影響）
**原則**：不再以 `config.ALLOWED_EMAILS` 控制，改在 moto 表中「種資料」；快取跨測試殘留，故 conftest 要重置。

1. `src/tests/conftest.py`（修改）：`_mock_dynamodb` fixture 改為 yield 前後各呼叫一次 `allowed_users.invalidate_cache()`
   （模組級快取不隨 `mock_aws` 重置；不重置會讓前一個測試的快取污染下一個）。`_override_auth` 不動（多數測試因此不經 DB 檢查）。
2. `src/tests/test_infra_allowed_emails.py`（**整檔刪除**）：其 5 個 infra 靜態測試都在斷言 `ALLOWED_EMAILS`/`allowed_emails`/`TF_VAR_allowed_emails`
   存在，與本 Story 直接衝突；另 2 個測試斷言 `test_auth.py` 內含已被改寫的 403 測試函式與 `monkeypatch.setattr(config, "ALLOWED_EMAILS"`，同樣失效。
   以新檔取代：`src/tests/test_allowed_emails_removed.py`（新增，靜態文字掃描，風格同被刪檔，需 `pyyaml` 已在 requirements）：
   斷言 `src/config.py`、`src/auth.py`、`infra/*.tf`、`infra/terraform.tfvars.example`、`.github/workflows/ci.yml` 皆不含 `ALLOWED_EMAILS` / `allowed_emails`（大小寫不敏感）；
   且 `ci.yml` terraform apply step 的 env 不含 `TF_VAR_allowed_emails`；`config` 模組無 `ALLOWED_EMAILS` 屬性；`auth` 模組無 `_get_allowed_emails`。
   （`docs/` 下歷史設計文件不掃描。）
3. `src/tests/test_auth.py`（修改）：
   - `test_verify_token_success_regular_user`（user@example.com 為一般使用者）與 `test_verify_token_with_at_hash_claim_accepted`：
     登入前以 `allowed_users.add_user("user@example.com")` 種入表中（否則空表 → 403）。
   - `test_verify_token_admin_whitelist`、`test_verify_token_expired_rejected`、`test_verify_token_unknown_kid_rejected`、`test_get_current_user_missing_header_401`：不需改（admin 短路、或在檢查前失敗）。
   - 「ALLOWED_EMAILS 白名單」區塊 7 個測試改寫為「allowed-users 表」版本（移除所有 `monkeypatch.setattr(config, "ALLOWED_EMAILS", ...)`）：
     `…in_allowlist_passes`（種表 a@，a@ 通過）、`…not_in_allowlist_raises`（表中只有 a@，c@ → `EmailNotAllowedError`）、
     `…empty_allowlist_backward_compatible` **改為** `…empty_table_rejects_regular_user`（空表 → `EmailNotAllowedError`）、
     `…admin_not_in_allowlist_still_rejected` **改為** `…admin_not_in_table_still_allowed`（ADMIN_EMAILS 含 admin@、表為空/只有他人 → 通過、role=admin、**表內無 admin@ 列**）、
     `test_get_current_user_email_in_allowlist_returns_200`（種表，經 `/api/me` 200）、
     `test_get_current_user_email_not_in_allowlist_returns_403`（403 且 detail `此帳號未被授權使用本系統`）。
   - 保留 `_JWKS_CACHE` monkeypatch 寫法與 `app.dependency_overrides.pop(get_current_user, None)`。
4. 新增測試（可放 `test_auth.py` 與新檔 `src/tests/test_allowed_users_login.py`）涵蓋 AC：
   - 快取：第二次登入不再查表（monkeypatch `list_users`/`_table` 計數，或表內刪除後 60 秒內仍通過）；以 monkeypatch `allowed_users.time.time` 前進超過 `CACHE_TTL_SECONDS` 後重新查表；`CACHE_TTL_SECONDS == 60`。
   - 失效：`add_user`/`remove_user`（含 `created=False`、不存在）後立即反映；經 admin HTTP API（POST/DELETE，`role="admin"` 覆寫 `get_current_user`）後同 container 立即生效。
   - fail closed：monkeypatch `allowed_users._table`（或 `list_users`）拋 `ClientError`、快取已清 → 一般使用者 403、管理者仍通過；快取未過期時查表壞掉仍通過。
   - `touch_last_login`：表中 email 寫入符合 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`；不在表中回 `False` 且 `scan()` 項目數不變（不建立列）；大小寫不同的 email 仍更新同一列。
   - `/api/me`：已在表中的使用者呼叫後 `last_login` 有值；管理者不在表中呼叫後表中無其列；monkeypatch `touch_last_login` 拋例外 → 仍 200 且有 error log（`caplog`）；
     其他端點（如 `/api/health`、`/api/admin/allowed-users` GET）呼叫後 `last_login` 不變。
   - 登入走 `verify_token` 的新測試需要與 `test_auth.py` 相同的 `rsa_key` 風格 fixture（可從 `test_auth.py` import 或複製 `_make_token`）。
5. 驗證命令（取自 `project-profile.yaml`）：`pip install -r src/requirements.txt` 後 `pytest src/tests -q`；另跑 e2e `CI=1 npx playwright test --workers=1`（專案無 `npm run test` script，僅有 `e2e`；不因本 Story 只動後端而略過）。

## UI 原型
無，本 Story 不涉及前端 UI（僅後端登入判定、`/api/me` 副作用與 infra/CI 設定移除；白名單管理畫面屬 SDLCAIP2-64，不在本 Story 範圍）。

## 開放設計問題（定稿時必須為空）
無。
