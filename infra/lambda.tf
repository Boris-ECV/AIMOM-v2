# Lambda 函式打包與部署（TASK-012 Mangum handler，TASK-014 修正：加入 Lambda Layer 打包相依套件）
#
# 相依套件透過 Lambda Layer 管理（見 infra/layer/python，由
# scripts/build_lambda_layer.ps1 產生，避免每次都重新 pip install 且與
# Lambda python3.12 x86_64 runtime 相容）。src/ 本身只放應用程式碼，
# 避免單一 function zip 過大且方便版本控管。
data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/build/aimom-lambda.zip"

  excludes = [
    "venv",
    "__pycache__",
    ".pytest_cache",
    "tests",
    "tmp",
    ".env",
    "requirements-lambda.txt",
  ]
}

# Layer zip 由 scripts/build_lambda_layer.ps1/.sh 直接產生在 infra/build/，
# 不透過 archive_file 動態壓縮 infra/layer/python。原因：在磁碟空間有限的環境
# （例如 AWS CloudShell 僅 1GB 配額）同時存放未壓縮原始檔（~80MB）與
# archive_file 另外產生的 zip 會爆掉空間；改為本機/CI 先建置好 zip 再上傳，
# CloudShell 端只需要這一個壓縮檔即可執行 terraform apply。
locals {
  lambda_layer_zip_path = "${path.module}/build/aimom-lambda-layer.zip"
}

resource "aws_lambda_layer_version" "deps" {
  layer_name          = "${local.name_prefix}-deps"
  filename            = local.lambda_layer_zip_path
  source_code_hash    = filebase64sha256(local.lambda_layer_zip_path)
  compatible_runtimes = ["python3.12"]
  compatible_architectures = ["x86_64"]
}

resource "aws_lambda_function" "api" {
  function_name    = "${local.name_prefix}-api"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_handler.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  layers           = [aws_lambda_layer_version.deps.arn]

  environment {
    variables = {
      LLM_ENGINE               = var.llm_engine
      LLM_MODEL                = var.llm_model
      GITHUB_TOKEN              = var.github_token
      OPENAI_API_KEY            = var.openai_api_key
      GROQ_API_KEY              = var.groq_api_key
      GEMINI_API_KEY            = var.gemini_api_key
      BEDROCK_PROXY_BASE_URL    = var.bedrock_proxy_base_url
      BEDROCK_PROXY_API_KEY     = var.bedrock_proxy_api_key
      ASSEMBLYAI_API_KEY        = var.assemblyai_api_key
      COGNITO_REGION            = var.aws_region
      COGNITO_USER_POOL_ID      = aws_cognito_user_pool.main.id
      COGNITO_APP_CLIENT_ID     = aws_cognito_user_pool_client.app.id
      ADMIN_EMAILS              = var.admin_emails
      DYNAMODB_MEETINGS_TABLE   = aws_dynamodb_table.meetings.name
      DYNAMODB_LLM_USAGE_TABLE  = aws_dynamodb_table.llm_usage.name
      DYNAMODB_JOBS_TABLE       = aws_dynamodb_table.jobs.name
      MEETING_RETENTION_DAYS    = tostring(var.meeting_retention_days)
      TMP_DIR                   = "/tmp"
      AUDIO_BUCKET_NAME         = aws_s3_bucket.audio.bucket
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
