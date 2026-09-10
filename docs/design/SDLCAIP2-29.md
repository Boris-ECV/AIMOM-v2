# 設計文件 — SDLCAIP2-29 已保留會議紀錄匯出 API（依 meeting_id 匯出 docx/pdf）

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-29，由 SDLCAIP2-19 設計階段拆分、經
HUMAN-INPUT SDLCAIP2-25 確認獨立處理）。核心行為：新增
`GET /export/meetings/{meeting_id}?format=docx|pdf`，依已保留會議紀錄的
`meeting_id` 產生 docx/pdf，內容取自 Meetings 表當下最新的 `minutes_json`
（因此自動反映 SDLCAIP2-19 PATCH 後的最新版本）；文件標題用該筆紀錄的
`title`，檔名沿用 `{meeting_id}.docx/pdf` 慣例；查無或非本人擁有一律 404。
範圍外：既有 `/export/{job_id}` 行為不變；批次匯出、匯出排程。

## 介面/API 契約

### `GET /api/export/meetings/{meeting_id}`（新端點，加入 `src/export.py`）

**Request**
- Path：`meeting_id`（string，與 `GET/DELETE/PATCH /meetings/{meeting_id}`
  同一識別碼）
- Query：`format`（string，預設 `"docx"`，僅支援 `"docx"` / `"pdf"`，與既有
  `/export/{job_id}` 參數同名同語意）
- 認證：沿用 `app.py` 掛在 `export_router` 上的 `Depends(get_current_user)`，
  以 `user.email` 作為 `user_id` 做擁有權查詢

**Response**
- `200`：`StreamingResponse`，與既有 `/export/{job_id}` 完全相同的回應形狀
  - `format=docx` → `media_type` 為
    `application/vnd.openxmlformats-officedocument.wordprocessingml.document`，
    `Content-Disposition: attachment; filename="{meeting_id}.docx"`
  - `format=pdf` → `media_type` 為 `application/pdf`，
    `Content-Disposition: attachment; filename="{meeting_id}.pdf"`
- `400`：`format` 非 `docx`/`pdf`，`detail`="format 僅支援 docx 或 pdf"
  （與既有 `/export/{job_id}` 用字一致）
- `404`：`meeting_id` 不存在，或存在但 `user_id` 不符（`db.get_meeting()`
  回傳 `None`），`detail`="找不到此會議紀錄"（與 `history.py` GET/DELETE/PATCH
  用字一致，不使用 403）
- `500`：非預期例外，交由 `app.py` 全域 exception handler 處理，本路由不另
  包 try/except（CONSTITUTION 失敗處理哲學）

既有 `GET /api/export/{job_id}` 路由與行為完全不變。

## 資料模型
無新增資料表／索引／欄位。純讀取既有 Meetings 表（`user_id` HASH +
`meeting_id` RANGE）現有 item 的 `title` 與 `minutes_json`。

## 關鍵技術決策

1. **新路由加入 `src/export.py`（而非 `history.py`），沿用 `history.py`
   的 `db.get_meeting()` 讀取模式。**
   CONSTITUTION 程式碼風格要求「每個功能一個檔案 + 一個 APIRouter」；本
   端點的職責是「產生 docx/pdf」，與 `export.py` 既有的 `_build_docx`/
   `_build_pdf`/`_meeting_info_lines` 同屬匯出功能，路由掛載於 `export_router`
   之下與既有 `/export/{job_id}` 相鄰最合理，避免 `history.py` 混入匯出
   格式相關程式碼；資料存取則是唯讀呼叫 `db.get_meeting()`，不需要把
   `db` 模組職責搬進 `export.py` 之外的地方。

2. **直接重用 `_build_docx(minutes, label)` / `_build_pdf(minutes, label)`，
   `label` 參數改傳 `meeting_id`（檔名沿用既有 `job_id` 檔名慣例），標題文字
   維持函式內部 `f"會議紀錄 - {label}"` 不變。**
   Ticket AC 明確要求「文件標題使用該筆紀錄的 title」，但既有
   `_build_docx`/`_build_pdf` 的 `job_id` 參數同時身兼「檔名」與「文件內
   標題文字」兩種用途（`doc.add_heading(f"會議紀錄 - {job_id}")`）。若直接
   把 `meeting_id` 換成 `title` 傳入，檔名會變成含 `title` 特殊字元的字串，
   正是 AC 第一段刻意避免的 Content-Disposition 問題。因此本 Story**不修改
   `_build_docx`/`_build_pdf` 的既有簽章語意**，而是新增一個極小的組裝步驟：
   在呼叫端把 `minutes` 物件的 `meeting_info` 前面插入一行等同「標題」的
   資訊——具體做法：呼叫 `_build_docx(minutes, meeting_id)` 產生檔案後，
   讓標題行改為 `f"會議紀錄 - {title}"` 而非 `f"會議紀錄 - {job_id}"`。為此
   將 `_build_docx`/`_build_pdf` 的第二個參數語意從「job_id（兼標題與檔名）」
   拆成兩個獨立參數：`heading: str`（文件內標題文字）與呼叫端另行組裝
   `filename`。即：
   ```python
   def _build_docx(minutes: dict, heading: str) -> bytes: ...
   def _build_pdf(minutes: dict, heading: str) -> bytes: ...
   ```
   既有 `/export/{job_id}` 呼叫處改為 `_build_docx(minutes, job_id)`
   （`heading=job_id`，行為完全不變，因為原本 heading 也是 job_id）；新端點
   呼叫 `_build_docx(minutes, title)`（`heading=title`），檔名另由呼叫端組成
   `f"{meeting_id}.docx"`。此改法是函式簽章「重新命名」而非邏輯變更，
   `/export/{job_id}` 現有測試行為不受影響。

3. **`minutes` 取得方式：`json.loads(item["minutes_json"])`，與
   `history.py` 既有 `GET /meetings/{meeting_id}` 完全一致。**
   `db.get_meeting()` 回傳的 item 裡 `minutes_json` 是 JSON 字串，非 dict；
   沿用既有已驗證過的解析方式，不另外發明或加驗證層（CONSTITUTION 避免
   不必要抽象層）。

4. **擁有權/存在性檢查沿用 `db.get_meeting(user_id, meeting_id)` 單一呼叫，
   回傳 `None` 一律 404，不區分「不存在」與「非本人」。**
   與 `history.py` GET/DELETE/PATCH 三個既有端點使用同一個函式、同一種
   404-only 判斷方式，維持全站一致的資訊揭露原則（不用 403，避免洩漏
   meeting_id 是否存在）。

## 開放設計問題（定稿時必須為空）
無。
