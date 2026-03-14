module "secrets" {
  source = "hashicorp/aws"

  secrets = [
    {
      name                    = "${local.name_prefix}/api-keys"
      description             = "API keys for AI Foundation services"
      recovery_window_in_days = 7
      kms_key_id              = var.secrets_kms_key_arn
      secret_key_value = {
        placeholder = "UPDATE_ME_AFTER_DEPLOYMENT"
      }
      secret_value_unmanaged = true
    },
    {
      name                    = "${local.name_prefix}/bedrock-config"
      description             = "Bedrock configuration and guardrail settings"
      recovery_window_in_days = 7
      kms_key_id              = var.secrets_kms_key_arn
      secret_key_value = {
        placeholder = "UPDATE_ME_AFTER_DEPLOYMENT"
      }
      secret_value_unmanaged = true
    },
    {
      name                    = "${local.name_prefix}/app-secrets"
      description             = "Application-level secrets"
      recovery_window_in_days = 7
      kms_key_id              = var.secrets_kms_key_arn
      secret_key_value = {
        placeholder = "UPDATE_ME_AFTER_DEPLOYMENT"
      }
      secret_value_unmanaged = true
    }
  ]

  tags = {
    Name = "${local.name_prefix}-secrets"
  }
}
