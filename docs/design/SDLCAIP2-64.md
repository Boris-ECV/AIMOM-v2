# 設計文件 — SDLCAIP2-64 管理者儀表板新增使用者白名單管理 UI

## 對應需求規格
G1 定稿版（見工單 SDLCAIP2-64 描述；SDLCAIP2-63 的子 Story C，前端）。共 15 條 AC，決策皆已定稿：
AC1 清單顯示 email + last_login（本地時間，新增 ISO 格式化函式；既有 `fmtDateTime` 吃 epoch 秒，不可沿用）；AC2 `null`→「—」；AC3 空清單→「清單為空」；
AC4 新增 201 → 立即出現、清空輸入；AC5 重複（API 200）→ 資訊樣式提示「已存在」、不重複列；AC6 無效 email（422）→ 固定中文訊息、不印 pydantic detail 陣列、前端不做格式驗證；
AC7 空輸入 → 不送請求、「請輸入 email」；AC8 行內二段式移除（移除 → 確認移除／取消），DELETE 路徑用 `encodeURIComponent`；AC9 404 →「找不到此 email」並重載清單；
AC10 POST/DELETE 失敗（503/5xx/網路）→ 錯誤顯示在區塊**內**（非僅 toast）、清單不變、按鈕恢復；AC11 清單載入失敗 → 錯誤 +「重試」，既有用量彙總不受影響（請求相互獨立）；
AC12 XSS 安全（createElement/textContent/addEventListener，禁 onclick 字串拼接）；AC13 非管理者入口按鈕隱藏（既有 `checkAdminAccess`）、403 不顯示資料；AC14 進行中按鈕 disabled；AC15 管理者移除自己的 email 不做特別處理。

範圍外：後端（SDLCAIP2-66 已部署，本 Story 不改後端）、登入判定與 last_login 寫入（SDLCAIP2-67）、前端 email 格式驗證、批次匯入、分頁/搜尋。

### 現況（已讀取程式碼確認）
- `src/frontend/index.html`（單檔、行內 CSS/JS）：`#view-admin`（約 549 行）是**單一 `.card`**，內含 `.section-title`（含「← 返回」）、兩個 `<h4>` + `.ds-table-scroll > table.action-table`、`#admin-total`。
- `openAdminDashboard()`（約 980 行）：先 `apiFetch('/api/admin/usage')`，403 → toast「僅限管理者存取」並 return；成功才填表並 `showView('view-admin')`；失敗 toast。以 `innerHTML` 模板填用量表（既有程式，本 Story 不改其渲染方式）。
- `checkAdminAccess()`（約 967 行）呼叫 `/api/me`，`role==='admin'` 才顯示 `#admin-dashboard-btn`（AC13 入口隱藏已由此滿足，不需改）。
- `apiFetch`（約 914 行）自動帶 Bearer；401 → 清 token、`showAuthGate()` 並 throw `Error('登入已逾期，請重新登入')`。`toast()` 3 秒自動消失（不足以承載錯誤，故錯誤另放區塊內）。
- `esc()`（約 1842 行）**不跳脫單引號**，且 `test_speaker_rename_xss.py` 以文字斷言它的寫法 → 本 Story 不使用 `esc()`、也不修改它。
- `.input`（266 行）、`.btn/.btn-primary/.btn-outline/.btn-sm`（136–162 行）、`.empty-state`（515 行）皆為共用 class；手機版（<480px）`.btn { width:100%; height:44px }`、`.input { width:100% }`。
- 後端契約（`src/admin.py`，SDLCAIP2-66，已讀）：`GET /api/admin/allowed-users` → `[{email, last_login: "YYYY-MM-DDTHH:MM:SSZ"|null}]`（email 升冪）；
  `POST` body `{"email": str}` → 新增 **201** `{email, last_login:null}`、已存在 **200**（同形狀）、格式不符 **422**（`detail` 為陣列）；`DELETE /api/admin/allowed-users/{email}` → **204**／不存在 **404**；
  DB 錯誤 **503**（`detail`「白名單資料表暫時無法存取」）；非 admin **403**；無/壞 token **401**。
