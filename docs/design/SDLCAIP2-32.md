# 設計文件 — SDLCAIP2-32 已保留會議紀錄歷史列表與詳情唯讀瀏覽 UI

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-32）。核心行為：新增「歷史紀錄」畫面，
呼叫既有 `GET /api/meetings` 顯示已保留紀錄清單（標題＋建立時間），點擊
清單項目呼叫既有 `GET /api/meetings/{meeting_id}` 切換到詳情畫面，唯讀
顯示標題、逐字稿內容（`transcript_text`）與會議紀錄內容（`minutes`，含
摘要／待辦事項／決定事項／討論重點），所有欄位不可編輯；空清單顯示空
狀態；詳情頁遇 404 顯示錯誤並可返回列表。

範圍外（依 ticket 明列）：編輯（SDLCAIP2-17 的工作）、刪除會議、從詳情頁
重新匯出、清單分頁/排序/搜尋、任何「保留此會議」觸發 UI。本故事僅設計
唯讀瀏覽 UI；SDLCAIP2-17 將在本故事的詳情畫面基礎上疊加編輯模式（見下方
關鍵技術決策 #2 對此的因應）。

後端 `GET /api/meetings`、`GET /api/meetings/{meeting_id}` 已由 SDLCAIP2-19
完成（見 `docs/design/SDLCAIP2-19.md`），本故事不新增/變更後端端點。

## 介面/API 契約

本故事不新增後端端點，僅消費既有兩個 GET 端點。

### `GET /api/meetings`（既有，本故事消費）
**Response（200）**
```json
{ "meetings": [ { "meeting_id": "string", "title": "string", "created_at": 1234567890, "expires_at": 1234567890 }, ... ] }
```
空清單時 `meetings: []`（AC2 空狀態情境）。

### `GET /api/meetings/{meeting_id}`（既有，本故事消費）
**Response（200）**
```json
{
  "meeting_id": "string",
  "title": "string",
  "transcript_text": "string",
  "minutes": {
    "meeting_info": { "date": "", "time": "", "location": "", "participants": [] },
    "summary": "string",
    "action_items": [ { "owner": "", "task": "", "due": "" } ],
    "decisions": ["string"],
    "sections": [ { "title": "string", "content": "string" } ]
  },
  "expires_at": 1234567890
}
```
**404**：`{"detail": "找不到此會議紀錄"}`（AC5）。

### 前端新增畫面與函式（無對外 API，屬前端內部契約明確化）

**導覽入口**：header 內、`#admin-dashboard-btn` 之後新增
```html
<button id="history-nav-btn" class="btn btn-outline btn-sm" style="margin-left:8px;" onclick="openHistoryList()">📜 歷史紀錄</button>
```
不做角色門檻（不同於 `admin-dashboard-btn` 的 `role === 'admin'` 判斷）——
歷史紀錄是「使用者名下」的個人資料，spec 未要求角色限制。登入後（`showApp()`
內）即顯示，不需額外呼叫 `/api/me` 判斷。

**新增兩個 view**（沿用既有 `.view`/`.view.active`/`showView(id)` 機制）：
`#view-history`（清單）、`#view-history-detail`（詳情）。

**`#view-history`**
```html
<div id="view-history" class="view">
  <div class="card">
    <div class="section-title">📜 歷史紀錄</div>
    <table class="action-table" id="history-table" style="display:none;">
      <thead><tr><th>標題</th><th>建立時間</th></tr></thead>
      <tbody id="history-tbody"></tbody>
    </table>
    <div id="history-empty" class="empty-state" style="display:none;">
      <p>尚無已保留的會議紀錄</p>
    </div>
  </div>
</div>
```
`history-tbody` 每列 `<tr onclick="openMeetingDetail('<meeting_id>')" style="cursor:pointer;">`，
兩欄為 `esc(title)` 與 `fmtDateTime(created_at)`（見下方新增輔助函式）。

