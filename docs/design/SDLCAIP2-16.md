# 設計文件 — SDLCAIP2-16 上傳錄音時可選擇會議模板，AI 依模板產出對應結構區塊

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-16）。核心行為：`/summarize` 接受選填
`template` 參數，依模板定義輸出結構化 `sections`；未帶 `template` 時套用
預設「一般會議」並維持 `meeting_info`、`action_items` 欄位不變；帶入不存在
的模板代碼回傳 400 並列出可用代碼清單。範圍外：自訂模板、前端 UI／匯出
渲染（後續 Story SDLCAIP2-15）、舊資料遷移。

內建模板清單（G1 核准，本文件對每個模板的區塊標題做出最終決定）：

| code             | 中文名稱       | section 標題（固定順序）                  |
|------------------|----------------|--------------------------------------------|
| `general`        | 一般會議（預設）| 無固定標題，沿用現行 `topics` 自由格式行為  |
| `project_status` | 專案進度會議   | 進度更新 / 風險與阻礙 / 下一步計畫          |
| `client_meeting` | 客戶業務會議   | 客戶需求 / 討論重點 / 後續跟進              |
| `brainstorm`     | 腦力激盪       | 發想主題 / 點子清單 / 後續評估              |
| `retro`          | Retro          | Keep / Problem / Try                        |

## 介面/API 契約

### `POST /api/summarize`（既有端點，擴充 request/response）

**Request（`SummarizeRequest`，新增欄位）**
```json
{
  "job_id": "string",
  "template": "retro"   // 選填，string，未帶或帶 null 視為 "general"
}
```

**Response（`SummarizeResponse`，欄位變更見下方「關鍵技術決策 #1」）**
```json
{
  "job_id": "string",
  "template": "retro",              // 新增：實際套用的模板代碼，永遠回填（未指定時為 "general"）
  "meeting_info": { "date": "", "time": "", "location": "", "participants": [] },
  "summary": "string",
  "action_items": [ { "owner": "", "task": "", "due": "" } ],
  "decisions": ["string"],
  "sections": [ { "title": "Keep", "content": "string" } ]
  // 原 "topics" 欄位移除，由語義相同、結構相同（title/content）的 "sections" 取代
}
```

- 固定模板（`project_status`／`client_meeting`／`brainstorm`／`retro`）：
  `sections` 陣列**永遠**恰好包含該模板定義的標題，且順序與上表一致（見
  關鍵技術決策 #3）。
- `general`（預設）：`sections` 陣列為自由格式，行為與現行 `topics`
  完全相同（LLM 依逐字稿內容自行決定議題標題與數量）。

**狀態碼**
- `200`：成功，回傳 `SummarizeResponse`。
- `400`：`job_id` 對應的 job 尚未完成 `/transcribe`（既有行為，不變）；
  **新增**：`template` 不在可用代碼清單內，`detail` 訊息列出可用代碼，例如
  `"未知的 template 代碼：not_exist。可用代碼：brainstorm, client_meeting, general, project_status, retro"`
  （驗證於呼叫 LLM 之前執行，避免無效請求浪費 LLM 成本）。
- `404`：`job_id` 不存在（既有行為，不變）。
- `500`／`503`：LLM 設定錯誤／服務失敗（既有行為，不變）。

## 資料模型
無新增資料表／索引。`jobstore` 的 job 仍以既有「整包 JSON 存在單一
`data` attribute」模式儲存（見 `src/jobstore.py`）；`minutes` 這個 JSON
blob 內新增兩個 key：`template`（string）、`sections`（取代原本的
`topics` key）。`decisions`、`meeting_info`、`action_items`、`summary`
key 不變。因 `jobstore` 本身是 schema-less（無型別檢查），此變更不需要
migration script；`舊資料不遷移`（spec 明列範圍外）——TTL 6 小時到期後
舊格式（含 `topics` 而非 `sections`）的 job 自然清除，`/history` 對舊
`minutes_json` 只做不透明的存取／回傳（見 `src/history.py`），不解析
內部欄位，不受影響。

## 關鍵技術決策

1. **`topics: List[Topic]` 重新命名為 `sections: List[Section]`，不是
   新增一個並行欄位。**
   `models.py` 現有 `Topic { title, content }` 結構與 spec 定義的
   section 完全同構（G1 gate finding #1）。AC2 的相容性保證文字明確只
   框定在「`meeting_info`、`action_items` 欄位不變」，未提及
   `topics`／`decisions`，因此把 `topics` 依語意改名為 `sections`（型別
   `Section` 沿用 `Topic` 的 `{title, content}` 形狀，直接改類別名稱，
   不保留 `Topic` 作為相容別名）屬於 AC2 文字明確允許的範圍，且避免
   `topics`／`sections` 兩個語意重疊欄位同時存在造成後續維護混淆。
   影響範圍：`src/frontend/index.html` 目前讀 `m.topics`（`|| []` 防禦
   式寫法，欄位消失只會讓議題區塊顯示空白，不會拋錯），前端渲染修正
   屬於 SDLCAIP2-15（該 Story 明列為此 Story 的後續依賴），本 Story
   不修前端。