- `tests/e2e/view-admin-design-system.spec.ts`（SDLCAIP2-45）的斷言對象（逐條讀取）：
  1. `#view-admin .card` 的 `.first()`（背景/邊框/圓角）；
  2. `#view-admin .action-table th`/`td` 的 `.first()`（--ds-* 色、邊框色）；
  3. `#view-admin h4` **`toHaveCount(2)`**，`.first()` 14px/500/secondary/20px；`#view-admin .section-title` 的 `.first()` 字級 ≠ 14px；
  4. 窄螢幕 375px：`document.documentElement.scrollWidth <= clientWidth`；`#view-admin .ds-table-scroll` `.first()` overflow-x=auto；`#view-admin .action-table` `.first()` min-width=`560px`；
  5. `#view-admin` 的 `innerHTML` 不得含 `[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]` 的 emoji/符號字元（「—」U+2014、「←」U+2190 不在範圍內，OK）。
- **跨元素樣式耦合測試**（依程序 4 搜尋 `tests/e2e/`）：
  - 與 `#view-admin` 相關者：`view-admin-design-system.spec.ts`（上列）；`view-history-detail-design-system.spec.ts` 199–218 行、`view-result-cards-design-system.spec.ts` 105–126 行以 `#view-admin .section-title` `.first()` 斷言「不是 18px」；
    `view-upload-design-system.spec.ts` 38–60、198–235 行以 `#view-admin .card` `.first()` 與 view-upload `.card` 比對（相等性比對：admin `.card` ↔ upload `.card`）；
    `upload-button-reset.spec.ts` 72–94 行點 `#view-admin button:has-text("← 返回")`；`design-system-foundation.spec.ts` 164、271–277 行只看 `#admin-dashboard-btn`。
  - 涉及 `.input`/`.btn` 的鏈（SDLCAIP2-36/37/54 的 `#template-select` ↔ `#export-format-select` ↔ `.meeting-info-grid input` 相等性）：**本設計不修改任何既有 selector 的 computed style**
    （只新增以新 id/class 為範圍的規則，不動 `.input`、`.btn`、`.card`、`.action-table` 基底與 SDLCAIP2-45 的 scoped 規則），故不會打斷這些鏈。**無需人類決策。**

## 介面/API 契約
純前端變更（`src/frontend/index.html`）；呼叫既有後端 API，不新增/修改端點。

### DOM 結構（加在 `#view-admin` 內、既有 `.card` **之後**，為第二張 `.card`）
```html
<div class="card" id="allowed-users-card">
  <div class="section-title">使用者白名單</div>            <!-- 非 h4，避免破壞 45 的 h4 count=2 -->
  <form id="allowed-users-form" class="au-form" novalidate>
    <input id="allowed-users-input" class="input" type="text" autocomplete="off"
           placeholder="輸入 email 後新增" aria-label="新增白名單 email">   <!-- type=text：不啟用瀏覽器 email 驗證（AC6 無前端格式驗證） -->
    <button id="allowed-users-add-btn" class="btn btn-primary" type="submit">新增</button>
  </form>
  <p id="allowed-users-msg" class="au-msg" role="status" hidden></p>          <!-- 操作訊息；data-kind="error"|"info" -->
  <div id="allowed-users-status" class="au-status" role="status">             <!-- 清單區狀態：載入中／清單為空／載入失敗 -->
    <span id="allowed-users-status-text"></span>
    <button id="allowed-users-retry-btn" class="btn btn-outline btn-sm" type="button" hidden>重試</button>
  </div>
  <div class="ds-table-scroll" id="allowed-users-table-wrap" hidden>
    <table id="allowed-users-table" class="action-table">
      <thead><tr><th>Email</th><th>最近登入</th><th>操作</th></tr></thead>
      <tbody id="allowed-users-tbody"></tbody>
    </table>
  </div>
</div>
```
- 每列（以 `document.createElement` 建構）：`<tr data-email="<email>">`（`dataset.email = email`，非字串拼接）→ `td.au-email`（`textContent = email`）、`td`（`textContent = fmtIsoLocal(last_login)`）、
  `td.au-actions`：預設一顆 `button.btn.btn-outline.btn-sm`「移除」（`.au-remove`）；進入確認態改為兩顆：`button.btn.btn-primary.btn-sm`「確認移除」（`.au-confirm`）與 `button.btn.btn-outline.btn-sm`「取消」（`.au-cancel`）。
- 事件一律 `addEventListener`（form `submit` 以 `preventDefault()`）；**禁止** `onclick="..."`／`innerHTML` 拼接 email。

