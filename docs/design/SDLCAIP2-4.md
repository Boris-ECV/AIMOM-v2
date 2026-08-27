# 設計文件 — SDLCAIP2-4 建立 Node.js + Playwright e2e 測試骨架（本機後端 + moto mock）

## 對應需求規格
G1 已核准的需求規格（本 ticket 描述）：建立最小可行的 Node.js 工具鏈
（`package.json` 僅含 devDependencies）與 Playwright e2e 測試骨架
（`tests/e2e/`），提供至少 1 個示範性 smoke 測試，對「本機啟動的
FastAPI 後端（moto mock DynamoDB + dependency override 跳過真實
Cognito 登入）+ `src/frontend/` 靜態頁面」執行並通過（非 skip）。同時
更新 `project-profile.yaml` 的 `commands` 補上 e2e 指令。範圍外明確排除：
不補齊既有頁面完整 e2e 覆蓋、不修改 `src/frontend/` 既有功能/樣式、不引入
前端 build/bundler、不新增 CI e2e job（留給 SDLCAIP2-5）。

## 介面/API 契約
本 Story 不新增/變更任何後端 API。以下是「e2e 測試如何取得後端」的具體
機制（developer 據此實作，不需自己發明格式）：

### 後端啟動方式：新增 `src/tests/e2e_server.py`
一支獨立的 Python 啟動腳本（非 pytest 測試檔，檔名不含 `test_` 前綴，
pytest 預設不會收集它），在**同一個行程**內完成三件事後才呼叫
`uvicorn.run(...)`——因為 `app.dependency_overrides` 與 moto 的
`mock_aws()` context 都是行程/物件層級的狀態，透過 CLI 分開啟動
（`uvicorn app:app`）之後無法從外部注入：

```python
# src/tests/e2e_server.py
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # 與 conftest.py 相同手法

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")

from moto import mock_aws
import uvicorn

from app import app
from auth import CurrentUser, get_current_user


def _fake_current_user() -> CurrentUser:
    return CurrentUser(email="e2e-user@example.com", role="user")


if __name__ == "__main__":
    app.dependency_overrides[get_current_user] = _fake_current_user
    with mock_aws():
        uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
```

- 與 `conftest.py` 的差異只在於：這裡是「啟動一個常駐 server 行程」而非
  「pytest fixture 包住每個測試」，`with mock_aws():` 包住整個
  `uvicorn.run(...)`（阻塞呼叫，行程存活期間 = mock 存活期間），效果等價。
- `dependency_overrides` 在 `uvicorn.run(app, ...)` 之前設定、且直接傳入
  `app` 物件（不是 `"app:app"` 字串），確保 uvicorn 使用的就是這個已被
  覆寫過的同一個 app 實例，不會被 uvicorn 重新 import 一次而遺失覆寫。
  因此 `reload=False`（reload 模式會在子行程重新 import 模組，同樣會遺失
  覆寫與 mock context，不適用於 e2e 啟動腳本）。
- 啟動指令：`python src/tests/e2e_server.py`（於 repo 根目錄執行，沿用
  `project-profile.yaml` `commands.setup` 已建立的 Python 環境，不需要
  額外安裝套件）。

### 前端靜態檔案伺服方式
沿用 Python 內建 `http.server`，不引入 Node 靜態伺服套件（維持
CONSTITUTION「避免不必要的抽象層」/範圍外「不引入前端 build/bundler」）：

```
python -m http.server 4173 --directory src/frontend
```

### Playwright 如何等待兩者就緒並取得 URL
`playwright.config.ts` 使用 Playwright Test 內建的 `webServer`
陣列設定（v1.24+ 支援多個 server），各自帶 `url` 供 Playwright 輪詢直到
回應成功才開始跑測試，不需要額外的 wait-on 套件：

```ts
webServer: [
  {
    command: "python src/tests/e2e_server.py",
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  {
    command: "python -m http.server 4173 --directory src/frontend",
    url: "http://127.0.0.1:4173/index.html",
    reuseExistingServer: !process.env.CI,
    timeout: 15_000,
  },
],
use: {
  baseURL: "http://127.0.0.1:4173",
},
```

- `baseURL` 指向前端靜態伺服器；smoke 測試中對後端的呼叫改用
  `request.get('http://127.0.0.1:8000/api/health')` 明確給後端完整 URL
  （見 `tests/e2e/config.ts` 常數），不透過 `baseURL` 混用，避免兩個伺服器
  的 URL 混淆。
- `reuseExistingServer: !process.env.CI`：本機重複執行測試時若 8000/4173
  已有伺服器在跑（開發者手動啟動來偵錯），不重複啟動；CI 環境一定重新啟動
  乾淔的行程。

### smoke 測試內容（`tests/e2e/smoke.spec.ts`）
兩個測試案例：
1. 「首頁可載入（未登入畫面）」：`page.goto('/')`，斷言
   `page.title()` 為 `會議錄音轉紀錄系統`，且 `#auth-gate` 可見、
   內含文字 `請先登入才能使用`（對應 `index.html` 現況：未帶
   `id_token` 時顯示 auth-gate，不顯示 `#app-shell`）。**不**嘗試走完整
   Cognito 登入流程——spec 的 Scenario 2 只要求「前端首頁可載入」，未要求
   驗證登入後畫面，見下方「關鍵技術決策」第 4 點的推斷依據。
2. 「後端健康檢查端點回應成功」：透過 Playwright 的
   `request` fixture（APIRequestContext）呼叫
   `GET http://127.0.0.1:8000/api/health`，斷言狀態碼 `200`、body
   `{"status": "ok"}`（對應 `app.py` 現有 `/api/health` 定義，無需認證）。

