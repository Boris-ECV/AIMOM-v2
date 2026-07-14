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