### 狀態（模組級單一物件，不放進 `state`）
```js
const allowedUsers = { items: [], loaded: false, pendingRemove: null, busy: false, loadSeq: 0 };
```
- `items`：目前顯示的 `{email,last_login}`；`pendingRemove`：處於「確認移除」態的 email（同時最多一列，點另一列的「移除」會取代前一個）；
  `busy`：任何 POST/DELETE/重載進行中；`loadSeq`：載入序號，慢回應的舊請求結果丟棄（防止重開儀表板時舊回應覆蓋新資料）。

### JS 函式清單（皆放在 `ADMIN DASHBOARD` 區段，`openAdminDashboard` 附近）
| 函式 | 責任 |
|---|---|
| `fmtIsoLocal(iso)` | `null/''` → `'—'`；`new Date(iso)` 為 Invalid Date → 回傳原字串；否則 `toLocaleString('zh-TW')`。**不重用** `fmtDateTime`（epoch 秒）。 |
| `loadAllowedUsers()` | `loadSeq++`；狀態區顯示「載入中…」；`apiFetch('/api/admin/allowed-users')`。200 → 寫入 `items`、`renderAllowedUsers()`；403 → 清空 `items`、狀態區顯示「僅限管理者存取」、**不渲染任何資料**；其他非 2xx／例外 → 狀態區顯示「讀取白名單失敗」+ 顯示「重試」鈕（`items` 不渲染）。內部 try/catch，**永不 throw**（不影響用量）。序號不符的回應直接丟棄。 |
| `renderAllowedUsers()` | 依 `items` 重建 `tbody`（`replaceChildren()` + createElement）；`items` 空 → 隱藏表格、狀態區顯示「清單為空」；非空 → 顯示表格、清空狀態區；依 `pendingRemove`/`busy` 決定每列按鈕樣貌與 `disabled`。 |
| `setAllowedUsersMsg(text, kind)` | `kind` ∈ `'error'|'info'|null`；null 或空字串 → `hidden`、清空；否則 `textContent = text`、`dataset.kind = kind`、移除 `hidden`。 |
| `setAllowedUsersBusy(flag)` | 設 `allowedUsers.busy`；`#allowed-users-add-btn`、`#allowed-users-input`、`#allowed-users-retry-btn`、`#allowed-users-tbody button` 全部 `disabled = flag`（AC14）。呼叫端一律在 `finally` 以 `false` 復原（AC10 按鈕恢復）。 |
| `addAllowedUser(ev)` | `preventDefault()`；`busy` 時直接 return；`v = input.value.trim()`，空 → `setAllowedUsersMsg('請輸入 email','error')` 並 return（**不送請求**，AC7）。否則清訊息、`setAllowedUsersBusy(true)`、`apiFetch('/api/admin/allowed-users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:v})})`：見下方對應表。 |
| `requestRemove(email)` | 設 `pendingRemove = email`、清訊息、`renderAllowedUsers()`（該列切為「確認移除／取消」）。 |
| `cancelRemove()` | `pendingRemove = null`、`renderAllowedUsers()`。 |
| `confirmRemove(email)` | `busy` 時 return；`setAllowedUsersBusy(true)`；`apiFetch('/api/admin/allowed-users/' + encodeURIComponent(email), {method:'DELETE'})`；見對應表。 |
| `openAdminDashboard()`（**微幅修改**） | 在既有 `apiFetch('/api/admin/usage')` **之前**先重置 `allowedUsers`（`items=[]`、`pendingRemove=null`、清訊息、清 input）並以 `loadAllowedUsers()` **不 await** 啟動（兩請求獨立並行，AC11）；其餘用量邏輯一字不改。 |
| `wireAllowedUsers()` | 在 `DOMContentLoaded` 內（`checkAdminAccess()` 附近）綁定 form `submit`、`#allowed-users-retry-btn` `click`；以 `addEventListener` 一次性綁定。 |

