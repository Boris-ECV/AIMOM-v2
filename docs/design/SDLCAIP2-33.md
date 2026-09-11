# 設計文件 — SDLCAIP2-33 轉錄語言改用 AssemblyAI 自動偵測，取代寫死的中文

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-33）。`build_transcription_config()` 移除
寫死的 `language_code="zh"`，改用 AssemblyAI `language_detection=True` 自動
偵測語言；**不**設定 `language_confidence_threshold`（避免 AssemblyAI 因低
信心直接讓整個轉錄失敗）。轉錄完成後若偵測到的語言信心
（`language_confidence`）低於門檻 0.5，於既有輪詢結果中附帶一個持續性提示
旗標，前端沿用 `#modified-badge` 的 warning 樣式常駐顯示提示訊息（非
toast），且不觸發任何重試。範圍外：重試邏輯、設定
`language_confidence_threshold`、讓使用者手動選語言、信心趨勢分析。

## 介面/API 契約

不新增端點。變更既有 `GET /api/status/{job_id}` 的回傳內容
（`StatusResponse`，狀態碼不變，仍是驗證通過下的 200）：

```jsonc
{
  "job_id": "xxx",
  "stage": "transcribed",
  "progress": 75,
  "message": "轉錄完成，共 12 段，3 位說話者",
  "low_language_confidence": true   // 新增欄位，見下方說明
}
```

- `low_language_confidence: bool`（新增，非 Optional，永遠有值）。
  - `_finalize_if_transcription_done()` 完成收尾（`stage` 從
    `transcribing` 轉為 `transcribed`）當下寫入 job 記錄一次；此後同一個
    job 的每次 `/api/status` 輪詢都會回傳同一個持久化的值（見下方資料
    模型），直到 `job` 被 `/api/cleanup/{job_id}` 刪除為止。
  - 判定規則：AssemblyAI 回傳的 `language_confidence` 有值且
    `< 0.5` 時為 `True`；`language_confidence` 為 `None`／欄位不存在，或
    `>= 0.5` 時為 `False`。
  - 舊 job（本 story 上線前已完成、job 記錄裡沒有這個欄位）讀取時預設
    `False`（見資料模型一節），對應 AC「該欄位不存在時視為信心正常、不
    顯示警示」。
  - `error` / `transcribing` / `uploaded` 等其他 `stage` 底下，此欄位固定
    回傳 `False`（尚無轉錄結果可判斷信心）。

`/api/transcribe`、`/api/upload`、`/api/upload/complete`、
`/api/transcript/{job_id}` 回應格式不變，本 story 不修改。

## 資料模型

### Jobs 表（`jobstore.py`，既有表，`data` JSON blob 內新增欄位）

| 欄位 | 型別 | 寫入時機 | 說明 |
|---|---|---|---|
| `low_language_confidence` | bool | `progress.py` 的 `_finalize_if_transcription_done()`，與 `stage="transcribed"` 同一次 `jobstore.update_job()` 呼叫寫入 | 見上方介面契約判定規則 |

不新增頂層 DynamoDB attribute、不新增資料表。舊 job 記錄沒有這個欄位；
`read_status()`／`get_status()` 讀取時一律用
`job.get("low_language_confidence", False)` 取值，向下相容既有 job，不需要
資料遷移。

## 關鍵技術決策

1. **`language_confidence` 只能透過 `transcript.json_response.get(...)`
   取得，不能用 `transcript.language_confidence`。**
   理由：SDK 高階 `Transcript` 包裝類別只公開 `.language_code`／
   `.language_codes`，不直接暴露 `.language_confidence`（見 ticket 附的
   SDK 原始碼證據 `transcriber.py:338-343`、`types.py:2402`）；本 story
   的 `_fetch_transcript_status_once()` 目前回傳的是 SDK 底層
   `api.get_transcript()` 的原始回應物件（非高階 `Transcript`），需確認
   該物件是否已含 `language_confidence` 屬性或需再包一層——實作時若
   `api.get_transcript()` 回傳型別本身就已含 `language_confidence`
   屬性，直接讀取即可；若沒有，改用 `.dict()`／等效原始 dict 存取
   `language_confidence` 鍵，理由同上：高階包裝不保證暴露這個欄位。

2. **判斷「低信心」的時機放在 `_finalize_if_transcription_done()` 组裝
   segments 之後、寫入 `stage="transcribed"` 的 `update_job()` 呼叫之前**
   （即現有函式第 96-118 行區塊，`try: usage.record_transcription_usage`
   之後、最終 `return jobstore.update_job(...)` 之前新增判斷邏輯，並在該
   `update_job()` 呼叫中新增 `low_language_confidence=...` 參數）。
   理由：這是 AssemblyAI `transcript` 物件在整個收尾流程中最後一次可用
   的時間點，沿用既有「一次性收尾、一次寫入」的形狀，不需要額外的
   DynamoDB 讀寫或狀態轉換。

3. **信心判斷讀取失敗（例如回應物件缺少該欄位、型別非預期）不可讓整個
   `/api/status` 收尾流程失敗。**
   比照 CONSTITUTION.md 失敗處理哲學「對外部依賴的呼叫用
   try/except 包住，不可讓例外無聲穿透，但也不可讓附帶判斷拖垮主流程」
   ——用 `try/except Exception` 包住 `language_confidence` 的讀取與比較，
   失敗時視同「信心正常」（`low_language_confidence=False`），因為信心
   提示是錦上添花的附帶資訊，其讀取失敗不應阻擋使用者拿到轉錄結果本身
   （行為上與既有 `usage.record_transcription_usage()` 的
   `try/except Exception: pass` 同構）。

4. **前端在 `pollStatus()` 收到的每次回應都覆寫
   `state.lowLanguageConfidence = !!s.low_language_confidence`，而非只在
   偵測到 `stage === 'transcribed'` 的那一次讀取。**
   理由：`low_language_confidence` 是持久化在 job 記錄裡的值（技術決策
   2），`/api/status` 之後每次輪詢都會回傳同一個值，不需要特別在「第一次
   偵測到 transcribed」的時機點特殊處理；用「每次都覆寫」比「只在特定
   stage 轉換時讀一次」更不容易因為未來的 stage 順序調整而漏讀。

5. **前端警示徽章沿用 `#modified-badge` 的 CSS 樣式（`background:
   #FEF3C7; color: var(--warning)`），新增獨立 DOM 元素
   `#low-confidence-badge`，不重用同一個 `#modified-badge` 元素。**
   理由：`#modified-badge` 語意已固定綁定「使用者是否手動編輯過會議紀錄」
   （`markModified()`／`exportMarkdown()`／`regenerateSummary()` 都會
   toggle 它），且其顯示文字（「● 未儲存修改」）與觸發時機（使用者編輯
   動作）與本 story 的「語言信心過低」語意完全不同、生命週期也不同（一個
   會在匯出/重新產生後被清除，一個應該持續到該次結果被清掉為止）；借用
   同一個元素會讓兩種完全獨立的狀態互相覆蓋彼此的顯示/隱藏邏輯。新增
   `#low-confidence-badge`，放在 `#modified-badge` 旁（`view-result` 的
   `.btn-row` 內），沿用相同的 class/inline style 寫法
   （`display:none` 預設隱藏，`display:inline-block` 顯示），顯示文字：
   「⚠ 偵測到的語言信心水準較低，逐字稿可能不夠準確」。顯示/隱藏邏輯放在
   `renderMinutes()`（`view-result` 顯示結果時的統一渲染入口）：讀
   `state.lowLanguageConfidence` 決定該徽章 `style.display`。

## 開放設計問題（定稿時必須為空）
無。
