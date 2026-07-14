variable "aws_region" {
  description = "AWS region 部署位置，需與主要 infra/ 使用的 region 一致"
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "資源名稱前綴，需與主要 infra/ 使用的 project_name 一致"
  type        = string
  default     = "aimom"
}