### 呼叫與結果對應（POST／DELETE／GET）
| 情境 | 判定 | 行為 |
|---|---|---|
| POST 201 | `res.status === 201` | `json = await res.json()`；`items.push({email: json.email, last_login: json.last_login})`，依 email 升冪（`a.email < b.email`，與後端 `sorted` 一致）；`renderAllowedUsers()`；`input.value = ''`；訊息清空（AC4） |
| POST 200 | `res.status === 200` | `setAllowedUsersMsg('已存在','info')`；`items` 不變、不新增列；輸入框內容保留（AC4 僅規範 201 清空；200 未規範，不擅自清空）（AC5） |
| POST 422 | `res.status === 422` | `setAllowedUsersMsg('email 格式不正確','error')`；**不讀取、不顯示 response body**（AC6） |
| POST 403 | `res.status === 403` | `setAllowedUsersMsg('僅限管理者存取','error')` |
| POST 其他非 2xx（503/5xx）／例外 | `!res.ok` 或 catch | `setAllowedUsersMsg('新增失敗，請稍後再試','error')`；`items` 不變（AC10） |
| DELETE 204 | `res.status === 204` | 自 `items` 移除、`pendingRemove=null`、`renderAllowedUsers()`、清訊息（AC8；AC15 無特殊處理） |
| DELETE 404 | `res.status === 404` | `pendingRemove=null`；`setAllowedUsersMsg('找不到此 email','error')`；`await loadAllowedUsers()` 重載清單（訊息位於獨立元素，重載不會清除它）（AC9） |
| DELETE 403 | | `setAllowedUsersMsg('僅限管理者存取','error')`、`pendingRemove=null` |
| DELETE 其他非 2xx／例外 | | `pendingRemove=null`；`setAllowedUsersMsg('移除失敗，請稍後再試','error')`；`items` 不變（AC10） |
| GET 非 2xx／例外 | | 見 `loadAllowedUsers`（AC11） |

401：`apiFetch` 已 `showAuthGate()` 並 throw；落入各 catch 而顯示通用失敗訊息，畫面已被登入閘門覆蓋，不另處理。

### CSS（新增，全部以新 id/class 為範圍；不改任何既有規則）
```css
/* ===== SDLCAIP2-64: 使用者白名單區塊（僅作用於 #allowed-users-card） ===== */
#allowed-users-card .au-form { display:flex; gap:var(--ds-space-2); margin-bottom:var(--ds-space-2); }
#allowed-users-card .au-form .input { flex:1; min-width:0; }
#allowed-users-card .au-msg { font-family:var(--ds-font-sans); font-size:13px; margin-bottom:var(--ds-space-2); }
#allowed-users-card .au-msg[data-kind="error"] { color:var(--danger); }               /* 與 #upload-error 一致 */
#allowed-users-card .au-msg[data-kind="info"]  { display:inline-block; padding:4px 12px; border-radius:var(--ds-radius-pill);
  background:var(--ds-badge-bg); border:1px solid var(--ds-badge-border); color:var(--ds-badge-text); }   /* 資訊樣式（非錯誤色） */
#allowed-users-card .au-status { font-family:var(--ds-font-sans); font-size:13px; color:var(--ds-text-secondary);
  padding:var(--ds-space-3) 0; display:flex; align-items:center; gap:var(--ds-space-2); flex-wrap:wrap; }
#allowed-users-card .au-status:empty { display:none; }
#view-admin #allowed-users-table { min-width:0; }                        /* id 選擇器 specificity 高於 45 的 `#view-admin .action-table{min-width:560px}`；僅覆寫新表 */
#allowed-users-card .au-email { overflow-wrap:anywhere; }
#allowed-users-card .au-actions { white-space:nowrap; }
#allowed-users-card .au-actions .btn { margin-right:var(--ds-space-1); }
@media (max-width: 479px) {
  #allowed-users-card .au-form { flex-direction:column; }
  #allowed-users-card .au-actions .btn, #allowed-users-card .au-status .btn { width:auto; }   /* 抵銷全域手機 .btn{width:100%}，僅限此區塊 */
}
```
`hidden` 屬性元素需確保不被上述 `display:flex/inline-block` 蓋掉：`#allowed-users-card [hidden]{display:none !important;}`（範圍限於此卡片）。

## 資料模型
無新增資料模型。不新增後端欄位/表；前端僅有記憶體內的 `allowedUsers` 狀態物件（見上），不寫入 `localStorage`/`sessionStorage`。

