terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # 使用 S3 remote backend 儲存 state（部分設定，實際 bucket/key/region 透過
  # `terraform init -backend-config=backend.hcl` 帶入，避免把 bucket 名稱寫死於程式碼）。
  # backend bucket 需先執行 `infra/bootstrap/` 建立，見 infra/README.md。
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}
