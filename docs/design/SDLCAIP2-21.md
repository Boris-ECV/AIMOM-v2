# 設計文件 — SDLCAIP2-21 管理者儀表板 LLM 成本彙總正確反映 bedrock-proxy 成本、定價缺漏明確標示

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-21），四個 Gherkin 情境：(1) 補上
`bedrock-proxy` / `mistral.mistral-large-3-675b-instruct` 定價後
`estimated_cost` 正確非 0；(2) 查無定價的紀錄新增 `pricing_unavailable=true`
且 `estimated_cost` 維持 `None`（不落地為 0）；(3) `/admin/usage` 回傳
`pricing_unavailable_count` 與涉及的 `(engine, model)` 清單，且
`total_estimated_cost` 明確排除這些紀錄；(4) 舊資料沒有
`pricing_unavailable` 欄位時視為 `false`，維持相容不拋錯。

G1 gate report 已訂正 ticket 背景的誤植：實際靜默補 0 的位置是
`summarize_usage()`（`src/usage.py:119` 與 `:139` 的 `or 0`），不是
`record_llm_usage()`——`record_llm_usage()` 目前已正確把缺定價的成本存成
`None`（`src/usage.py:104`）。本設計依真實根因（`summarize_usage()`）修正，
`record_llm_usage()` 只需新增 `pricing_unavailable` 欄位本身。

## 介面/API 契約
`GET /admin/usage`（`src/admin.py`，既有端點，無新增/變更路由或狀態碼）
回傳 JSON 新增兩個頂層欄位，其餘既有欄位形狀不變：

```jsonc
{
  "by_date": [ { "date": "...", "input_tokens": 0, "output_tokens": 0,
                 "estimated_cost": 0.0, "calls": 0 }, ... ],
  "by_user": [ { "user_id": "...", "input_tokens": 0, "output_tokens": 0,
                 "estimated_cost": 0.0, "calls": 0 }, ... ],
  "total_calls": 0,
  "total_estimated_cost": 0.0,          // 明確排除 pricing_unavailable 紀錄
  "pricing_unavailable_count": 0,        // 新增：查無定價的紀錄筆數
  "pricing_unavailable_engines": [       // 新增：涉及的 (engine, model)，去重、排序
    { "engine": "...", "model": "..." }
  ]
}
```

`record_llm_usage()`（非 HTTP 介面，`summarize.py` 內部呼叫）回傳 dict
新增一個既有 boolean 欄位 `pricing_unavailable`，其餘欄位不變：

```jsonc
{
  "date": "...", "usage_id": "...", "engine": "...", "model": "...",
  "input_tokens": 0, "output_tokens": 0,
  "estimated_cost": null,          // 查無定價時維持 None，不再是 0
  "pricing_unavailable": true,     // 新增
  "user_id": "...", "meeting_id": "...", "created_at": "..."
}
```

## 資料模型
DynamoDB `LLMUsage` 表（`config.DYNAMODB_LLM_USAGE_TABLE`，既有表，不變更
key schema）新增一個 item 屬性：

- `pricing_unavailable` (Bool)：`estimate_cost()` 回傳 `None` 時為
  `true`，否則為 `false`。DynamoDB 原生支援 Bool 型別，`record_llm_usage()`
  可直接把這個布林值放進 `dynamo_item`（不需要像 `estimated_cost` 那樣轉
  `Decimal`）。
- 舊資料（本欄位新增前寫入的 item）沒有這個屬性；`summarize_usage()` 讀取時
  用 `i.get("pricing_unavailable", False)` 取得，預設 `false`，對應 AC4
  「視為 pricing_unavailable=false，沿用原本 estimated_cost 數字」。

`PRICING_PER_MILLION_TOKENS`（`src/usage.py:18`）新增一筆：

```python
("bedrock-proxy", "mistral.mistral-large-3-675b-instruct"): (0.50, 1.50),
```

（換算自 $0.0005/1K input tokens → $0.50/1M；$0.0015/1K output tokens →
$1.50/1M，與 AC1 給定數字一致。）

## 關鍵技術決策

1. **修法定位在 `summarize_usage()`，不動 `record_llm_usage()` 的成本計算
   邏輯**——`estimate_cost()` 與既有的 `None` 寫入行為（`usage.py:104`）本來
   就正確；唯一要動的是讀取彙總時把 `None`（查無定價）跟合法的 `0.0`
   （定價存在但用量為 0 導致算出 0 元）分開處理，這正是 G1 gate report
   訂正過的根因位置。

2. **`record_llm_usage()` 只新增 `pricing_unavailable` 欄位，用
   `cost is None` 直接推導**，不另外重算一次「查表是否命中」——避免兩處
   邏輯各自判斷、日後定價表擴充時只改一處就好（`estimate_cost()` 回傳
   `None` 即代表查無定價，單一事實來源）。

3. **`summarize_usage()` 判斷「排除」用 `i.get("pricing_unavailable",
   False)`，不是用 `i.get("estimated_cost") is None`**——理由是 AC4 明確
   要求舊資料（沒有這個新欄位）視為 `false` 且「沿用原本 estimated_cost
   數字」；若改用 `estimated_cost is None` 判斷，邏輯上等價於本故事的新資料，
   但用專門欄位判斷語意更直接對應 AC2/AC4 的措辭，且未來若欄位語意需要調整
   （例如某天定價恢復但仍想暫時排除）不會綁死在 `estimated_cost` 的值。

4. **`by_date`/`by_user` 的 `estimated_cost` 加總比照 `total_estimated_cost`
   一併排除 `pricing_unavailable` 的紀錄**（原本兩處都是同一個 `or 0`
   pattern 的變形），維持同一支函式內部一致的「不把缺定價的紀錄靜默算成
   0」邏輯，避免 `total_estimated_cost` 排除了、但 `by_date`/`by_user` 卻仍
   把它當 0 拉低平均這種同函式內自相矛盾的情況。`calls` 計數不受影響（每筆
   紀錄，不論定價是否可得，都算一次呼叫——這是既有行為，AC 沒有要求改變）。
   `by_date`/`by_user` 不新增 `pricing_unavailable_count` 逐組欄位，因為
   AC3 只要求 `/admin/usage` 頂層有這個彙總，逐組拆分是規格沒要求的延伸，
   依範圍紀律不做。

5. **`pricing_unavailable_engines` 用 list of `{engine, model}` dict、依
   `(engine, model)` 去重並排序**（用 `sorted(set(...))`），不是 list of
   tuple 或字串串接——JSON 序列化 tuple 會變 list 語意不明確，dict 形式
   讓前端不用猜欄位順序；排序讓回應具決定性（deterministic），方便前端/
   測試斷言。

## 開放設計問題(定稿時必須為空)
無。
