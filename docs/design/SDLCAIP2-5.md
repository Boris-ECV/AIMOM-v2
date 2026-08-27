# 設計文件 — SDLCAIP2-5 CI 整合：新增獨立的 e2e job 到 GitHub Actions

## 對應需求規格
G1 已核准的需求規格（本 ticket 描述）：在 `.github/workflows/ci.yml`
新增一個獨立命名、不阻擋既有 `quality`（pytest/ruff）job 的 `e2e` job，
自動安裝 Playwright browsers 並執行 SDLCAIP2-4 建立的
`tests/e2e/`；job 執行測試前需先啟動本機後端並確認就緒（輪詢
`/api/health`）。範圍外：不將 e2e job 設為 branch protection 的必要檢查、
不新增 SDLCAIP2-4 範圍外的新測試案例、不修改既有 quality job 的
pytest/ruff 指令與門檻。

依賴：`docs/design/SDLCAIP2-4.md`（G1b 尚待人類核准，本文件假設其目前
版本定案，見「開放設計問題」）——沿用其 Node.js 20.x、repo 根目錄
`package.json`、`playwright.config.ts` 的 `webServer` 陣列（已內建
「啟動+輪詢就緒+執行後自動關閉」機制，見下方決策 2），CI job 不需要
另外手動 poll `/api/health` 或另寫等待腳本。

## 介面/API 契約
本 Story 不新增/變更任何後端 API。以下是 `.github/workflows/ci.yml`
新增的 `e2e` job 完整內容：

```yaml
  e2e:
    name: e2e (Playwright, non-blocking)
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Python dependencies (for local e2e_server.py)
        run: pip install -r src/requirements.txt

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - name: Install Node dependencies
        run: npm ci

      # npm ci 已透過 package.json 的 postinstall script
      # (`playwright install --with-deps chromium`，見 SDLCAIP2-4 設計文件
      # 決策 6) 自動安裝 Chromium + 系統相依套件，此處不需要重複的
      # `npx playwright install` 步驟。

      - name: Run Playwright e2e tests
        run: npx playwright test

      - name: Upload Playwright report on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7
```

完整 job 加入既有 `jobs:` 底下，與 `quality:` 平行（同一層級縮排），
兩者不宣告 `needs:`，因此 GitHub Actions 會平行執行、互不依賴，各自在
PR 頁面顯示獨立的檢查結果（對應驗收 Scenario 1、2）。`on:` 觸發條件
沿用既有頂層設定（`pull_request`/`push` to `main`），不需要為 e2e job
另開一組 workflow 檔案或 `on:` 區塊。

**「不阻擋 PR 合併」的落地方式**：程式碼層面（本 job 不對 `quality`
設 `needs:`、無 job 間依賴）已確保 e2e 失敗不會讓 `quality` 顯示紅色。
但「PR 合併按鈕是否被擋」最終取決於 GitHub repo 設定裡的 branch
protection required status checks 清單——這是 repo 設定，不是本 Story
程式碼能控制的範圍。**設計文件在此提醒：developer 完成本 Story 後，
需要在 PR 描述或 ticket 留言提醒人類確認 GitHub repo Settings →
Branches → branch protection rule，`e2e (Playwright, non-blocking)`
未被加入 required status checks（若既有規則是用 job id `e2e` 而非
`name:` 字串比對，需要確認用的是 `e2e` 這個 job id）**。

## 資料模型
無新增資料模型。

## 關鍵技術決策

1. **Job 名稱定為 `e2e`（job id），顯示名稱 `e2e (Playwright,
   non-blocking)`。**
   理由：GitHub Actions 頁面用 `name:` 欄位顯示於 UI，加上
   `(non-blocking)` 讓閱讀 PR 檢查列表的人立刻理解此 job 失敗不影響
   合併判定，不需要額外查閱文件；job id 維持簡短的 `e2e`，因為
   branch protection required status checks 清單是用 job id 比對，
   簡短 id 也方便未來若真的要調整 required checks 時查找。

