# Cognito User Pool + Google 聯合登入（TASK-008）
resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-users"

  username_attributes     = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${local.name_prefix}-auth"
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_cognito_identity_provider" "google" {
  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id        = var.google_client_id
    client_secret     = var.google_client_secret
    authorize_scopes = "openid email profile"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
  }
}

resource "aws_cognito_user_pool_client" "app" {
  name         = "${local.name_prefix}-app-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # SPA（前端）使用 Authorization Code + PKCE，不需要 client secret
  generate_secret = false

  supported_identity_providers = [aws_cognito_identity_provider.google.provider_name]

  allowed_oauth_flows                 = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                = ["openid", "email", "profile"]

  callback_urls = var.frontend_callback_urls
  logout_urls   = var.frontend_logout_urls

  explicit_auth_flows = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]

  depends_on = [aws_cognito_identity_provider.google]
}
