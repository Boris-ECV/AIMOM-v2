# 設計文件 — SDLCAIP2-22 AssemblyAI 轉錄成本估算

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-22，`docs/PRD.md` 同名段落）。轉錄完成時依
`duration_sec` 與目前 `ASSEMBLYAI_MODEL` / `ASSEMBLYAI_SPEAKER_DIARIZATION`
設定估算轉錄成本，寫入一筆可與既有 LLM 用量紀錄區分的用量紀錄；
`/admin/usage` 同時顯示 transcription／summarization 兩種小計與合計。
範圍外：其他 add-ons 定價、即時串流計費、歷史轉錄補記成本、定價表外部
設定檔化（沿用 ticket 原文範圍外清單）。

## 介面/API 契約

不新增端點。變更既有 `GET /admin/usage` 的回傳內容（狀態碼不變，仍是
`require_admin` 保護下的 200）：

```jsonc
{
  "by_date": [ ... ],   // 既有欄位，形狀不變（跨 service 合併彙總）
  "by_user": [ ... ],   // 既有欄位，形狀不變（跨 service 合併彙總）
  "by_service": {
    "transcription":  {"calls": 3, "estimated_cost": 0.51},
    "summarization":  {"calls": 5, "estimated_cost": 0.02}
  },
  "total_calls": 8,
  "total_estimated_cost": 0.53   // 兩個 service 小計之和
}
```

- `by_service.<service>.estimated_cost`：該 service 下所有 `estimated_cost`
  非 None 紀錄的加總（`pricing_unavailable=true` 的紀錄 `estimated_cost`
  為 None，加總時貢獻 0，不視為「花費 0 元」而是「這筆不計入」——
  與現有 `summarize_usage()` 對 None 的處理方式一致，見下方技術決策 1）。
- `by_date` / `by_user` 既有結構刻意不拆分 service（AC3 只要求「分別列出
  transcription 與 summarization 的小計成本」，沒有要求依日期/使用者也拆
  service；依範圍紀律不多做）。

`/api/transcribe`、`/api/status/{job_id}`、`/api/upload`、
`/api/upload/complete` 對外回應格式（`StatusResponse`／`UploadResponse`）
不變，本story不新增/修改回應欄位。

## 資料模型

### Jobs 表（`jobstore.py`，既有表，新增欄位）

寫入 `data` JSON blob 內的新欄位（沿用既有「打包成 JSON 字串」形狀）：

| 欄位 | 寫入時機 | 說明 |
|---|---|---|
| `user_id` | `upload.py` 的 `_finalize_upload()` → `jobstore.create_job()` | job 擁有者 email，見技術決策 2 |
| `assemblyai_model` | `transcribe.py` 的 `/transcribe` 送出時 | 送出當下的 `config.ASSEMBLYAI_MODEL`，見技術決策 3 |
| `assemblyai_diarization_enabled` | 同上 | 送出當下的 `config.ASSEMBLYAI_SPEAKER_DIARIZATION` |

新增一個**頂層**（非 JSON blob 內）DynamoDB attribute：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `finalize_claimed` | Bool | 冪等鎖，見技術決策 4。刻意放在頂層而非 `data` 內，因為 `data` 是單一字串屬性，`ConditionExpression` 無法對字串內的 JSON 欄位做條件判斷，只能對真正的 DynamoDB attribute 判斷 |

### LLMUsage 表（`usage.py`，既有表，重新詮釋為「用量表」，新增欄位）

沿用既有 `record_llm_usage()` 寫入的表（`config.DYNAMODB_LLM_USAGE_TABLE`），
新增一個判別欄位與轉錄專屬欄位：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `service` | `"transcription"` \| `"summarization"` | 新增判別欄位。**既有舊紀錄沒有這個欄位**，讀取時視為 `"summarization"`（向下相容，比照 SDLCAIP2-21 對 `pricing_unavailable` 舊資料的處理方式），見技術決策 1 |
| `duration_sec` | number \| null | 僅 transcription 紀錄有值 |
| `diarization_enabled` | bool | 僅 transcription 紀錄有值 |
| `pricing_unavailable` | bool | 沿用 SDLCAIP2-21 的欄位名稱與語意（定價表查無對應組合，或 `duration_sec` 缺失時皆標記為 true） |

`estimated_cost`／`user_id`／`meeting_id`／`date`／`usage_id`／`created_at`
沿用既有欄位語意；transcription 紀錄的 `engine` 固定填 `"assemblyai"`，
`model` 填當時的 `assemblyai_model`。`input_tokens`／`output_tokens`
對 transcription 紀錄無意義，寫入 0（維持既有表 schema 一致，不為了
這個 service 另開一張表——見技術決策 5）。

## 關鍵技術決策

1. **AC4 逐字矛盾（「不寫入…並標記 pricing_unavailable=true」）：採用寫入一筆
   `estimated_cost=None, pricing_unavailable=true` 的紀錄，而非真的不寫。**
   理由：`pricing_unavailable=true` 這個標記若沒有對應的紀錄可以掛，語意上
   無法成立；比照 AC2「查無定價」情境的處理方式（同樣是寫入但標記不可用），
   讓「定價缺漏」與「時長缺漏」兩種不可估算的情境在資料模型上有一致的
   表示方式，管理者儀表板未來要顯示「有多少筆成本無法估算」時也只需處理
   一種情況。這是規格沒講清楚、但架構師職責內必須裁示的技術決策
   （橘子色風險註記 #2），已在此明確記錄，不留待 Refining。