## 關鍵技術決策
1. **新區塊放第二張 `.card`，標題用 `.section-title`（不是 `<h4>`）**：45 的 e2e 斷言 `#view-admin h4` 恰為 2 個、且多處以 `.first()` 取 `.card`/`.section-title`/`.ds-table-scroll`/`.action-table`；新增物件全排在 DOM 之後且不是 h4，既有斷言全數維持成立。
2. **新表沿用 `.action-table`（重用 45 的 scoped th/td token）而非另寫樣式**：取得一致外觀，且不動 45 的規則；唯一覆寫是新表 `min-width:0`（兩欄加按鈕，不需 560px 強制橫向捲動）。45 的 min-width=560 斷言取 `.first()`＝用量表，不受影響。外層仍用 `.ds-table-scroll` 保留窄螢幕保護。
3. **`<input type="text">` 而非 `type="email"`**：spec AC6 明定前端不做格式驗證；`type=email` 會觸發瀏覽器原生驗證訊息而繞過固定中文訊息。以 `<form novalidate>` + submit 事件支援 Enter 送出。
4. **新增成功用本地插入＋排序，不重抓清單**：201 已回完整項目，少一次請求；排序規則與後端 `sorted()` 同（碼位比較）。其他情境（404）才重載以對齊伺服器。
5. **錯誤/資訊訊息放區塊內元素、不靠 `toast()`**：`toast` 3 秒消失且全域單例，AC10 要求錯誤持續可見；`#allowed-users-msg`（操作結果）與 `#allowed-users-status`（清單區狀態/重試）分開，使 404 後重載不會清掉「找不到此 email」。
6. **用 DOM API 建列，不用 `esc()` 也不用模板字串**：`esc()` 不跳脫單引號且有文字斷言測試鎖定寫法；email 由使用者輸入，`createElement + textContent + dataset` 從根本上排除注入（AC12）。`confirmRemove(email)` 以閉包持有 email，不把它序列化進 HTML/onclick。
7. **`openAdminDashboard()` 並行啟動 `loadAllowedUsers()` 且 try/catch 內吞**：兩請求互不等待，清單失敗不會讓用量頁整個不顯示；用量失敗/403 時既有行為不變（view 不顯示）。`loadSeq` 防止舊回應覆蓋。
8. **二段式確認用「列內按鈕切換」，同時只允許一列處於確認態**：無 modal、無 `confirm()`，最少 DOM；點另一列「移除」自動取代前一個確認態，避免畫面殘留多個待確認列。進行中（busy）所有按鈕 disabled（AC14）。
9. **DELETE 路徑 `encodeURIComponent(email)`**：`@` → `%40`，`+` 等字元安全；後端 FastAPI path 參數會解碼。
10. **AC15（管理者移除自己）不做任何特殊處理**：spec 已定稿；管理者靠 `ADMIN_EMAILS`（SDLCAIP2-67）永遠可登入，移除自己的列不影響其登入權。
11. **只有 403 之外的 4xx（422）以固定訊息處理，且完全不解析 body**：避免把 pydantic `detail` 陣列印到畫面（AC6）；503 的後端 detail 文字同樣不顯示，統一用固定中文訊息。

## UI 原型
`docs/design/SDLCAIP2-64-prototype.html`：靜態、可直接用瀏覽器開啟（行內 CSS/JS、無外部相依；沿用 `index.html` 的 `--ds-*` token 與 `.card/.btn/.input/.action-table` 規則；email 以 `textContent` 渲染）。
頁面上方按鈕可切換 6 種狀態：有資料清單（含 last_login 為「—」的列）、清單為空、載入失敗（錯誤＋重試）、新增錯誤（固定中文訊息）、重複新增（資訊提示「已存在」）、移除二段式確認（確認移除／取消）；
亦可在「有資料清單」狀態實際點「移除」體驗二段式切換。原型僅示意視覺與互動，不呼叫任何 API。

