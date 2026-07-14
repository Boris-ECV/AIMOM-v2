output "state_bucket_name" {
  description = "State bucket 名稱，填入主要 infra/ backend 設定的 bucket 參數"
  value       = aws_s3_bucket.tf_state.bucket
}

output "state_bucket_region" {
  description = "State bucket 所在 region"
  value       = var.aws_region
}
