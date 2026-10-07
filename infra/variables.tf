variable "aws_region" {
  description = "AWS region 部署位置"
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "資源名稱前綴，用於區分環境/專案"
  type        = string
  default     = "aimom"
}

variable "environment" {
  description = "環境名稱（dev/staging/prod），會附加在資源名稱後"
  type        = string
  default     = "dev"
}

variable "meeting_retention_days" {
  description = "會議紀錄保留天數（DynamoDB TTL 使用）"
  type        = number
  default     = 14
}

variable "admin_emails" {
  description = "管理者 email 白名單，逗號分隔"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth Client ID（Cognito 聯合登入用）"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth Client Secret（Cognito 聯合登入用）"
  type        = string
  sensitive   = true
}

variable "frontend_callback_urls" {
  description = "Cognito App Client 允許的登入後導回網址清單（前端網址）"
  type        = list(string)
  default     = ["http://localhost:5500"]
}

variable "frontend_logout_urls" {
  description = "Cognito App Client 允許的登出後導回網址清單"
  type        = list(string)
  default     = ["http://localhost:5500"]
}

variable "llm_engine" {
  description = "LLM_ENGINE 環境變數：github-models / openai-gpt4o / groq / gemini / bedrock-proxy"
  type        = string
  default     = "bedrock-proxy"
}

variable "llm_model" {
  description = "覆寫預設 LLM 模型名稱，留空則依 llm_engine 使用預設值"
  type        = string
  default     = ""
}

variable "github_token" {
  description = "GitHub Models PAT（LLM_ENGINE=github-models 時使用）"
  type        = string
  default     = ""
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API Key（LLM_ENGINE=openai-gpt4o 時使用）"
  type        = string
  default     = ""
  sensitive   = true
}

variable "groq_api_key" {
  description = "Groq API Key（LLM_ENGINE=groq 時使用）"
  type        = string
  default     = ""
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Gemini API Key（LLM_ENGINE=gemini 時使用）"
  type        = string
  default     = ""
  sensitive   = true
}

variable "bedrock_proxy_base_url" {
  description = "Bedrock proxy base URL（LLM_ENGINE=bedrock-proxy 時使用）"
  type        = string
  default     = ""
  sensitive   = true
}

variable "bedrock_proxy_api_key" {
  description = "Bedrock proxy API key（LLM_ENGINE=bedrock-proxy 時使用）"
  type        = string
  default     = ""
  sensitive   = true
}

variable "assemblyai_api_key" {
  description = "AssemblyAI API Key（轉譯服務）"
  type        = string
  default     = ""
  sensitive   = true
}

variable "lambda_memory_size" {
  description = "Lambda 函式記憶體大小 (MB)"
  type        = number
  default     = 1024
}

variable "lambda_timeout" {
  description = "Lambda 函式逾時秒數"
  type        = number
  default     = 30
}