## 資料模型
無新增資料模型。moto mock 的 DynamoDB table schema 完全沿用既有
`db.py` / `jobstore.py` / `usage.py` 各自的 `ensure_*_table_exists()`
函式（`KeySchema`/`AttributeDefinitions` 定義都已存在於程式碼中）。本
Story 的 smoke 測試只呼叫 `/api/health`，該端點不存取 DynamoDB，因此
**不會觸發任何 table 的建立**——`mock_aws()` context 在此純粹是滿足
spec Given 子句「以 moto mock_aws 模擬 DynamoDB」的執行環境設定，為未來
擴充（會呼叫到 DB 的 e2e 案例）預先鋪好同一套骨架，不代表本 Story 需要
主動建表或寫入假資料。

## 關鍵技術決策

1. **Node.js 版本選 20.x LTS。**
   理由：Playwright 官方測試矩陣支援 Node 18/20/22，20.x 是目前 Active
   LTS、GitHub Actions `ubuntu-latest` 預裝，且與 SDLCAIP2-5（CI 整合）
   要接的 runner 版本一致，避免屆時另外指定 Node 版本。

2. **`package.json` 放在 repo 根目錄，不放子目錄（如 `tests/e2e/`）。**
   理由：Playwright Test 慣例上以 `package.json` 所在目錄為專案根，
   `playwright.config.ts` 與 `tests/e2e/` 路徑都相對於它；spec 的
   Scenario 1 也寫「於 package.json 所在目錄執行 npm install」並隱含
   之後 `npx playwright test tests/e2e/smoke.spec.ts` 這種相對路徑可直接
   運作，代表 spec 預期 repo 根目錄即是 Node 工具鏈根目錄（與 Python
   `src/` 工具鏈並列，兩套工具鏈用不同設定檔區分，不是用目錄區分）。

3. **`playwright.config.ts` 用內建 `webServer`（陣列）而非另外寫
   shell script／npm pre-test hook 來啟動後端+前端。**
   理由：Playwright 內建機制自帶「輪詢 URL 直到就緒才開始測試」與
   「測試結束後自動關閉子行程」，比自建腳本更不容易遺漏 teardown；陣列
   形式（v1.24+）可同時管理後端 8000 + 前端 4173 兩個獨立行程。

4. **新增 `src/tests/e2e_server.py`（而非直接用
   `uvicorn app:app --port 8000` CLI 指令）啟動 e2e 用後端。**
   理由：見上方「介面/API 契約」──`dependency_overrides` 與
   `mock_aws()` 都是 Python 物件/行程層級狀態，必須在同一行程內、
   `uvicorn.run()` 呼叫前設定好，CLI 字串型態的 `uvicorn app:app`
   啟動方式做不到「從外部注入 auth 覆寫」，因此需要一支小型 Python
   啟動腳本；放在 `src/tests/` 而非新建 `scripts/` 底下的理由是它需要
   `conftest.py` 已經在用的同一招 `sys.path.insert` 技巧才能 import
   `app`/`auth`，放在同目錄最省事、也讓未來讀者容易類比理解兩者關係。

5. **前端首頁 smoke 斷言的是「未登入畫面」（`#auth-gate`），不是走完整
   Cognito Hosted UI 登入流程後的 `#app-shell`。**
   理由（推斷依據，非我自行決定產品需求）：spec Scenario 2 的 Then
   只寫「驗證前端首頁可載入」與「對後端既有端點取得成功回應」，並未提及
   登入；範圍外也明確排除「修改 `src/frontend/` 既有功能」與新技術方案
   （若要測試登入後畫面，需要模擬/繞過 Cognito Hosted UI 的重新導向，
   這是明顯超出「Node.js + Playwright 骨架」範圍的額外技術方案，spec
   沒有要求）。因此依現狀 `index.html`：未帶 `id_token` 時預設顯示
   `#auth-gate`，這正是「首頁可載入」在沒有任何登入動作下的天然可觀察
   結果，直接斷言這個畫面即可滿足 Scenario 2，不需要也不應該新增登入
   模擬機制。

6. **`package.json` 加入 `"postinstall": "playwright install --with-deps
   chromium"` script，只安裝 Chromium（不裝 Firefox/WebKit）。**
   理由：Scenario 1 要求「`npm install` 後不需額外手動設定即可執行」，
   而 `@playwright/test` 套件本身不會在 `npm install` 時自動下載瀏覽器
   執行檔，需要 `playwright install` 這一步；用 `postinstall` hook 讓它
   隨 `npm install` 自動觸發，滿足「不需額外手動設定」。只裝 Chromium
   （而非三個瀏覽器）是因為本 Story 只要求 1 個示範性 smoke 測試，尚無
   跨瀏覽器需求，符合 CONSTITUTION 範圍紀律（不預先設計未要求的能力）；
   未來若有 Story 明確要求跨瀏覽器測試，再擴充這個 script。

7. **`.gitignore` 新增 `playwright-report/`（`node_modules/` 與
   `test-results/` 已存在於既有 `.gitignore`，無需再加）。**
   理由：Playwright 預設在測試失敗時於 repo 根目錄產生
   `playwright-report/` HTML 報表，屬於本機產物，延續既有
   `.gitignore` 對其他測試產物（`.pytest_cache/`、`htmlcov/`）的排除
   慣例。

## 開放設計問題（定稿時必須為空）
無。設計中唯一需要對 spec 做推斷的地方（決策 5：smoke 測試斷言未登入
畫面而非登入後畫面）已在「關鍵技術決策」中列出推斷依據；該推斷是從
spec 的 Given/Then 字面內容與範圍外條款直接導出，不涉及 spec 未言明的
新產品行為決定，故不列為開放問題。
