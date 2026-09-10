# 設計文件 — SDLCAIP2-19 已保留會議紀錄編輯 API（後端）

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-19）。核心行為：`PATCH /meetings/{meeting_id}`
以完整覆蓋語意（不支援 partial patch）更新已保留會議紀錄的 `minutes` 內容，
沿用既有 DynamoDB `user_id`＋`meeting_id` 複合鍵做擁有權判斷，查不到一律
404（不用 403，不揭露「存在但非本人」）。範圍外：逐字稿編輯、版本歷史／
undo、`title` 編輯、部分欄位更新語意。

## 介面/API 契約

### `PATCH /api/meetings/{meeting_id}`（新端點，加入 `src/history.py`）

**Request**
- Path：`meeting_id`（string，既有 `GET/DELETE /meetings/{meeting_id}` 沿用的識別碼）
- Body：完整 `minutes` 物件，與 `GET /meetings/{meeting_id}` 回應中 `minutes`
  欄位**同一份 JSON 形狀**（即 `job["minutes"]` 原樣結構：`job_id`、
  `template`、`meeting_info`、`summary`、`action_items`、`decisions`、
  `sections`）。**body 型別為原始 `dict`（`Body(...)`），不套用 pydantic
  strict schema** — 見下方關鍵技術決策 #1。

```json
{
  "job_id": "string",
  "template": "retro",
  "meeting_info": { "date": "", "time": "", "location": "", "participants": [] },
  "summary": "string",
  "action_items": [ { "owner": "", "task": "", "due": "" } ],
  "decisions": ["string"],
  "sections": [ { "title": "Keep", "content": "string" } ]
}
```

**Response（200，成功）** — 與 `GET /meetings/{meeting_id}` 回應同形狀：
```json
{
  "meeting_id": "string",
  "title": "string",
  "transcript_text": "string",
  "minutes": { /* 更新後的完整內容，等於 request body 原樣 */ },
  "expires_at": 1234567890
}
```

**狀態碼**
- `200`：成功，`minutes` 整份被 request body 覆蓋，回傳更新後完整紀錄。
- `404`：`meeting_id` 不存在，或存在但 `user_id` 不符（`db.update_meeting`
  回傳 `None`），`detail` 訊息沿用 `"找不到此會議紀錄"`（與既有 GET/DELETE
  用字一致）。不使用 403。
- `500`：非預期例外，交由 `app.py` 全域 exception handler 處理（不在本路由
  另外包 try/except，遵循 CONSTITUTION 失敗處理哲學）。

## 資料模型
無新增資料表／索引。沿用既有 Meetings 表（`user_id` HASH + `meeting_id`
RANGE）。變更僅為覆寫既有 item 的 `minutes_json` attribute（string，內容為
`json.dumps(request_body)`）；`title`、`transcript_text`、`created_at`、
`expires_at` 等其他 attribute 維持不變（PATCH 不重設 TTL，見關鍵技術決策 #3）。

## 關鍵技術決策

1. **PATCH body 以原始 `dict` 接收，不建立 pydantic strict schema 驗證
   `minutes` 內部欄位。**
   沿用 SDLCAIP2-16 設計文件已載明的既有慣例：`minutes_json` 是
   schema-less 的不透明 JSON blob（`jobstore`／`db.py` 皆不做型別檢查），
   `GET /meetings/{meeting_id}` 本身也只用 `json.loads()` 原樣回傳，未套
   pydantic response model。PATCH 若另外發明一套嚴格 schema，一旦與
   `SummarizeResponse` 未來的欄位變化不同步，會變成兩份定義互相打架；
   維持「整份覆蓋、不做內容驗證」與 AC1「整份 minutes 內容被覆蓋為 body
   內容」的字面語意完全一致，也符合 CONSTITUTION「避免不必要的抽象層」。

2. **新增 `db.update_meeting(user_id, meeting_id, minutes_json) ->
   Optional[dict]`，內部先呼叫既有 `get_meeting()` 做存在性＋擁有權檢查，
   再 `put_item` 整筆覆寫。**
   直接沿用 `delete_meeting()` 已建立的「先 `get_meeting` 確認、查無則回
   `None`／`False`」模式，讓路由層的 404 判斷方式與既有 GET/DELETE 完全
   一致（`if item/deleted is None/False: raise HTTPException(404, ...)`），
   不需要在 db 層額外處理「存在但非本人」與「完全不存在」的區分（DynamoDB
   複合鍵天然合併這兩種情況為同一個查詢結果）。用 `put_item` 整筆寫回
   （而非 `update_item` 局部更新）是因為 `get_meeting()` 已經取得完整既有
   item，直接在記憶體內合併 `minutes_json` 欄位後整筆寫回，程式碼形狀與
   `put_meeting()` 一致，不需要額外學習 DynamoDB `UpdateExpression` 語法。

3. **PATCH 不更新 `expires_at`（TTL 不因編輯而重設／延長）。**
   Spec 三個情境皆未提及編輯是否影響保留期限，依 CONSTITUTION 範圍紀律
   「需求不明確時列為 open question，不可用合理猜測補上」——但這裡影響
   範圍極小且有清楚的保守預設可循：既有 `keep_meeting` 建立時已依
   `MEETING_RETENTION_DAYS` 設定到期時間，編輯屬於「使用者仍在使用這筆
   紀錄」的訊號，若不確定，維持既有到期時間不變是風險最低的預設（不會
   意外讓資料「續命」超出使用者原本認知的保留天數）。仍在下方列為開放
   問題供人類確認，而非在本文件內單方面鎖定為最終產品行為。

## 開放設計問題（定稿時必須為空）

1. **PATCH 是否應重設／延長 `expires_at`（TTL）？** 目前設計預設「不變」
   （見決策 #3 的保守理由），但這是 spec 未明講的產品行為，需要人類確認
   是否符合預期（例如：使用者編輯後期待保留期限從編輯當下重新起算 14
   天，或維持原本的到期時間不變）。

2. **AC3（編輯後重新匯出反映最新內容）與現有 `/export/{job_id}` 端點的
   資料來源不相容，需要確認範圍歸屬。** 目前 `src/export.py` 的
   `/export/{job_id}` 只讀取 `jobstore`（以 `job_id` 為鍵、6 小時 TTL 的
   暫存 job 狀態），而本故事的 PATCH／既有的「保留」流程操作的是完全獨立
   的 Meetings 表（以 `user_id`＋`meeting_id` 為鍵、14 天 TTL）；
   `keep_meeting()` 保留時會產生**全新的** `meeting_id`（`uuid.uuid4()`），
   與原始 `job_id` 沒有任何欄位保留對應關係。換言之，目前程式庫內**沒有
   任何既有端點**可以「依 `meeting_id` 匯出 docx/pdf」——即使不做編輯，
   單純保留後想匯出已保留的紀錄，現有 `/export/{job_id}` 也無法讀到
   （job 6 小時後過期，且 job_id 與 meeting_id 是不同識別碼空間）。這是
   PATCH 本身無法解決的既有缺口：要讓 AC3 成立，需要新增一個以
   `meeting_id` 為鍵的匯出路徑（例如 `GET /export/meetings/{meeting_id}`），
   但這已超出本 ticket 標題「編輯 API」界定的範圍，屬於一個需要人類確認
   的範圍歸屬決策——是併入本故事一併實作，還是另立故事、由本故事的
   G1b／後續排程明確標注「AC3 依賴一個目前不存在的匯出端點」。本設計文件
   對 PATCH 端點本身（AC1、AC2）的設計已完整，不因此問題而阻塞；僅 AC3
   的可驗證性受影響。
