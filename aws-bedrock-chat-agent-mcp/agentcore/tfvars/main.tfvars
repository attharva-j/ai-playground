aws_region                  = "us-east-1"
project_name                = "ai-foundation"
environment                 = "prod"
availability_zones          = ["us-east-1b", "us-east-1c"]
lambda_runtime              = "python3.12"
lambda_timeout              = 300
lambda_memory_size          = 512
bedrock_model_id            = "anthropic.claude-sonnet-4-20250514-v1:0"
agent_runtime_container_uri = "<account-id>.dkr.ecr.us-east-1.amazonaws.com/aifoundation:prod"
secrets_kms_key_arn         = "arn:aws:kms:us-east-1:<account-id>:key/<key-id>"
existing_vpc_id             = "<your-vpc-id>"
existing_private_subnet_ids = ["<subnet-id-1>", "<subnet-id-2>"]
# Optional: provide pre-created SG IDs; when omitted, module creates a dedicated runtime SG in prod.
# existing_security_group_ids = ["sg-PROD_AGENTCORE_RUNTIME"]
jwt_discovery_url           = "https://<your-oidc-provider>/.well-known/openid-configuration"
microsoft_tenant_id         = "<your-tenant-id>"
