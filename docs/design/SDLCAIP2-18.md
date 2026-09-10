# 設計文件 — SDLCAIP2-18 逐字稿分頁講者命名 UI（前端）

## 對應需求規格
SDLCAIP2-18（G1 定稿版，經 HUMAN-INPUT 澄清 SDLCAIP2-27）。範圍：在既有
`view-result` 逐字稿分頁的講者重命名區塊（`#speaker-rename-area`，純前端、
無後端呼叫）加上「送出」按鈕，將姓名對應送到已合併的後端
`POST /api/speaker-names`（SDLCAIP2-20，見 `src/speaker_names.py` /
`src/models.py` 的 `SpeakerNamesRequest`/`SpeakerNamesResponse`），並依回傳
結果即時更新逐字稿顯示與匯出內容。不含「會議紀錄」分頁同步（明確排除於
spec 範圍外）。

## 介面/API 契約
沿用既有後端契約，前端不新增/變更任何後端路由，只新增一個前端函式呼叫既有
API：

**`POST {API}/api/speaker-names`**（已存在，`src/speaker_names.py`）
- Request body：
  ```json
  { "job_id": "<state.jobId>", "speaker_names": { "SPEAKER_A": "王小明", "SPEAKER_B": "李小華" } }
  ```
  `speaker_names` 只包含使用者「已填寫且與原始標籤不同」的項目（見下方
  key decision）；未填寫的講者不出現在這個 dict 裡。
- Response（200）：
  ```json
  { "job_id": "...", "speakers": ["王小明", "李小華"], "segments": [ { "start": ..., "speaker": "王小明", "text": "..." }, ... ] }
  ```
- 前端呼叫方式沿用 `apiFetch()`（帶 Authorization header、401 自動導向登入），
  沿用 `doUpload()`/`exportServerFile()` 既有的
  `try { ... } catch (e) { toast(...) }` + 按鈕 disable/還原 pattern。
- 錯誤處理：`res.ok` 為 false 時讀取 `data.detail` 丟出 `Error`，於 catch
  block 用 `toast()` 顯示；不新增前端自訂錯誤格式，維持與 `doUpload()`
  一致的既有慣例。

前端新增（無後端變更）：
1. `submitSpeakerNames()` — 新的 JS 函式，繫結到新的「送出」按鈕。
2. `#speaker-rename-area` 區塊內新增一個「送出」`<button>` 與一段固定的
   影響範圍提示文字（`<p>` 或 `<small>`，AC5）。

## 資料模型
無新增資料模型。前端 `state` 物件不新增欄位；沿用既有
`state.speakers`（`Record<原始標籤, 顯示名稱>`）與 `state.segments`。

## 關鍵技術決策

1. **送出的 `speaker_names` payload 只含「使用者實際填寫且改動過」的項目**
   （即 `state.speakers[tag] !== tag` 且 trim 後非空），而非把
   `state.speakers` 整包（含尚未改名、預設值等於原始標籤的項目）送出。
   理由：`loadResults()` 會把 `state.speakers` 預先填成
   `{ SPEAKER_A: 'SPEAKER_A', ... }` 當作預設值；若整包送出，未改名的講者
   也會被當成「使用者提交的姓名對應」送給後端（值與 key 相同、對後端結果
   無影響，但語意上偏離 AC2「一次送出所有『已填寫』的姓名對應」的明確用詞）。

2. **呼叫成功後，用回應的 `segments`/`speakers` 直接覆蓋
   `state.segments`（`state.speakers` 重設為 `{}`），而不是繼續疊加本地
   `state.speakers` 映射。**
   理由：後端已把新姓名寫回 job 的 `segments`（`seg.speaker` 直接變成新
   姓名字串），是後續 `renderTranscript()`／匯出函式讀取顯示名稱時的
   single source of truth；沿用舊的 `state.speakers[seg.speaker]` 映射會
   造成 key（原始標籤）已不存在於新 segments 中而失效。清空
   `state.speakers` 讓 `renderTranscript()` 既有的
   `state.speakers[seg.speaker] || seg.speaker` fallback 邏輯直接吃到
   `seg.speaker`（已是新姓名），不需要改動 `renderTranscript()` 的顯示
   邏輯本身，只改動它讀到的資料。這也自然滿足 AC4（未知標籤被後端靜默
   忽略後，前端只是照單全收 `segments`/`speakers` 重新渲染，不做額外
   比對、不報錯）。

3. **`renameSpeaker()`（既有、純前端即時預覽）保持不動，不與
   `submitSpeakerNames()`（呼叫後端）合併成同一個函式。**
   理由：兩者職責不同——前者是輸入框 `onchange` 的即時本地預覽（AC1／AC3
   要求「不送出仍可正常使用」），後者是「送出」按鈕觸發的明確送出動作
   （AC2）。合併會讓每次 keystroke／blur 都打 API，且無法滿足 AC3
   「未點擊送出，標籤維持原始 AI 標籤」（因為 API 呼叫才是姓名真正生效的
   時機）。

4. **Word/PDF 匯出（`exportServerFile()`，呼叫既有 `/api/export/{job_id}`）
   不需要任何前端改動即可自動滿足 AC2 的「匯出檔案使用新姓名」**，因為
   `/api/speaker-names` 已經把新姓名寫回後端 job store 的 `segments`，
   `/api/export` 讀的就是同一份 job 資料。Markdown／純文字匯出
   （`exportMarkdown()`/`exportPlainText()`，前端組字串）則依賴決策 2 的
   `state.segments` 更新才會反映新姓名，因為這兩個匯出路徑完全不打
   API、只讀前端 state。

5. **送出按鈕不做「至少填寫一位講者才能點擊」的前端驗證**，允許
   `speaker_names` 為空物件送出。理由：spec 沒有定義這個邊界情況的產品
   行為（是否要 disable 按鈕、要不要提示「請至少輸入一位」），依
   CONSTITUTION.md 範圍紀律「需求不明確時列為 open question，不可用合理
   猜測補上」；但這裡後端本身能安全處理空 dict（等同無操作、200 回傳原
   segments），不會報錯或破壞資料，所以不視為需要人類決策的阻斷點，僅在
   下方開放問題列出供之後視情況決定 UX 是否要加提示。

## 開放設計問題（定稿時必須為空）
無。（見決策 5：空白送出的 UX 細化留待未來視需要再開故事，不影響本 Story
verifiable 的驗收條件，故不列為阻斷本設計定稿的開放問題。）
