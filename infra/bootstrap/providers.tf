terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # 這個 bootstrap 模組本身不使用 remote backend（雞生蛋問題：backend bucket 要先被建立出來）
  # 因此維持 local state，state 檔請自行妥善保管（例如放在私有的密碼管理工具或加密備份）
}

provider "aws" {
  region = var.aws_region
}