**`#view-history-detail`**
```html
<div id="view-history-detail" class="view">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <h2 id="history-detail-title" style="font-size:1.2rem;"></h2>
      <button class="btn btn-outline btn-sm" onclick="showView('view-history')">← 返回歷史列表</button>
    </div>
  </div>
  <div id="history-detail-error" class="empty-state" style="display:none;">
    <p id="history-detail-error-msg"></p>
    <button class="btn btn-outline btn-sm" onclick="showView('view-history')">← 返回歷史列表</button>
  </div>
  <div id="history-detail-body" style="display:none;">
    <div class="tabs">
      <button class="tab active" id="history-tab-btn-minutes" onclick="switchHistoryTab('minutes')">📝 會議紀錄</button>
      <button class="tab" id="history-tab-btn-transcript" onclick="switchHistoryTab('transcript')">🎙 逐字稿</button>
    </div>
    <div id="history-tab-minutes">
      <div class="card">
        <div class="section-title">摘要</div>
        <p id="history-summary-text"></p>
      </div>
      <div class="card">
        <div class="section-title">待辦事項</div>
        <table class="action-table">
          <thead><tr><th>負責人</th><th>工作事項</th><th>截止時間</th></tr></thead>
          <tbody id="history-action-tbody"></tbody>
        </table>
      </div>
      <div class="card">
        <div class="section-title">決定事項</div>
        <ul class="decision-list" id="history-decision-list"></ul>
      </div>
      <div class="card">
        <div class="section-title">討論重點</div>
        <div id="history-topics-container"></div>
      </div>
    </div>
    <div id="history-tab-transcript" style="display:none;">
      <div class="card">
        <div id="history-transcript-container"></div>
      </div>
    </div>
  </div>
</div>
```

**新增 JS 函式**
- `openHistoryList()`：`showView('view-history')`；`apiFetch('/api/meetings')`；
  成功時若 `meetings.length === 0` 顯示 `#history-empty`、隱藏
  `#history-table`，否則填 `#history-tbody`、顯示 `#history-table`、隱藏
  `#history-empty`；`res.ok` 為否或例外時 `toast('讀取歷史紀錄失敗')`（沿用
  `openAdminDashboard()` 既有的失敗提示慣例）。
- `openMeetingDetail(meetingId)`：`showView('view-history-detail')`；
  `apiFetch(`/api/meetings/${meetingId}`)`；`res.status === 404` 時隱藏
  `#history-detail-body`、顯示 `#history-detail-error`（訊息取 `data.detail`
  或預設「找不到此會議紀錄」），`res.ok` 時隱藏 `#history-detail-error`、
  顯示 `#history-detail-body`、呼叫 `renderMinutesReadOnly(data)`。
- `renderMinutesReadOnly(data)`：唯讀渲染，寫入 `#history-detail-title`、
  `#history-summary-text`（`textContent`，非 contenteditable）、
  `#history-action-tbody`（純 `<td>`，無 `contenteditable`/`ondblclick`）、
  `#history-decision-list`、`#history-topics-container`（沿用
  `.topic-item`/`.topic-header`/`.topic-body` 樣式，但用獨立
  `toggleHistoryTopic(i)` 與 `history-topic-body-${i}`/`history-topic-arrow-${i}`
  id，避免與 `view-result` 既有 `toggleTopic()`/`topic-body-${i}` 撞名）、
  `#history-transcript-container`（單一 `<pre>` 區塊顯示 `esc(data.transcript_text)`，
  無逐段/講者渲染，見關鍵技術決策 #3）。
- `switchHistoryTab(tab)`：與既有 `switchTab()` 邏輯相同，操作
  `history-tab-minutes`/`history-tab-transcript`/`history-tab-btn-*`。
- `fmtDateTime(epochSeconds)`：新增輔助函式，`new Date(epochSeconds * 1000).toLocaleString('zh-TW')`。