## 錯誤與邊界處理（AC → 機制）
| AC | 機制 |
|---|---|
| AC1 | `loadAllowedUsers` 取清單 → `renderAllowedUsers` 每列 email 欄 `textContent`、最近登入欄 `fmtIsoLocal(last_login)`（新函式，`toLocaleString('zh-TW')`） |
| AC2 | `fmtIsoLocal(null)` → `'—'` |
| AC3 | `items.length === 0` → 隱藏表格、`#allowed-users-status-text` 顯示「清單為空」 |
| AC4 | POST 201 → 本地插入＋排序＋`renderAllowedUsers()`；`input.value=''` |
| AC5 | POST `status===200` → `setAllowedUsersMsg('已存在','info')`（`data-kind=info` 樣式，非錯誤色）；`items` 不變 |
| AC6 | POST 422 → 固定「email 格式不正確」；不讀 body；前端無格式驗證（`type=text`、`novalidate`） |
| AC7 | `trim()===''` → 「請輸入 email」，直接 return，不呼叫 `apiFetch` |
| AC8 | 「移除」→ `requestRemove`（確認態）→「確認移除」→ `confirmRemove`（`DELETE` + `encodeURIComponent`）；「取消」→ `cancelRemove` |
| AC9 | DELETE 404 → 「找不到此 email」＋`loadAllowedUsers()` |
| AC10 | POST/DELETE 非預期狀態或例外 → 區塊內 `#allowed-users-msg`（error）；`items` 不動；`finally { setAllowedUsersBusy(false) }` 復原按鈕 |
| AC11 | `loadAllowedUsers` 失敗 → 狀態區「讀取白名單失敗」+「重試」（`click` → `loadAllowedUsers()`）；與 `/api/admin/usage` 為獨立請求，用量表照常 |
| AC12 | 全程 `createElement`/`textContent`/`dataset`/`addEventListener`；無 `onclick=` 字串、無 `innerHTML` 拼接（e2e 以含 `<img onerror>` 與單引號的 email 驗證不執行、以文字顯示） |
| AC13 | 入口按鈕沿用 `checkAdminAccess`（非 admin 隱藏，不改）；若仍直接觸發，`GET` 403 → 不渲染任何資料、狀態區顯示「僅限管理者存取」 |
| AC14 | `setAllowedUsersBusy(true)` 於請求期間禁用新增鈕/輸入框/重試鈕/所有列按鈕；`busy` 時 handler 亦 early return 防連點 |
| AC15 | `confirmRemove` 不比對目前登入 email，無特例 |

## 測試計畫
- **pytest**：不新增後端測試（無後端變更）。靜態檢查（新檔 `src/tests/test_allowed_users_ui.py`，風格同 `test_speaker_rename_xss.py`，讀 `index.html` 文字）：
  1. 含 `id="allowed-users-card"`、`id="allowed-users-input"`、`id="allowed-users-tbody"` 等關鍵 id；
  2. `encodeURIComponent` 出現在 `/api/admin/allowed-users/` 的 DELETE 呼叫附近；
  3. 白名單函式區段內（自 `function fmtIsoLocal` 至 `function wireAllowedUsers` 結尾）**不含** `onclick=`、`esc(`，且不含 `innerHTML`（用 `textContent`/`replaceChildren`）；
  4. `type="text"` 的 `allowed-users-input`（非 `type="email"`）；
  5. `esc()` 本體未改（既有 `test_speaker_rename_xss.py` 仍通過即可，不重複）。
- **e2e**（新檔 `tests/e2e/admin-allowed-users.spec.ts`；沿用 45 的 `loginBypass` 手法；`page.route('**/api/me', → {role:'admin'})`、`**/api/admin/usage`、
  `**/api/admin/allowed-users`（GET/POST 清單端點）與 **`**/api/admin/allowed-users/**`**（DELETE 單筆端點——注意 glob 的 `*` 不跨 `/`，兩個 pattern 都要註冊；`encodeURIComponent` 後路徑為 `/allowed-users/x%40y.com`）；入口以 `#admin-dashboard-btn` 點擊進入；執行 `CI=1 npx playwright test --workers=1`）：
  - AC1/AC2：清單 3 筆（含 `last_login:null`）→ 3 列；有值列顯示本地時間字串（非原 ISO「T…Z」）；null 列文字恰為「—」。
  - AC3：回 `[]` → 見「清單為空」、表格隱藏。
  - AC4：POST 回 201 → 新列立即出現且排序正確、`#allowed-users-input` 為空；斷言 request body `{"email": "..."}`。
  - AC5：POST 回 200 → 顯示「已存在」（`data-kind="info"`、顏色非 danger）、列數不變。
  - AC6：POST 回 422 + 陣列 detail → 顯示「email 格式不正確」，頁面文字不含 `loc`/`msg`/`value_error`。
  - AC7：空白輸入點新增 → 顯示「請輸入 email」，POST 路由計數 0。
  - AC8：點「移除」→ 該列出現「確認移除」「取消」；點取消還原；確認 → 斷言 DELETE URL 含 `%40`（編碼）、列消失；點另一列「移除」→ 前一列還原。
  - AC9：DELETE 404 → 顯示「找不到此 email」且 GET 被再呼叫一次（清單依新回應更新）。
  - AC10：POST 503／DELETE 500／`route.abort()` → 區塊內錯誤訊息可見、列數不變、按鈕 enabled。
  - AC11：GET 回 500 → 見錯誤＋「重試」；用量表（`#admin-by-date-tbody`）仍有資料；點重試（改回 200）→ 清單出現。
  - AC12：email 為 `"><img src=x onerror=window.__xss=1>` 與 `a'b@x.com` → 以文字顯示、`window.__xss` 為 undefined、`#allowed-users-tbody img` 數量 0；移除該列時 DELETE URL 正確編碼。
  - AC13：`/api/me` 回 `role:'user'` → `#admin-dashboard-btn` 不可見；另以 evaluate 直接呼叫 `openAdminDashboard()` 且 GET 回 403 → 表格無列、顯示「僅限管理者存取」。
  - AC14：POST 以延遲 route（`await new Promise(r=>setTimeout(r,300))`）→ 期間 `#allowed-users-add-btn` 與列按鈕 disabled，完成後恢復。
  - AC15：以 `/api/me` 的 email 為自己的列執行移除 → 與一般列行為相同（204 即移除、無額外對話）。
