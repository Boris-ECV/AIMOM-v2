# DynamoDB — Meetings 表（TASK-009）：使用者歷史紀錄，14 天 TTL 自動過期
resource "aws_dynamodb_table" "meetings" {
  name         = "${local.name_prefix}-meetings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "meeting_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "meeting_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# DynamoDB — LLMUsage 表（TASK-011）：LLM 呼叫用量與成本紀錄
resource "aws_dynamodb_table" "llm_usage" {
  name         = "${local.name_prefix}-llm-usage"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "date"
  range_key    = "usage_id"

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "usage_id"
    type = "S"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# DynamoDB — Jobs 表（TASK-016）：非同步轉錄/摘要作業狀態，取代本機 /tmp 的
# meta.json/status.json/transcript.json/minutes.json，讓任何 Lambda container
# 都能讀到最新進度（/api/transcribe 改為非同步後，後續 /api/status 輪詢不保證
# 落在同一個 container）。TTL 6 小時，足夠涵蓋長會議轉錄+摘要+匯出的作業時間
resource "aws_dynamodb_table" "jobs" {
  name         = "${local.name_prefix}-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