2. **不額外寫 `curl`/`wait-on` 輪詢 `/api/health` 的 shell 步驟。**
   理由：SDLCAIP2-4 的 `playwright.config.ts` 已用 Playwright 內建
   `webServer` 陣列機制（`url` 欄位）在測試框架內部完成「啟動 →
   輪詢就緒 → 逾時失敗 → 測試結束自動關閉行程」的完整生命週期（見
   `docs/design/SDLCAIP2-4.md` 決策 3），`npx playwright test` 這一個
   指令本身即涵蓋驗收 Scenario 3 的全部要求；CI job 若額外重複一套
   輪詢邏輯，反而是重複實作同一件事、違反 CONSTITUTION「避免不必要的
   抽象層」。

3. **不設定 `concurrency:` group。**
   理由：spec 未要求限制同一 PR 重複觸發時的併發行為，既有 `quality`
   job 本身也沒有 `concurrency:` 設定；為維持與既有 job 一致的觸發語意
   （每次 push 都各自跑一份，不取消前一次），本 Story 不引入新設定，
   避免無 spec 依據地改變既有 CI 行為模式。若未來要優化 CI 資源消耗，
   應是獨立的技術債故事。

4. **`npm` 用 `actions/setup-node@v4` 內建 `cache: "npm"`；不額外對
   `pip install` 加 cache。**
   理由：`npm ci` 搭配 `setup-node` 的 cache 是官方建議的標準寫法，
   直接減少 `npm ci` 安裝時間，無額外設定成本。`pip install -r
   src/requirements.txt` 沿用既有 `quality` job 現況（該 job 目前也
   沒有 pip cache），保持兩個 job 的 Python 安裝步驟寫法一致、對稱，
   不在本 Story 順手引入既有 job 都還沒有的優化，避免範圍外改動。

5. **`timeout-minutes: 15`。**
   理由：`playwright.config.ts` 內兩個 `webServer` 各自的啟動 timeout
   是 30s + 15s（見 SDLCAIP2-4 設計文件），加上 `npm ci` 安裝、
   `pip install` 安裝與實際測試執行時間，15 分鐘留有餘裕又能在
   runner 卡住時及時失敗回報，不會無限期佔用 Actions runner 額度；
   既有 `quality` job 未設 timeout，本 Story 不動既有 job（範圍外）。

6. **失敗時上傳 `playwright-report/` 為 artifact（`if: failure()`）。**
   理由：spec 只要求「顯示獨立的檢查結果」，未要求除錯產物，但
   Playwright 測試在 CI 失敗時最有效的除錯資訊就是這份 HTML 報表
   （見 SDLCAIP2-4 設計文件決策 7，已將其加入 `.gitignore`）；上傳
   artifact 不影響 job 通過/失敗判定本身，屬於「讓失敗結果可觀察」的
   合理延伸，不算新增 spec 未要求的測試範圍。

7. **`pip install -r src/requirements.txt` 使用與既有 `quality` job
   完全相同的 Python 版本（3.12）與安裝指令，不引入 venv 快取或版本差異。**
   理由：`src/tests/e2e_server.py` import `app`/`auth` 時的相依套件與
   既有測試環境完全相同，維持兩個 job 的 Python 設定一致可避免「同一份
   程式碼在兩個 job 裡因版本不同而行為不同」這類難以排查的問題。

## 開放設計問題（定稿時必須為空）
無。本文件對 SDLCAIP2-4 尚待 G1b 人類核准這件事的處理方式：直接依其
目前版本（`docs/design/SDLCAIP2-4.md`，已完整定案且開放設計問題章節為
空）作為既定事實設計本 Story 的 CI job，理由——(a) SDLCAIP2-4 的開放
設計問題章節已清空，代表其架構師自評無待人類決定的產品問題，僅是
「等待人類走完 gate 簽核動作」而非「內容可能大改」；(b) 若 SDLCAIP2-4
在核准過程中仍有微調（例如指令字串、port 號），本 Story 的 CI job
只是呼叫 `npx playwright test` 這一個指令、不重複其內部細節，微調不會
波及本文件的技術決策，屆時 developer 只需確認指令仍為
`npx playwright test` 即可，不需要重新設計。因此不將此列為需要人類
先解決才能定稿的開放問題。