2. **`decisions` 欄位不納入模板化，所有模板皆固定回傳同一份
   `decisions: List[str]`。** spec 的 Gherkin 三個情境只描述
   `sections`（AC1）與 `meeting_info`／`action_items`（AC2）；未要求
   `decisions` 依模板改變結構或消失。依 CONSTITUTION「範圍紀律」——不
   在需求未明確要求處自行擴大範圍——維持 `decisions` 現行行為不變。
3. **固定模板的 `sections` 一律依模板定義的標題清單、固定順序回傳，
   缺漏的標題以空字串 `content` 補齊，而非直接透傳 LLM 輸出的陣列。**
   `_normalize_sections()` 對固定模板：先把 LLM 回傳的 section 陣列
   建成 `{title: content}` 對照表，再依模板定義的標題清單逐一取值、
   查無則填 `""`；`general` 模板則沿用現行 `_normalize_topics()` 的
   自由格式邏輯（原樣搬移，只改函式名稱與回傳欄位名稱)。理由：AC1
   要求「section 標題符合 Retro 模板定義」，若直接透傳 LLM 輸出，標題
   文字、順序、數量都可能因 LLM 產出不穩定而飄移，測試會 flaky；
   固定映射確保回應結構「決定性（deterministic）」，也讓 SDLCAIP2-15
   前端可以放心依固定標題渲染欄位，不需要額外容錯邏輯。與
   `meeting_info` 現行「逐字稿未提及則留空字串，不臆測」的既有慣例
   一致（`models.py` `MeetingInfo` docstring）。
4. **新增 `src/meeting_templates.py`，以模組層級的靜態 dict
   （`TEMPLATES: dict[str, MeetingTemplate]`）定義 5 個內建模板，不做
   資料庫／設定檔化。** spec 明列「使用者自訂模板」為範圍外，內建模板
   清單本次是需求已核准的固定清單（見上表），沒有「執行期新增/修改
   模板」的需求，依 CONSTITUTION「避免不必要的抽象層」，用最簡單的
   靜態 Python 資料結構即可，不須為目前不存在的需求（可設定化）預先
   設計儲存層。
5. **`template` 驗證發生在呼叫 LLM 之前（fail fast）。** 未知代碼在
   組出逐字稿文字、呼叫 LLM API 之前就以 400 短路，避免浪費 LLM
   token 成本與時間去處理一個注定要丟棄的請求；沿用 CONSTITUTION
   「失敗處理哲學」既有慣例（`upload.py` 的 404/500 轉換模式）——
   對可預期的輸入錯誤用明確狀態碼＋清楚中文訊息的 `HTTPException`，
   不讓例外無聲穿透或退回 500。
6. **Response 新增 `template` 欄位，永遠回填實際套用的代碼（未指定時
   為 `"general"`），而非只在使用者有帶入時才回傳。** 讓下游
   SDLCAIP2-15（前端／匯出）與 `/history`、`/export` 未來讀取
   `minutes` 時，不需要另外判斷「這筆記錄到底用了哪個模板」，直接讀
   `minutes.template`；同時作為向下相容的顯式訊號（舊 job 若無此
   key，消費端可判斷為 pre-模板化資料）。
7. **`SYSTEM_PROMPT` 依模板動態組裝，而非為每個模板寫一份完整重複的
   prompt 字串。** 固定模板部份：在既有 prompt 架構上，把原本描述
   `topics` 欄位的那段改為描述 `sections`，並在該模板情境下額外插入
   一段「`sections` 必須恰好包含以下標題，依此順序：<清單>；某個標題
   若逐字稿未提及對應內容，`content` 填空字串，不可臆測或省略該
   標題」的固定指示（與現行 `meeting_info` prompt 段落「不可臆測」
   的用詞風格一致）。之所以仍讓 LLM 產出各標題內容而非只做本地
   規則抽取：判斷逐字稿哪段文字對應「Keep／Problem／Try」等語意
   分類，需要語言理解能力，不是關鍵字比對能做到的，且 `_normalize_
   sections()`（決策 #3）已經在後端把最終標題／順序鎖死，LLM 產出
   不穩定的部分只影響 `content` 品質，不影響回應結構的確定性。

## 開放設計問題（定稿時必須為空）
無。
