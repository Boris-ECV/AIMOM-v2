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

data "archive_file" "lambda_layer" {
  type        = "zip"
  source_dir  = "${path.module}/layer"
  output_path = "${path.module}/build/aimom-lambda-layer.zip"
}

resource "aws_lambda_layer_version" "deps" {
  layer_name          = "${local.name_prefix}-deps"
  filename            = data.archive_file.lambda_layer.output_path
  source_code_hash    = data.archive_file.lambda_layer.output_base64sha256
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
      ASSEMBLYAI_API_KEY        = var.assemblyai_api_key
      COGNITO_REGION            = var.aws_region
      COGNITO_USER_POOL_ID      = aws_cognito_user_pool.main.id
      COGNITO_APP_CLIENT_ID     = aws_cognito_user_pool_client.app.id
      ADMIN_EMAILS              = var.admin_emails
      DYNAMODB_MEETINGS_TABLE   = aws_dynamodb_table.meetings.name
      DYNAMODB_LLM_USAGE_TABLE  = aws_dynamodb_table.llm_usage.name
      MEETING_RETENTION_DAYS    = tostring(var.meeting_retention_days)
      TMP_DIR                   = "/tmp"
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
