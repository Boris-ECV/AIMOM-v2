# 設計文件 — SDLCAIP2-23 登入白名單（ALLOWED_EMAILS）

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-23）。新增環境變數 `ALLOWED_EMAILS`（逗號分隔
email 白名單），在 `verify_token()` 通過 JWT 驗證、取得 email 之後、回傳
`CurrentUser` 之前，多一道白名單檢查：不在白名單內回 403；`ALLOWED_EMAILS`
未設定或為空字串時維持向下相容（不限制）；管理者身分不自動繞過白名單檢查
（見 Gherkin 情境四）。範圍外：IdP 層控管、白名單管理 UI、告警機制。

## 介面/API 契約
不新增端點。變更既有驗證流程對外可觀察的行為：

- 所有掛在 `Depends(get_current_user)`（含 `require_admin`，因其本身依賴
  `get_current_user`）之下的既有路由，回應狀態碼新增一種可能結果：

  | 情境 | 狀態碼 | body |
  |---|---|---|
  | token 無效/過期/簽章錯誤（既有行為，不變） | 401 | `{"detail": "未授權，請重新登入"}` |
  | token 有效，email 不在 `ALLOWED_EMAILS` 白名單內（且白名單非空） | **403**（新） | `{"detail": "此帳號未被授權使用本系統"}` |
  | token 有效，email 在白名單內，或 `ALLOWED_EMAILS` 為空/未設定 | 200（依路由本身邏輯） | 不變 |

  403 訊息文字採 spec 用語「此帳號未被授權使用本系統」，與既有 `require_admin`
  的 403 訊息（「僅限管理者存取」）語意區分——一個是「未授權使用本系統」、
  一個是「權限不足看到管理者功能」，避免前端/使用者混淆兩種 403 的成因。

## 資料模型
無新增資料模型。`ALLOWED_EMAILS` 是環境變數，比照 `ADMIN_EMAILS` 的既有形狀
（逗號分隔字串，非資料庫欄位），符合 CONSTITUTION.md 安全預設段落「新增權限
判斷應延續白名單環境變數這個既有形狀」。

## 關鍵技術決策

1. **`verify_token()` 用一個新的例外類別區分「白名單拒絕」與「token 無效」，
   不重用既有 `ValueError`。**
   新增 `class EmailNotAllowedError(Exception)`（定義於 `src/auth.py`，
   `CurrentUser` 附近）。白名單檢查失敗時 `raise EmailNotAllowedError(email)`，
   而非 `ValueError`。理由：`get_current_user()` 目前用
   `except ValueError` 把所有驗證失敗一律轉成 401；若白名單檢查也 raise
   `ValueError`，`get_current_user()` 無法區分「token 本身無效」（規格要求
   401，既有行為不可變）與「token 有效但不在白名單」（規格明確要求 403）。
   用獨立例外類別讓 `get_current_user()` 可以分別 `except` 並轉成對應狀態碼，
   不需要用字串比對錯誤訊息去猜測失敗原因（脆弱、且違反 CONSTITUTION.md
   「不可讓例外無聲穿透／應轉成帶清楚訊息的 HTTPException」的既有慣例精神）。

2. **白名單檢查放在 `verify_token()` 內、email 解析之後、`return
   CurrentUser(...)` 之前**（緊接在既有 `role = "admin" if ... else "user"`
   那行之後），而不是放在 `get_current_user()` 或另開一個 dependency。
   理由：`verify_token()` 是唯一被單元測試直接呼叫、也是唯一定義「什麼樣的
   token 算通過驗證」的函式（見既有 docstring「任何失敗都拋出
   ValueError」，這裡延伸為「token 相關失敗拋 ValueError，白名單失敗拋
   EmailNotAllowedError」）；把白名單邏輯留在同一函式內，維持
   `verify_token()` 作為單一驗證入口的既有設計，`get_current_user()` 只負責
   例外→HTTP 狀態碼的轉換，不重複判斷邏輯。

3. **白名單解析函式 `_get_allowed_emails()` 完全比照既有 `_get_admin_emails()`
   的寫法**（`config.ALLOWED_EMAILS or ""`，逗號分隔，`strip().lower()`，
   組成 `set[str]`），大小寫不敏感比對方式與 `_get_admin_emails()` / 既有
   `role` 判定一致。理由：同一個 email 比對語意（大小寫、去空白）在同一個
   函式裡出現兩次不同標準會是隱藏 bug 來源；沿用既有函式的既定形狀。

4. **空白名單（未設定或空字串）視為「不限制」，判斷式為
   `if allowed_emails and email.lower() not in allowed_emails`。**
   `allowed_emails` 集合為空時整個 `if` 短路為 False，不做任何檢查——對應
   Gherkin 情境三的向下相容要求（已由人類在 spec 中定案，不再列為 open
   question，依 CONSTITUTION.md 範圍紀律「需求不明確時列 open question」
   原則，這裡並非不明確，故不列)。

5. **管理者不自動繞過白名單**（Gherkin 情境四）：因為白名單檢查與角色判定
   是獨立的兩行程式碼（角色判定用 `_get_admin_emails()`，白名單檢查用
   `_get_allowed_emails()`），兩者互不影響，天然滿足「admin 也要過白名單」
   ——不需要額外程式碼特別處理這個情境，只需確保實作順序是「先做白名單檢查
   （不通過就 raise，函式提前結束）→ 再做角色判定 → 回傳
   `CurrentUser`」，讓被拒絕的 admin email 連 `CurrentUser` 都不會被建立。

6. **`config.py` 新增 `ALLOWED_EMAILS = os.getenv("ALLOWED_EMAILS", "")`**，
   緊接在既有 `ADMIN_EMAILS` 那行之後，寫法逐字比照，符合 CONSTITUTION.md
   「設定值一律集中在 config.py」的既有慣例。

### 新增/變更程式碼摘要（供 developer 對照，非強制逐字照抄）

`src/auth.py`：
```python
class EmailNotAllowedError(Exception):
    """token 驗證通過，但 email 不在 ALLOWED_EMAILS 白名單內。"""


def _get_allowed_emails() -> set[str]:
    raw = config.ALLOWED_EMAILS or ""
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def verify_token(...) -> CurrentUser:
    ...
    email = payload.get("email")
    if not email:
        raise ValueError("token 缺少 email claim")

    allowed_emails = _get_allowed_emails()
    if allowed_emails and email.lower() not in allowed_emails:
        raise EmailNotAllowedError(email)

    role = "admin" if email.lower() in _get_admin_emails() else "user"
    return CurrentUser(email=email, role=role)


async def get_current_user(...) -> CurrentUser:
    ...
    try:
        return verify_token(token)
    except EmailNotAllowedError as exc:
        raise HTTPException(status_code=403, detail="此帳號未被授權使用本系統") from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="未授權，請重新登入") from exc
```

`src/config.py`（緊接 `ADMIN_EMAILS` 那行之後）：
```python
ALLOWED_EMAILS = os.getenv("ALLOWED_EMAILS", "")  # 逗號分隔白名單，登入門檻（非空時強制）
```

## 開放設計問題（定稿時必須為空）
無。