## 資料模型
無新增資料模型。本故事純消費既有 `GET /api/meetings`、
`GET /api/meetings/{meeting_id}` 回應（SDLCAIP2-19 已定案的欄位形狀），
不新增/變更任何欄位、資料表或索引。

## 關鍵技術決策

1. **新增兩個獨立 view（`view-history`、`view-history-detail`），不在既有
   view 內加子狀態。** 沿用既有 4 個 view（`view-admin`/`view-upload`/
   `view-progress`/`view-result`）「一個畫面一個 view」的既定慣例，用
   `showView(id)` 切換；在既有 view 內部加條件式子狀態會破壞這個一致的
   心智模型，也讓 CSS/DOM 責任邊界變模糊。

2. **新增獨立 `renderMinutesReadOnly(data)` 函式，結構鏡射既有
   `renderMinutes()`（同樣的摘要／待辦事項／決定事項／討論重點四張
   card），但寫入完全獨立的一組 DOM id（`history-*` 前綴），不含任何
   `contenteditable`/`ondblclick`/`onchange="markModified()"`。** 這是刻意
   複製而非重用 `renderMinutes()`：(a) `renderMinutes()` 的 DOM 天生帶編輯
   副作用（`markModified()`、`contenteditable` 屬性切換），唯讀畫面重用它
   等於要在共用函式裡加條件分支去「關掉」編輯行為，反而更脆弱；(b) ticket
   明確要求「清楚分離唯讀渲染邏輯」以利後續 SDLCAIP2-17 疊加編輯模式——
   獨立的 `renderMinutesReadOnly()` 讓 SDLCAIP2-17 可以直接在這個唯讀骨架
   上疊加 toggle-to-edit 行為，而不需要先拆解一個混雜編輯邏輯的既有函式。

3. **逐字稿以單一 `<pre>` 區塊顯示 `transcript_text` 純文字，不重用
   `renderTranscript()` 的逐段＋講者色塊 UI。** `GET /api/meetings/{id}`
   回應形狀（見 SDLCAIP2-19 設計文件）只提供扁平化的 `transcript_text`
   字串，沒有 `segments` 陣列或講者標籤——「保留」流程本身就不保存
   segment 層級結構，此故事的資料契約里也沒有這份資訊可用；重新產生
   segment 切分不在 spec 範圍內，也超出前端能從既有回應推導的資訊。

4. **詳情頁不顯示 `meeting_info`（日期／時間／地點／參與者）。** AC4 的
   Gherkin 明確列舉「會議紀錄內容」只包含「摘要／待辦事項／決定事項／
   討論重點」四項，未提及 `meeting_info`；依此逐字對應範圍，不額外渲染
   spec 未列出的欄位，避免超出本故事界定的顯示範圍。

5. **`created_at` 假設為 epoch 秒數，以 `fmtDateTime()` 用
   `toLocaleString('zh-TW')` 顯示。** 回應中 `created_at` 與既有
   `expires_at`（epoch 秒的 TTL 屬性，見 SDLCAIP2-19 設計文件）同屬
   Meetings 表 attribute，依既有欄位慣例推斷格式一致，非憑空臆測；若
   實際型別不同，屬 developer 實作階段可直接依真實 API 回應調整的顯示
   細節，不影響本設計的元件結構。

6. **導覽入口不做角色門檻，登入即顯示。** 對照 `admin-dashboard-btn` 是
   `role === 'admin'` 才顯示（管理者專屬功能），歷史紀錄依 spec 是「使用者
   名下」的個人資料查詢，任何已登入使用者都應能存取，不需要額外呼叫
   `/api/me` 判斷角色。

7. **清單與 404 錯誤都採用既有 `.empty-state` class 樣式，失敗提示沿用
   `toast()`。** 沿用 `renderTranscript()`/`renderMinutes()` 已建立的
   空狀態視覺慣例與 `openAdminDashboard()` 的失敗提示慣例，不引入新的
   UI 樣式。

## 開放設計問題（定稿時必須為空）
無。
