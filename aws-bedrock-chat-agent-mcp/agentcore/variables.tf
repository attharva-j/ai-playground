variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "ai-foundation"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
}

variable "bedrock_model_id" {
  description = "Bedrock model ID"
  type        = string
  default     = "anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "existing_vpc_id" {
  description = "Existing VPC ID used by AgentCore"
  type        = string
}

variable "existing_private_subnet_ids" {
  description = "Existing private subnet IDs used by AgentCore"
  type        = list(string)
}

variable "existing_public_subnet_ids" {
  description = "Existing public subnet IDs used by AgentCore"
  type        = list(string)
  default     = []
}

variable "existing_security_group_ids" {
  description = "Existing security group IDs used by AgentCore runtime VPC configuration"
  type        = list(string)
  default     = []
}

variable "agent_runtime_container_uri" {
  description = "Container image URI for AgentCore Agent Runtime"
  type        = string
}

variable "gateway_target_lambda_arn" {
  description = "Lambda ARN for Gateway Target MCP integration"
  type        = string
  default     = ""
}

variable "agentcore_microsoft_client_id" {
  description = "Client ID for Microsoft Oauth2 credential provider"
  type        = string
}

variable "agentcore_microsoft_client_secret" {
  description = "Client secret for Microsoft Oauth2 credential provider"
  type        = string
  sensitive   = true
}

variable "microsoft_tenant_id" {
  description = "Microsoft Entra ID (Azure AD) tenant ID"
  type        = string
}

variable "secrets_kms_key_arn" {
  description = "KMS key ARN used to encrypt Secrets Manager secrets"
  type        = string
}

variable "jwt_discovery_url" {
  description = "OIDC discovery URL for JWT authorizer on AgentCore runtime"
  type        = string
}