- 驗證命令（取自 `project-profile.yaml`）：`pip install -r src/requirements.txt` → `pytest src/tests -q`；`CI=1 npx playwright test --workers=1`（全套，不因只動前端而略過 pytest）。

## 回歸計畫（SDLCAIP2-45 及相關既有 e2e）
實作後完整重跑 `tests/e2e/`，特別確認下列斷言維持通過（理由已逐條對照）：
| 既有斷言 | 為何不受影響 |
|---|---|
| 45 AC1 `#view-admin .card` `.first()` 背景/邊框/圓角 | 新卡片是第二張 `.card`，`.first()` 仍為用量卡；兩者同為共用 `.card` token |
| 45 AC2 `.action-table th/td` `.first()` 色值 | `.first()` 為用量表；新表亦繼承相同 scoped 規則（值相同），且 DOM 在後 |
| 45 AC3 `#view-admin h4` count=2、首個 14px/500 | 新區塊**不使用 `<h4>`**（標題為 `.section-title`），count 維持 2；`.section-title` `.first()` 仍為原標題且 ≠14px |
| 45 AC4 scrollWidth ≤ clientWidth、`.ds-table-scroll`/`.action-table` `.first()` min-width=560 | 新表包在 `.ds-table-scroll`、`min-width:0`、email 欄 `overflow-wrap:anywhere`；`min-width:0` 覆寫只套新表（id specificity），`.first()` 仍為 560px；表單於 <480px 改直向 |
| 45 AC5 `#view-admin` innerHTML 無 emoji/符號 | 新區塊文字僅中文、「—」(U+2014)；不使用 ✓/✕/emoji（符號範圍 U+2600–27BF） |
| `view-history-detail`/`view-result-cards` 的 `#view-admin .section-title` `.first()` ≠ 18px | `.first()` 仍為原標題；未新增 `#view-admin .section-title` 規則 |
| `view-upload` AC1/AC8 `#view-admin .card` `.first()` 與 view-upload `.card` 相等比對 | 未改 `.card` 規則；第一張 card 不變 |
| `upload-button-reset` `#view-admin button:has-text("← 返回")` | 新按鈕文字為「新增/移除/確認移除/取消/重試」，不含「← 返回」，不產生多重匹配 |
| `design-system-foundation` `#admin-dashboard-btn` | 未改入口按鈕 |
| 既有測試開啟儀表板時只 mock `/api/admin/usage`（如 view-upload AC8） | 新增的清單 GET 會打到 e2e_server（`role=user`，回 403/錯誤）→ 僅在白名單區塊顯示訊息，不 throw、不影響用量與斷言 |
共用 selector 零修改的證明方式：實作 PR 的 diff 在 `<style>` 內只能是**新增**行（`#allowed-users-card`/`#view-admin #allowed-users-table` 開頭的規則），審查時以此檢視。

## 開放設計問題（定稿時必須為空）
無。
（備註，非待決問題：AC5 重複新增時輸入框是否清空 spec 未規範，設計取「保留不動」，因 AC4 只對 201 規範清空；若人類偏好清空，僅需改一行，不影響其他設計。）
