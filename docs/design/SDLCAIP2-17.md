# 設計文件 — SDLCAIP2-17 已保留會議紀錄詳情頁編輯 UI（拆分後改寫範圍）

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-17）。核心行為：在 SDLCAIP2-32 提供的
「已保留會議紀錄唯讀詳情頁」上加入編輯模式切換——點擊「編輯」進入可編輯
狀態並顯示「儲存」／「取消」；點擊「儲存」呼叫既有 `PATCH
/api/meetings/{meeting_id}`（SDLCAIP2-19 已完成），成功則切回唯讀並顯示
最新內容＋成功提示；失敗（網路錯誤／非 2xx，含 404）則停留編輯模式、不遺失
使用者輸入，並顯示錯誤提示（404 訊息為「找不到此會議紀錄」）。範圍外：
編輯後立即重新匯出（SDLCAIP2-29 已處理匯出對最新內容的反映）、編輯
`transcript_text`、刪除會議紀錄、並發編輯衝突偵測、唯讀詳情頁／歷史列表
本身（SDLCAIP2-32 職責）。

## ⚠️ 風險／假設（依賴 SDLCAIP2-32，尚未合併）

SDLCAIP2-32 目前也在 Designing 階段、平行進行，本設計無法讀取其定稿的
設計文件或實作。以下對其唯讀詳情頁形狀的假設是本設計的**前提條件**，若
SDLCAIP2-32 實際實作與此不符，開發者需要回頭調整本 Story 的整合點（非重新
設計，屬於銜接風險，請 reviewer／人類在 G1b／SDLCAIP2-32 定稿後複核）：

1. 詳情頁遵循既有 `showView(id)` 慣例，是 `<div class="view">` 容器
   （命名假設為 `view-meeting-detail`，實際 id 以 SDLCAIP2-32 為準），
   內部有可定位的 DOM 節點分別顯示：會議資訊（日期/時間/地點/參與者）、
   摘要、待辦事項、決定事項、討論重點——沿用 `view-result` 既有欄位分區
   （見下方關鍵決策 #1），而非另一套版面。
2. 詳情頁載入時會將該筆會議紀錄整包存成一個模組級/畫面級狀態物件（本設計
   稱之為 `state.detail`，類比既有 `state.minutes`），內容形狀等同
   `GET /api/meetings/{meeting_id}` 回應的 `minutes` 欄位（`job_id`、
   `template`、`meeting_info`、`summary`、`action_items`、`decisions`、
   `sections`）——與 SDLCAIP2-19/29 設計文件中已定案的 `minutes` JSON
   形狀一致。若 SDLCAIP2-32 改用不同的狀態變數名稱，僅需替換本設計中
   `state.detail` 的實際存取路徑，DOM 收集/覆寫邏輯不受影響。
3. 詳情頁本身**不**內建編輯能力（唯讀），本 Story 是在其之上疊加一層
   編輯模式，不修改 SDLCAIP2-32 的唯讀渲染函式本體，只在其渲染出的 DOM
   節點上掛編輯用的 class/屬性與新按鈕。

## 介面/API 契約

本 Story 不新增後端端點，純消費 SDLCAIP2-19 已定案的既有端點：

### 消費：`PATCH /api/meetings/{meeting_id}`（既有，SDLCAIP2-19）
- **呼叫方式**：`apiFetch('/api/meetings/${meetingId}', { method: 'PATCH',
  headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })`，
  沿用既有 `apiFetch` 的 Bearer 認證＋401 自動導向登入閘的包裝，不另外
  處理認證。
- **Request body（`payload`）**：完整 `minutes` 物件，形狀與
  SDLCAIP2-19 設計文件定案的 request body 完全相同（整份覆蓋語意，非
  partial patch）：
  ```json
  {
    "job_id": "<沿用 state.detail.job_id 原樣回填，前端不編輯此欄位>",
    "template": "<沿用 state.detail.template 原樣回填，本 Story 不提供模板切換>",
    "meeting_info": { "date": "", "time": "", "location": "", "participants": [] },
    "summary": "string",
    "action_items": [ { "owner": "", "task": "", "due": "" } ],
    "decisions": ["string"],
    "sections": [ { "title": "string", "content": "string" } ]
  }
  ```
  組裝方式沿用 `view-result` 既有的「從 DOM 收集表單值」模式
  （`getMeetingInfoFromForm()` + 逐一讀取 `#action-tbody`/`#decision-list`
  的 `textContent`），只是資料來源從匯出用途改為 PATCH payload——見下方
  關鍵決策 #1。
