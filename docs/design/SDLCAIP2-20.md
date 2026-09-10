# 設計文件 — SDLCAIP2-20 轉錄後講者姓名對應 API（後端）

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-20）。核心行為：轉錄完成後，使用者可
呼叫新 API 提交「講者標籤 → 姓名」對應（自由輸入文字，含非團隊成員），
job 的 `segments` 中對應標籤的 `speaker` 欄位就地改為指定姓名；未提交
對應的標籤維持原標籤；之後呼叫 `/summarize` 時 LLM 讀到的即是改名後的
`speaker` 值。job 未完成轉錄時回傳 400；提交的標籤若 job 內不存在則靜默
忽略該筆，其餘正常套用。範圍外：跨會議聲紋辨識／記憶身份、已保留歷史
會議改名、segment 級重新歸屬。

## 介面/API 契約

### `POST /api/speaker-names`（新端點，新檔案 `src/speaker_names.py`）

沿用 `diarize.py` 的路由/錯誤處理慣例（同一種「job 未完成轉錄」400 判斷
式），並掛在 `app.py` 既有 `_auth_dep`（`Depends(get_current_user)`）分組
下，不需額外驗證程式碼（CONSTITUTION 安全預設）。

**Request（新 model `SpeakerNamesRequest`）**
```json
{
  "job_id": "string",
  "speaker_names": { "SPEAKER_A": "王小明" }
}
```
- `speaker_names`：`dict[str, str]`，key 為講者標籤、value 為自由輸入的
  姓名字串（不限團隊成員白名單，前端不做下拉選單，後端也不驗證是否為
  已知使用者——spec 明確要求「非下拉選單」）。

**Response（新 model `SpeakerNamesResponse`，形狀比照 `DiarizeResponse`）**
```json
{
  "job_id": "string",
  "speakers": ["王小明", "SPEAKER_B"],
  "segments": [ { "start": 0.0, "end": 1.2, "text": "...", "speaker": "王小明" } ]
}
```
- `speakers`：套用對應後、依目前 segments 實際出現的 speaker 值去重排序
  的清單（沿用 `diarize.py` 現有 `sorted(set(...))` 邏輯）。
- `segments`：套用對應後的完整 segments（與 `/transcript/{job_id}`、
  `/diarize` 回傳的 `Segment` 結構相同）。

**狀態碼**
- `200`：成功，回傳 `SpeakerNamesResponse`（即使 `speaker_names` 為空
  dict 或全部標籤都不存在，也視為成功，仍回傳目前 segments 現狀）。
- `400`：`job is None or job.get("segments") is None`（job 不存在或尚未
  完成轉錄），訊息沿用 `diarize.py` 既有文字「請先執行 /transcribe 並
  等待轉錄完成」，與既有端點一致，不另外分辨「job 不存在」與「轉錄未
  完成」兩種情況（`diarize.py` 現行行為即是如此，維持一致）。
- 提交的標籤在 job 內不存在：**不是錯誤**，靜默忽略該筆，其餘正常套用
  （AC5 明確要求）——不回傳 400，也不在 response 內额外標示「哪些標籤
  被忽略」（spec 未要求）。

### 對 `/summarize`（`src/summarize.py`）：無程式碼變更
`_build_transcript_text()` 已經是直接讀 `seg.get("speaker")` 組逐字稿
文字餵給 LLM（`src/summarize.py:43-48`），本 Story 只要 segments 的
`speaker` 欄位已經是改名後的姓名，`/summarize` 不需任何修改即可自然
反映新姓名於 `meeting_info.participants`／`action_items.owner`（AC3）
——這點已對照 `summarize.py` 原始碼確認。

## 資料模型
無新增資料表／索引。沿用 `jobstore` 既有「整包 JSON 存在單一 `data`
attribute」模式：讀出 `job["segments"]`，對每個 segment 的 `speaker`
欄位依 `speaker_names` 對應表就地覆寫（存在對應者覆寫、不存在者維持
原樣），再以 `jobstore.update_job(job_id, segments=updated_segments)`
整批寫回。不新增欄位記錄「原始標籤」或「對應表本身」——spec 三個情境
都只要求 segments 的最終呈現值，未要求保留可逆的原始標籤或稽核紀錄，
依 CONSTITUTION「範圍紀律」不擴大範圍。

## 關鍵技術決策

1. **新增獨立檔案 `src/speaker_names.py` + 獨立 `APIRouter`，不併入
   `diarize.py`。** 沿用 CONSTITUTION 程式碼風格「模組化路由：每個功能
   一個檔案」慣例；雖然此功能操作同一批 segments，但語意（人工姓名對應
   輸入）與 `diarize.py`（讀取既有 AssemblyAI 講者標籤）不同，比照
   `upload.py`/`transcribe.py`/`summarize.py` 各自成檔的既有先例。

2. **姓名覆寫直接就地修改 `speaker` 欄位值，不新增額外欄位保存映射
   表或原始標籤。** AC1/AC2 只描述「segments 的 speaker 欄位改為姓名」
   這個最終狀態；spec 範圍外明確排除「segment 重新歸屬」與「歷史會議
   改名」，代表本 Story 不需要支援日後撤銷/重新對應到不同姓名時還原
   原始標籤的能力。若之後需要，屬於未來 Story 的範圍（不預先設計，依
   CONSTITUTION「避免不必要的抽象層」）。

3. **未知標籤（job 內不存在的 key）用「過濾後套用」而非「驗證後 400」
   處理，具體實作：以 job 目前 segments 中出現過的 speaker 值集合，對
   `speaker_names` 的 key 做交集，只套用交集內的對應。** AC5 明文要求
   忽略不存在的標籤且不可報錯，這是 spec 已經做出的明確產品決策，非
   本設計自行判斷；用集合交集是最直接、無額外狀態的作法。

4. **`job` 未完成轉錄的判斷式沿用 `diarize.py` 逐字：`job is None or
   job.get("segments") is None` → 400。** 與既有同類端點（`diarize.py`）
   保持一致的失敗語意與訊息文字，讓前端/測試對「未完成轉錄」情境的
   錯誤處理可以共用同一段判斷邏輯與期待訊息，不節外生枝發明新的錯誤
   分類。

5. **`speaker_names` 為空 dict、或全部 key 都不存在時，仍回傳 200
   （而非 400）。** AC5 的情境本質上就是「全部或部分標籤不存在」的
   特例，spec 描述的行為是「忽略、不報錯、其餘正常套用」，延伸到「一筆
   都不套用」的邊界也應是 200＋原樣 segments，維持行為一致性，不是
   自行新增規則。

## 開放設計問題（定稿時必須為空）
無。
