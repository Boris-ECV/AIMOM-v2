# CONSTITUTION — AIMOM

<!--
Durable engineering principles for this project. Read by
requirements-analyst / architect / reviewer (see their agent docs'
step "0."). Purpose: narrow judgment calls that would otherwise be
re-decided from scratch on every story, so similar situations get
similar answers across the codebase. This does NOT remove the
disclosure requirement — a judgment call guided by a principle here
must still be stated explicitly in the spec/design/review output, not
silently applied.

Keep this short and stable. Add a principle only after it has come up
as a real judgment call more than once; don't pre-populate hypothetical
rules.

本文件於 Phase B 從既有程式碼（brownfield，非本框架新寫）觀察歸納而成，
反映「這個 repo 已經在用的做法」，不是憑空發明的新規範。詳見
docs/04-project-instantiation.md 既有專案補充章節第 2 點。
-->

## 失敗處理哲學（Failure handling）

- `app.py` 有全域 `@app.exception_handler(Exception)`，未預期例外一律經它
  轉成統一格式的 500 JSON 回應（`{"detail": "伺服器內部錯誤：..."}`），並用
  `logger.exception(...)` 記錄完整 traceback。新加的路由不需要也不應該自己
  重複這層兜底，除非要回傳更精確的錯誤碼。
- 對外部依賴（S3、DynamoDB、Cognito JWKS、LLM/ASR 供應商）的呼叫，慣例是
  用 `try/except Exception as e` 包住，轉成帶有清楚中文訊息的
  `HTTPException`（例如 `upload.py` 的 404/500 轉換），不可讓例外無聲穿透。
- 既有程式碼裡這類 `except Exception` 屬於既有慣例（ruff 會標記
  `BLE001`），延續既有慣例優先於為了消除警告而改變錯誤處理形狀；若要收斂
  異常類型，應是獨立的技術債故事，而非隨手在功能 PR 裡順便改掉。

## 安全預設（Security defaults）

- `app.py` 用 `dependencies=[Depends(get_current_user)]` 掛在每個
  `include_router(...)` 上，預設整個 API 需要登入才能存取；只有
  `/api/health`（探測用）跟 `/api/admin` 的路由分組例外處理。新增路由預設
  應該掛進需要驗證的分組，除非明確理由需要公開。
- 身分驗證固定走 Amazon Cognito JWT（見 `auth.py`），角色（`user`/`admin`）
  由 `ADMIN_EMAILS` 環境變數白名單決定，不是存在資料庫的欄位；新增權限判斷
  應延續「白名單環境變數」這個既有形狀，不要另外發明一套角色儲存機制。
- 機密一律透過環境變數注入（`config.py` 集中讀取，`_env()`/`os.getenv()`），
  不寫死在程式碼；`.env`、`infra/terraform.tfvars`、`infra/backend.hcl`
  均已列在 `.gitignore`，不可移除這些排除規則。

## 測試哲學（Testing philosophy）

- 測試一律用 `pytest`，透過 `src/tests/conftest.py` 的 autouse fixture
  跳過真實登入（`app.dependency_overrides[get_current_user]`）與模擬
  DynamoDB（`moto.mock_aws`），不需要真實 AWS 帳號即可全部本地執行。新測試
  延續這個模式，不要為了「更真實」而繞過 fixture 直接打真正的 AWS 服務。
- 目前 baseline：`src/tests/` 12 個檔案、60 個測試案例全數通過，覆蓋率
  92%（2026-08-27 驗證，CI 門檻設 85% 留緩衝，見 `project-profile.yaml`
  `quality.coverage_threshold`）。新故事不可讓這個 baseline 退步。
- lint（ruff）目前為既有技術債、CI report-only 不阻擋合併（見
  `project-profile.yaml` `quality.lint_zero_tolerance` 與其 notes）；這不
  代表新程式碼可以無視 lint，新增/修改的程式碼仍應盡量乾淨，只是既有 88
  個歷史錯誤不會阻擋當前 Story 合併。

## 範圍紀律（Scope discipline）

- 只實作 spec 明確要求的範圍；看得到未來會需要、但目前故事沒要求的功能，
  一律不做，留給未來的故事。
- 需求不明確時，列為 open question 交由人類決策，不可用「合理猜測」補上，
  即使猜測看起來顯而易見。
- 舊功能（TASK-002 ~ TASK-016 時期開發）沒有 `docs/design/<KEY>.md`
  設計文件可查，相關背景只能讀 `docs/archive/` 的歷史交付紀錄或直接讀原始
  碼；不可因為「找不到設計文件」就誤判為「無先例」而自行重新設計，見
  `project-profile.yaml` 的 `conventions.notes`。

## 程式碼風格（Code style）

- 模組化路由：每個功能一個檔案 + 一個 `APIRouter`（`upload.py`、
  `transcribe.py`、`summarize.py` 等），在 `app.py` 用
  `include_router()` 掛載，不把多個功能塞進同一個路由檔。
- 註解/docstring 一律用**繁體中文**說明「為什麼」（例如 CORS 中介層順序的
  取捨、TASK-XXX 的歷史脈絡），識別字（函式名/變數名）用英文；新程式碼延續
  這個中英混用慣例，不要整段改成純英文或純中文。
- 設定值一律集中在 `config.py`，用 `os.getenv()`/`_env()` 讀取並給預設值，
  不在其他模組內散落直接呼叫 `os.getenv`。
- 遵循既有程式庫中已建立的慣例（命名、錯誤處理形狀、目錄結構），優先於
  個人偏好；新模式只在既有慣例明顯不適用時才引入，並在 PR 中說明原因。
- 避免不必要的抽象層：三段類似的程式碼優於一個只為了「將來可能會用到」而
  設計的通用抽象。

## 視覺設計（Visual design）

- 前端目前是純靜態 HTML/JS（`src/frontend/index.html` + `config.js`），
  沒有 build 流程、沒有 npm/package.json，也沒有 `docs/design-system.md`
  這類正式設計系統文件。新故事若涉及畫面改動，先讀現有 `index.html` 抓既有
  排版/樣式慣例延續，不要引入新的前端框架或 build 工具鏈，除非有獨立故事
  明確要做這個技術決策。
- `config.js` 是唯一隨環境（dev/staging/prod）變動的檔案（API base
  URL、Cognito 設定等），修改環境設定只動這個檔案，不要把環境相關值散落到
  `index.html`。