- **成功（200）**：response body 即更新後的完整 `GET` 同形狀紀錄
  （`{meeting_id, title, transcript_text, minutes, expires_at}`）。前端
  以 `data.minutes` 覆寫 `state.detail`，呼叫 SDLCAIP2-32 的唯讀渲染
  函式重新渲染，並切回唯讀模式（拿掉編輯模式 class／隱藏儲存取消按鈕），
  `toast('已儲存')`。
- **404**：`toast('找不到此會議紀錄')`，**不**切回唯讀模式、**不**清空
  使用者輸入中的欄位值（維持 AC4 字面要求）。
- **其他失敗（網路錯誤 fetch reject、非 2xx 非 404）**：`toast('儲存失敗，請稍後再試')`，
  同樣停留編輯模式、不遺失輸入（AC3）。
- **無新增/變更的後端契約**——本 Story 是純前端改動。

## 資料模型
無新增資料模型。純前端狀態變更：新增一個畫面級布林旗標
`state.detailEditing`（預設 `false`）追蹤編輯模式開關，不落地儲存、不
影響任何後端資料表。

## 關鍵技術決策

1. **編輯模式的 UI 機制沿用 `view-result` 既有的「雙擊進入
   contenteditable」局部欄位編輯模式（`enableEdit`/`disableEdit`/
   `ondblclick`/`onblur`），而非另外設計一套全新的表單編輯 UI。**
   理由：`view-result` 已建立好「摘要用 `<p contenteditable>` 雙擊編輯」
   與「待辦事項表格用 `<td contenteditable>` 雙擊編輯」兩種既定模式，
   詳情頁的可編輯欄位集合（會議資訊、摘要、待辦事項、決定事項、討論
   重點）與 `view-result` 完全對應；重用同一套機制維持全站 UI 一致性，
   符合 CONSTITUTION「遵循既有慣例優先於個人偏好」與「避免不必要的
   抽象層」。差異點：`view-result` 的雙擊編輯永遠可用（欄位本身天生
   可編輯，儲存與否是另一個按鈕），而詳情頁預設唯讀，因此新增一個
   外層「編輯」開關（見決策 #2）統一控制所有欄位是否允許雙擊進入
   `contenteditable`，而非每個欄位各自判斷。
2. **編輯模式用單一畫面級旗標 `state.detailEditing` + 一個 CSS class
   （例如在容器加 `.editing`）切換，不做整頁重新渲染。**
   進入編輯模式：對會議資訊改用 `<input>`（沿用 `view-result` 的
   `#meeting-date` 等既有 input 元素/命名慣例）、其餘欄位比照
   `view-result` 加上 `ondblclick="enableEdit(this)"` 允許
   `contenteditable`，並顯示「儲存」「取消」按鈕、隱藏「編輯」按鈕。
   取消：捨棄 DOM 上未儲存的變更，重新以 `state.detail`（進入編輯模式
   前的快照）呼叫唯讀渲染函式復原畫面，切回唯讀模式。
   理由：這是最小改動——重用現有 DOM 節點與既有雙擊編輯函式，不需要
   引入模板引擎或虛擬 DOM diff，符合 CONSTITUTION「前端純靜態
   HTML/JS，不引入新框架」與「避免不必要的抽象層」。
3. **儲存失敗（含 404）時完全不觸碰使用者已輸入的 DOM 值，只切換
   toast 訊息、不呼叫任何渲染/復原函式。**
   理由：AC3、AC4 明確要求輸入不遺失、且不得切回唯讀模式；由於編輯模式
   本身就是直接操作既有 DOM（`contenteditable`/`<input>`），只要「儲存
   失敗」路徑不呼叫渲染函式覆寫這些節點，就自然滿足「不遺失」，不需要
   額外實作一份「暫存輸入快照」機制——被動地什麼都不做即是正確行為。
4. **PATCH payload 中的 `job_id`／`template` 兩個欄位固定原樣回填自
   `state.detail`（進入編輯模式前的既有值），不提供 UI 讓使用者在此
   Story 編輯。**
   理由：SDLCAIP2-19 的 PATCH 語意是整份覆蓋，若遺漏欄位會被覆蓋為
   `undefined`/遺失；ticket AC 只列出「會議資訊、摘要、待辦事項、決定
   事項、討論重點」五類可編輯欄位，不含模板切換，維持 CONSTITUTION
   「範圍紀律：只實作 spec 明確要求的範圍」，模板切換若未來需要應是
   獨立 Story。
5. **404 與其他失敗共用同一組「停留編輯模式＋不遺失輸入」行為，僅
   toast 文字不同。**
   理由：AC3（一般失敗）與 AC4（404）在畫面行為上完全相同，唯一差異是
   錯誤訊息文字；沒有必要為 404 開一條獨立的程式碼路徑分支畫面狀態，
   只需依 response status 決定 toast 內容，符合「避免不必要的抽象層」。

## 開放設計問題（定稿時必須為空）
無。