2. **`user_id` 在 `upload.py` 建立 job 時就寫入 job 記錄，而非在
   `progress.py` 完成收尾時才取得。**
   `/upload`、`/upload/complete` 兩個端點加上
   `user: CurrentUser = Depends(get_current_user)` 參數（原本router層級
   `dependencies=_auth_dep` 已強制驗證，這裡只是把已存在的身分「取出來用」，
   不改變驗證行為），把 `user.email` 一併傳入 `jobstore.create_job()`。
   理由：job 的擁有者語意上應該是「上傳音檔的人」，而不是「輪詢
   `/api/status` 時剛好是誰在打」——後者理論上任何持有 `job_id` 且通過
   驗證的使用者都能觸發（沒有 job 層級的存取控管，這是既有行為，本story
   不擴大範圍去改），若在輪詢當下才取身分，`user_id` 會隨機取決於「誰先
   輪詢到轉錄完成的那一刻」，語意錯誤且不可重現。解決風險註記 #1。

3. **轉錄用的 `assemblyai_model`／`assemblyai_diarization_enabled` 在
   `/transcribe` 送出當下寫入 job 記錄，完成收尾時讀這兩個欄位算成本，
   而非在收尾當下直接讀當前的 `config.*`。**
   理由：`config.ASSEMBLYAI_MODEL`／`ASSEMBLYAI_SPEAKER_DIARIZATION` 是
   process 等級環境變數，理論上可能在轉錄送出後、完成前被改變（例如
   Lambda 冷啟動抓到新的環境變數版本、或人工調整設定）；把「送出時實際
   使用的設定」釘在 job 記錄上，成本估算才會對應「這次轉錄真正用的組合」，
   而不是「收尾當下恰好生效的設定」。舊 job（本story上線前已在
   `transcribing` 狀態、沒有這兩個欄位的資料）在完成收尾時退回讀取當下
   `config.*` 當作 fallback，避免這批舊 job 因為缺欄位而永遠
   `pricing_unavailable`。

4. **併發鎖用獨立頂層 DynamoDB attribute `finalize_claimed` +
   `ConditionExpression`，而非在既有 `jobstore.update_job()` 的
   get-then-put 模式上加判斷。**
   風險註記 #3 指出 `_finalize_if_transcription_done()` 的
   `job.get("stage") != "transcribing"` 檢查與後續寫入之間沒有原子性，
   ~2 秒輪詢下可能兩個併發 `/api/status` 請求都通過檢查、各自完整跑一次
   組裝＋記費。既有 `jobstore` 把整個 job 打包成單一 `data` JSON 字串存放，
   DynamoDB 的 `ConditionExpression` 無法對字串內的巢狀欄位做條件判斷，
   所以無法直接對 `data.stage` 加鎖；改為新增一個**頂層**、獨立於 `data`
   之外的 `finalize_claimed` attribute，用
   `UpdateExpression="SET finalize_claimed = :true"` +
   `ConditionExpression="attribute_not_exists(finalize_claimed)"`
   讓 DynamoDB 保證只有第一個呼叫端能成功寫入這個 attribute（第二個會收到
   `ConditionalCheckFailedException`，視為「已被搶走，直接回傳目前狀態」）。
   只在 AssemblyAI 回報 `completed`、即將真正寫入 segments／記費之前才
   呼叫這把鎖，避免「還在處理中」的多次輪詢無謂觸碰這個 attribute。
   這是技術健全性措施（既有 race 本來無害，記費後才變得可見），非產品
   決策，依橘子色風險註記 #3 屬於架構師可自行決定的範圍。

5. **轉錄成本沿用既有 `DYNAMODB_LLM_USAGE_TABLE` 這張表，不另開新表。**
   理由：`/admin/usage` 需要「合計」兩種 service 的成本，同表 `scan()`
   一次就能拿到全部資料，`summarize_usage()` 改動也最小；符合 CONSTITUTION.md
   「避免不必要的抽象層」，沒有明顯理由需要為單一新 service 另開一張表。
   代價是 `input_tokens`/`output_tokens` 對 transcription 紀錄無意義，
   固定填 0（不用 None，避免既有 `summarize_usage()` 對這兩個欄位做
   `i.get("input_tokens", 0)` 加總時要多處理 None 的情況）。

6. **轉錄成本記錄失敗（例如 DynamoDB 短暫錯誤）比照
   `summarize.py` 既有 `record_llm_usage` 呼叫方式，用
   `try/except Exception: pass` 包住，不阻擋 `/api/status` 回應。**
   理由：延續 CONSTITUTION.md「失敗處理哲學」與既有程式碼慣例——用量記錄是
   附帶效果，不應該讓使用者看不到轉錄結果；與 `summarize.py:193-204`
   完全同構，維持同一份程式庫內同類情境一致的錯誤處理形狀。

7. **AssemblyAI 定價表比照既有 `PRICING_PER_MILLION_TOKENS` 的「程式碼內
   dict」形狀，新增 `PRICING_ASSEMBLYAI_PER_HOUR`，鍵為
   `(model, diarization_enabled)`：**
   ```python
   PRICING_ASSEMBLYAI_PER_HOUR = {
       ("universal-2", False): 0.15,
       ("universal-2", True): 0.17,  # 0.15 (universal-2) + 0.02 (diarization add-on)
   }
   ```
   找不到對應組合回傳 `None`（沿用 `estimate_cost()` 既有「查無定價回
   None」慣例）。範圍外聲明已明確排除「定價表外部設定檔化」，故不做成
   環境變數或設定檔。

## 開放設計問題（定稿時必須為空）
無。風險註記列出的三個問題（`user_id` 取得時機、AC4 矛盾、併發記費競態）
均已在上方「關鍵技術決策」1、2、4 中裁示並記錄理由，未發現規格本身無法
從既有程式碼/spec 推導出的其餘產品決策。
