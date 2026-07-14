# Terraform State 儲存桶（僅執行一次，供主要 infra/ 的 backend "s3" 使用）
#
# 加上隨機後綴避免 bucket 名稱全域衝突（S3 bucket 名稱需全域唯一）
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "tf_state" {
  bucket = "${var.project_name}-tf-state-${random_id.suffix.hex}"

  # 防止不小心用 terraform destroy 誤刪 state bucket
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Project   = var.project_name
    Purpose   = "terraform-state"
    ManagedBy = "terraform-bootstrap"
  }
}

# 版本控制：state 檔案的歷史版本可還原，避免誤寫壞掉的 state 造成資料遺失
resource "aws_s3_bucket_versioning" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
