data "aws_iam_policy_document" "assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

data "aws_secretsmanager_secret_version" "bedrock_config" {
  secret_id = "${local.name_prefix}/bedrock-config"
}

locals {
  bedrock_config = jsondecode(data.aws_secretsmanager_secret_version.bedrock_config.secret_string)
  sp_tenant_id   = trimspace(local.bedrock_config.SHAREPOINT_TENANT_ID)
  sp_client_id   = trimspace(local.bedrock_config.SHAREPOINT_CLIENT_ID)
  sp_client_secret = trimspace(local.bedrock_config.SHAREPOINT_CLIENT_SECRET)
}

resource "aws_iam_role" "gateway" {
  name               = "${local.name_prefix}-agentcore-gateway-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = { Name = "${local.name_prefix}-agentcore-gateway-role" }
}

resource "aws_iam_role" "agent_runtime" {
  name               = "${local.name_prefix}-agentcore-runtime-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = { Name = "${local.name_prefix}-agentcore-runtime-role" }
}

resource "aws_iam_role_policy" "agent_runtime" {
  name   = "${local.name_prefix}-agentcore-runtime-policy"
  role   = aws_iam_role.agent_runtime.id
  policy = data.aws_iam_policy_document.agent_runtime.json
}

data "aws_iam_policy_document" "agent_runtime" {
  statement {
    sid       = "SecretsAccess"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [
      "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/*",
      "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.environment}/mcp-server/*",
      "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:bedrock-agentcore-identity*"
    ]
  }

  statement {
    sid    = "BedrockAccess"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:ApplyGuardrail",
      "bedrock:GetGuardrail"
    ]
    resources = [
      "arn:aws:bedrock:${var.aws_region}::foundation-model/*",
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:guardrail/${aws_bedrock_guardrail.main.guardrail_id}"
    ]
  }

  statement {
    sid    = "S3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:AbortMultipartUpload"
    ]
    resources = ["arn:aws:s3:::${local.name_prefix}-data/*"]
  }

  statement {
    sid    = "DynamoDBAccess"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:Query"
    ]
    resources = ["arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.name_prefix}-*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "CloudWatchMetrics"
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
  }

  statement {
    sid    = "AgentCoreWorkloadIdentity"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:CreateWorkloadIdentity",
      "bedrock-agentcore:GetWorkloadIdentity",
      "bedrock-agentcore:DeleteWorkloadIdentity",
      "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
      "bedrock-agentcore:GetResourceOauth2Token"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "KMSDecrypt"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey"]
    resources = [var.secrets_kms_key_arn]
  }

  statement {
    sid       = "ECRAuth"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid       = "ECRPull"
    effect    = "Allow"
    actions   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    resources = [module.ecr.repository_arn]
  }
}

resource "aws_bedrockagentcore_gateway" "main" {
  name            = "${local.name_prefix}-agentcore-gateway"
  role_arn        = aws_iam_role.gateway.arn
  authorizer_type = "AWS_IAM"
  protocol_type   = "MCP"
  description     = "AgentCore MCP Gateway for ${var.project_name} (${var.environment})"
  tags            = { Name = "${local.name_prefix}-agentcore-gateway" }
}

resource "aws_bedrockagentcore_agent_runtime" "main" {
  agent_runtime_name = "${replace(var.project_name, "-", "_")}_${var.environment}_runtime"
  role_arn           = aws_iam_role.agent_runtime.arn
  description        = "AgentCore runtime for ${var.project_name} (${var.environment})"

  agent_runtime_artifact {
    container_configuration {
      container_uri = var.agent_runtime_container_uri
    }
  }

  network_configuration {
    network_mode = local.is_production ? "VPC" : "PUBLIC"

    dynamic "network_mode_config" {
      for_each = local.is_production ? [1] : []
      content {
        subnets         = toset(local.private_subnet_ids)
        security_groups = toset(local.agent_runtime_security_group_ids)
      }
    }
  }

  protocol_configuration {
    server_protocol = "MCP"
  }

  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url = var.jwt_discovery_url
      allowed_clients = ["AmazonQuickSuite"]
    }
  }

  environment_variables = {
    PROJECT_NAME  = var.project_name
    ENVIRONMENT   = var.environment
    AWS_REGION    = var.aws_region
    BEDROCK_MODEL = var.bedrock_model_id
    LOG_LEVEL     = "INFO"
    S3_BUCKET     = "${local.name_prefix}-data"
    GUARDRAIL_ID  = aws_bedrock_guardrail.main.guardrail_id
  }

  tags = { Name = "${local.name_prefix}-agentcore-runtime" }

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_bedrockagentcore_oauth2_credential_provider" "custom_microsoft" {
  name = "microsoft-oauth-provider"
  credential_provider_vendor = "CustomOauth2"

  oauth2_provider_config {
    custom_oauth2_provider_config {
      client_id     = var.agentcore_microsoft_client_id
      client_secret = var.agentcore_microsoft_client_secret
      oauth_discovery {
        discovery_url = "https://login.microsoftonline.com/${var.microsoft_tenant_id}/v2.0/.well-known/openid-configuration"
      }
    }
  }
}

# Should be, but tenant_id is not supported: https://github.com/hashicorp/terraform-provider-aws/issues/46141
# resource "aws_bedrockagentcore_oauth2_credential_provider" "microsoft" {
#   name = "microsoft-oauth-provider"
#   credential_provider_vendor = "Microsoft"
#   oauth2_provider_config {
#     microsoft_oauth2_provider_config {
#       client_id     = var.agentcore_microsoft_client_id
#       client_secret = var.agentcore_microsoft_client_secret
#       tenant_id = "<your-tenant-id>"
#     }
#     }
#   }
# }

