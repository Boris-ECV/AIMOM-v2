# 設計文件 — SDLCAIP2-40 會議紀錄結果頁操作區塊應回復至 SDLCAIP2-39 合併前的呈現方式

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-40）：`#view-result` 操作區塊（模板／重
新產生／匯出格式／匯出／清除暫存／新錄音）的排版與按鈕圖示，因
SDLCAIP2-39（PR #244，squash-merge commit `9b9d4e4`）被意外改動，需回復到
SDLCAIP2-39 合併前（SDLCAIP2-37 完成後）的樣式。**實作方式已由人類裁決並
鎖定：必須對 `9b9d4e4` 執行 `git revert`，不得基於目前程式碼手動改寫**（前
一版把實作方式留給 developer 自行判斷的規格草稿，已因這個模糊性被 G1 駁回
一次）。六條 Gherkin AC（AC1-AC6）：AC1-AC3 三個 `.btn-row` 容器移除
`flex-wrap:nowrap`／`overflow-x:auto` inline style，回退為共用 `.btn-row`
class 的 `flex-wrap:wrap`；AC4 三顆按鈕文字回復 emoji 前綴；AC5（回歸）
id／class／onclick／元素順序不變，三個 JS 函式不受影響；AC6
`tests/e2e/action-bar-nowrap.spec.ts` 隨 revert 一併刪除，`pytest -q` +
`npx playwright test` 在 CI 上維持全綠。範圍外：`src/export.py`、字型檔
（SDLCAIP2-38，無關檔案）、`9b9d4e4` 以外的任何 commit/檔案歷史、任何基於
現況的手動改寫、窄螢幕下 `flex-wrap:wrap` 導致的換行（這是 revert 的預期
結果，非缺陷）。

## 介面/API 契約
N/A — 純前端靜態頁面樣式/文字回復，不涉及 API 或資料模型變更。本 story
不新增、不修改任何對外 HTTP 端點；影響範圍限定在 `src/frontend/index.html`
既有 inline style 與按鈕文字內容的字元級回退，以及刪除一個 e2e 測試檔案。

## 資料模型
無新增資料模型。

## 架構作法：`git revert 9b9d4e4`

### 為什麼是 revert，而不是手動改寫
- 人類已在 ticket 中明確裁決並鎖定實作方式（見上方「對應需求規格」段），
  這是產品/流程層級的硬性限制，不是技術判斷空間；設計文件據此描述
  `git revert` 機制本身，不提出替代做法。
- `9b9d4e4` 是 squash-merge commit、**單一 parent**，`git revert 9b9d4e4`
  可直接套用，不需要 `-m` 指定 mainline parent（多 parent 的 merge commit
  才需要 `-m`）。
- 自 `9b9d4e4` 之後，没有任何後續 commit 觸碰過它影響的兩個檔案
  （`src/frontend/index.html`、`tests/e2e/action-bar-nowrap.spec.ts`），
  故 revert 預期**乾淨套用、無 conflict**。

### `9b9d4e4` 變更範圍與 revert 後的結果
`9b9d4e4`（PR #244）異動兩個檔案，`git revert` 會將兩者都還原：

1. **`src/frontend/index.html`**（12 行變更，第 ~298-317 行區域）：
   - 外層 `.btn-row` 容器（第 298 行）：revert 移除 inline style 中的
     `flex-wrap:nowrap;overflow-x:auto;`，該 style 回到 SDLCAIP2-37 完成後
     的 `align-items:center;justify-content:space-between;flex:1;`
     （AC1、AC2）。
   - `#result-action-group-content`（第 299 行）：revert 移除
     `flex-wrap:nowrap;`，回到 `align-items:center;`（AC1、AC3）。
   - `#result-action-group-reset`（第 316 行）：revert 移除
     `flex-wrap:nowrap;`，回到 `align-items:center;`（AC1、AC3）。
   - 三層容器移除 inline `flex-wrap:nowrap` 後，落回共用 `.btn-row` class
     （第 70 行 `display:flex;gap:10px;flex-wrap:wrap;`）本身的
     `flex-wrap:wrap`，此規則本身不動、也不受這次 revert 影響（AC1-AC3）。
   - `#regenerate-btn`／`#export-confirm-btn`／`#cleanup-btn` 文字：revert
     還原 emoji 前綴，分別回到 `🔄 重新產生`／`⬇ 匯出`／`🗑 清除暫存`
     （AC4）。`#new-recording-btn` 的 `+ 新錄音` 不在 `9b9d4e4` 變更範圍
     內，不受影響。
   - `class`、`id`、`onclick`、元素數量與順序：`9b9d4e4` 本就未觸碰這些屬
     性，revert 後自然維持不變（AC5）。
   - `<script>` 區塊：`9b9d4e4` 未變更任何 JS，revert 不涉及
     `regenerateSummary()`／`exportSelectedFormat()`／`cleanupAndReset()`
     的邏輯或呼叫參數（AC5）。

2. **`tests/e2e/action-bar-nowrap.spec.ts`**（178 行，`9b9d4e4` 新建此
   檔）：revert 會將此檔案**整個刪除**，因為它斷言的正是 SDLCAIP2-39 現在
   要被回退的 `nowrap`/`overflow-x` 行為，回退後這些斷言不再成立（AC6）。

### 驗證方式
- `pytest src/tests -q` 全綠（本 story 不觸碰任何後端程式碼，預期不受
  影響，但仍需實際執行確認 baseline 未退步）。
- `npx playwright test` 全綠：`action-bar-nowrap.spec.ts` 已隨 revert 移
  除，其餘既有 e2e 測試（含 SDLCAIP2-37 建立、驗證 `.btn-row` 分組/樣式
  的既有測試，若有）需保持通過，確認未因 revert 引入其他非預期變化。
- 目視或用既有 grep 確認第 298/299/316/305/314/317 行的 inline style 與
  按鈕文字，逐字符合上方「revert 後的結果」描述。

## 關鍵技術決策

1. **用 `git revert 9b9d4e4` 而非手動編輯 `index.html` 回到目標狀態，即
   使最終文字結果理論上相同。** 這是人類的硬性裁決（見對應需求規格段），
   非技術判斷；`git revert` 保證 diff 與 `9b9d4e4` 的異動範圍逐行對應，
   避免手動改寫時遺漏或誤改其他相鄰內容的風險，同時保留清楚的版本歷史
   （commit message 會明確記載「revert 9b9d4e4」），方便未來追溯。

2. **不額外處理 `9b9d4e4` 之後可能存在的其他 commit 對同一區塊的變
   動。** 已透過 `git log`／既有事實確認自 `9b9d4e4` 後無其他 commit 觸碰
   這兩個檔案，故 revert 預期無 conflict；若實作階段執行時發現有
   conflict（例如兩次驗證之間又有新 commit 落地），屬於實作時的環境變化，
   非本設計判斷範圍，developer 應停下確認而非自行合併解決衝突內容。

3. **窄螢幕下恢復 `flex-wrap:wrap` 導致的換行，視為 revert 的正確結果，
   不額外處理。** Ticket 範圍外明確排除「narrow-viewport 重新換行」，這是
   刻意接受 SDLCAIP2-39 之前就存在的既有行為，不是本 story 要修的缺陷。

## 開放設計問題（定稿時必須為空）
無。實作方式（`git revert 9b9d4e4`）已由人類在 ticket 中明確裁決並鎖定，
`9b9d4e4` 的異動範圍（兩個檔案、12 行 HTML 變更、一個新建測試檔）與
revert 後的目標狀態均可由既有 commit 內容逐字確認，六條 AC 沒有需要額外
產品決策的模糊地帶。
