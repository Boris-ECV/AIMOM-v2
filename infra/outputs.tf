output "api_invoke_url" {
  description = "API Gateway 端點，作為前端 API base URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_app_client_id" {
  description = "Cognito App Client ID"
  value       = aws_cognito_user_pool_client.app.id
}

output "cognito_hosted_ui_domain" {
  description = "Cognito Hosted UI 網域（登入頁面）"
  value       = "${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "audio_bucket_name" {
  description = "音檔暫存 S3 bucket 名稱"
  value       = aws_s3_bucket.audio.bucket
}

output "frontend_bucket_name" {
  description = "前端靜態網站 S3 bucket 名稱"
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_cloudfront_domain" {
  description = "前端 CloudFront 網域"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "前端 CloudFront distribution ID"
  value       = aws_cloudfront_distribution.frontend.id
}

output "dynamodb_meetings_table" {
  description = "Meetings DynamoDB 表名稱"
  value       = aws_dynamodb_table.meetings.name
}

output "dynamodb_llm_usage_table" {
  description = "LLMUsage DynamoDB 表名稱"
  value       = aws_dynamodb_table.llm_usage.name
}

output "dynamodb_jobs_table" {
  description = "Jobs DynamoDB 表名稱（TASK-016 非同步轉錄作業狀態）"
  value       = aws_dynamodb_table.jobs.name
}
