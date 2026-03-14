data "aws_caller_identity" "current" {}

resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/${aws_bedrockagentcore_gateway.main.gateway_id}"
  retention_in_days = 90
  tags              = { Name = "${local.name_prefix}-gateway-logs" }
}

resource "aws_cloudwatch_log_group" "runtime" {
  name              = "/aws/vendedlogs/bedrock-agentcore/runtime/APPLICATION_LOGS/${aws_bedrockagentcore_agent_runtime.main.agent_runtime_id}"
  retention_in_days = 90
  tags              = { Name = "${local.name_prefix}-runtime-logs" }
}

resource "aws_cloudwatch_log_resource_policy" "agentcore_log_delivery" {
  policy_name = "${local.name_prefix}-agentcore-log-delivery"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSLogDeliveryWrite20150319"
        Effect = "Allow"
        Principal = {
          Service = ["delivery.logs.amazonaws.com"]
        }
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.gateway.arn}:log-stream:*",
          "${aws_cloudwatch_log_group.runtime.arn}:log-stream:*"
        ]
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = [data.aws_caller_identity.current.account_id]
          }
          ArnLike = {
            "aws:SourceArn" = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"]
          }
        }
      }
    ]
  })
}

resource "aws_cloudwatch_log_delivery_source" "gateway" {
  name         = "${local.name_prefix}-gateway-app-logs"
  log_type     = "APPLICATION_LOGS"
  resource_arn = "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:gateway/${aws_bedrockagentcore_gateway.main.gateway_id}"
}

resource "aws_cloudwatch_log_delivery_destination" "gateway" {
  name = "${local.name_prefix}-gateway-cloudwatch"
  delivery_destination_configuration {
    destination_resource_arn = aws_cloudwatch_log_group.gateway.arn
  }
  depends_on = [aws_cloudwatch_log_resource_policy.agentcore_log_delivery]
}

resource "aws_cloudwatch_log_delivery" "gateway" {
  delivery_source_name     = aws_cloudwatch_log_delivery_source.gateway.name
  delivery_destination_arn = aws_cloudwatch_log_delivery_destination.gateway.arn
}

resource "aws_cloudwatch_log_delivery_source" "runtime" {
  name         = "${local.name_prefix}-runtime-app-logs"
  log_type     = "APPLICATION_LOGS"
  resource_arn = "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:runtime/${aws_bedrockagentcore_agent_runtime.main.agent_runtime_id}"
}

resource "aws_cloudwatch_log_delivery_destination" "runtime" {
  name = "${local.name_prefix}-runtime-cloudwatch"
  delivery_destination_configuration {
    destination_resource_arn = aws_cloudwatch_log_group.runtime.arn
  }
  depends_on = [aws_cloudwatch_log_resource_policy.agentcore_log_delivery]
}

resource "aws_cloudwatch_log_delivery" "runtime" {
  delivery_source_name     = aws_cloudwatch_log_delivery_source.runtime.name
  delivery_destination_arn = aws_cloudwatch_log_delivery_destination.runtime.arn
}
