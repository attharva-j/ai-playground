output "vpc_id" {
  description = "VPC ID"
  value       = local.vpc_id
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = local.private_subnet_ids
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = local.public_subnet_ids
}

output "agent_runtime_security_group_ids" {
  description = "Security group IDs attached to AgentCore runtime in VPC mode"
  value       = local.agent_runtime_security_group_ids
}

output "s3_bucket_data" {
  description = "Data S3 bucket name"
  value       = module.s3_data.s3_bucket_id
}

output "s3_bucket_logs" {
  description = "Logs S3 bucket name"
  value       = module.s3_logs.s3_bucket_id
}

output "dynamodb_conversations_table" {
  description = "DynamoDB conversations table name"
  value       = module.dynamodb_conversations.dynamodb_table_id
}

output "dynamodb_agent_state_table" {
  description = "DynamoDB agent state table name"
  value       = module.dynamodb_agent_state.dynamodb_table_id
}

output "bedrock_guardrail_id" {
  description = "Bedrock guardrail ID"
  value       = aws_bedrock_guardrail.main.guardrail_id
}

output "secrets_api_keys_arn" {
  description = "Secrets Manager ARN for API keys"
  value       = module.secrets.secret_arns["${local.name_prefix}/api-keys"]
}

output "resource_group_name" {
  description = "AWS Resource Group name"
  value       = aws_resourcegroups_group.agentcore.name
}

output "resource_group_arn" {
  description = "AWS Resource Group ARN"
  value       = aws_resourcegroups_group.agentcore.arn
}

output "agentcore_gateway_id" {
  description = "Bedrock AgentCore Gateway ID"
  value       = aws_bedrockagentcore_gateway.main.gateway_id
}

output "agentcore_gateway_url" {
  description = "Bedrock AgentCore Gateway URL"
  value       = aws_bedrockagentcore_gateway.main.gateway_url
}

output "agentcore_runtime_id" {
  description = "Bedrock AgentCore Agent Runtime ID"
  value       = aws_bedrockagentcore_agent_runtime.main.agent_runtime_id
}

output "agentcore_runtime_arn" {
  description = "Bedrock AgentCore Agent Runtime ARN"
  value       = aws_bedrockagentcore_agent_runtime.main.agent_runtime_arn
}

output "cloudwatch_log_group_gateway" {
  description = "CloudWatch log group for AgentCore Gateway"
  value       = aws_cloudwatch_log_group.gateway.name
}

output "cloudwatch_log_group_runtime" {
  description = "CloudWatch log group for AgentCore Runtime"
  value       = aws_cloudwatch_log_group.runtime.name
}
