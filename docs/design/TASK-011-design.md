# TASK-011 系統設計 — 管理者成本/用量儀表板

## 架構說明

新增 `src/usage.py` 封裝 DynamoDB `LLMUsage` 表的寫入與彙總查詢；`summarize.py` 於每次 LLM 呼叫後
呼叫 `record_llm_usage()` 寫入一筆用量紀錄。新增 `src/admin.py` 提供僅 `role=admin` 可存取的
彙總查詢端點，供未來前端管理者儀表板頁籤使用。

## 成本估算表（每百萬 tokens，美元）

沿用先前討論的定價（寫死於 `usage.py` 常數，未來調整價格只需改此表）：

| engine | model | input | output |
|--------|-------|-------|--------|
| github-models / openai | gpt-4o | $2.50 | $10.00 |
| groq | llama-3.3-70b-versatile | $0.59 | $0.79 |
| groq | gpt-oss-120b | $0.15 | $0.60 |
| groq | llama-3.1-8b-instant | $0.05 | $0.08 |
| bedrock-proxy | mistral.mistral-large-3-675b-instruct | 依 proxy 計費方案 | 依 proxy 計費方案 |
| gemini | gemini-2.0-flash | $0.25 | $1.50 |
| gemini | gemini-1.5-pro | $1.50 | $9.00 |

找不到對應價格時，估算成本回傳 `None`（前端顯示「未知」，不阻擋功能）。
Bedrock proxy 的實際計費目前由外部 proxy 服務決定，`usage.py` 先以 `None` 處理，不影響摘要主流程。

## DB Schema

```
Table: LLMUsage (config.DYNAMODB_LLM_USAGE_TABLE)
  PK: date (S, YYYY-MM-DD)
  SK: usage_id (S, uuid)
  屬性: engine, model, input_tokens, output_tokens, estimated_cost (N), user_id, meeting_id (job_id), created_at
```

## 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/admin/usage` | 僅管理者，回傳依日期彙總的用量與成本，及依使用者彙總 |

## 前端

新增「管理者儀表板」頁籤，僅 `role=admin` 登入者可見；顯示彙總表格。
