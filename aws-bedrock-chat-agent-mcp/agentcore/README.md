# AgentCore

Core AI Foundation runtime infrastructure on AWS.

## Resources

- **Bedrock AgentCore Gateway** — MCP gateway with AWS_IAM authorizer
- **Bedrock AgentCore Agent Runtime** — serverless runtime for AI agents (public network mode)
- **Bedrock AgentCore Gateway Target** — links gateway to runtime
- **Bedrock Guardrail** — content filtering (sexual, violence, hate, insults, misconduct, prompt attack) + PII handling
- **S3 Buckets** — data, artifacts, logs (with lifecycle policies)
- **DynamoDB Tables** — conversations (session_id + timestamp), agent-state (agent_id)
- **Secrets Manager** — api-keys, bedrock-config, app-secrets
- **AWS Resource Group** — tag-based resource discovery
- **IAM Roles** — gateway role, runtime role with scoped policies (Bedrock, S3, DynamoDB, SecretsManager, CloudWatch)

## Architecture

- Uses an **existing VPC** (configurable) — no VPC creation
- Agent Runtime runs in **PUBLIC** network mode
- Gateway exposes **MCP** protocol with **AWS_IAM** authorization
- All resources tagged via provider default_tags (`Project`, `Environment`, `ManagedBy`, `Team`)

## Inputs

| Variable | Description | Default |
|---|---|---|
| `aws_region` | AWS region | `us-east-1` |
| `project_name` | Project name for resource naming | `ai-foundation` |
| `environment` | Environment name | `dev` |
| `existing_vpc_id` | Existing VPC ID | `<your-vpc-id>` |
| `existing_private_subnet_ids` | Private subnet IDs | 2 subnets |
| `existing_public_subnet_ids` | Public subnet IDs | `[]` |
| `lambda_runtime` | Lambda runtime | `python3.12` |
| `lambda_timeout` | Lambda timeout (seconds) | `300` |
| `lambda_memory_size` | Lambda memory (MB) | `512` |
| `bedrock_model_id` | Bedrock model ID | `anthropic.claude-sonnet-4-20250514-v1:0` |

## Outputs

| Output | Description |
|---|---|
| `vpc_id` | VPC ID |
| `private_subnets` | Private subnet IDs |
| `s3_bucket_data` | Data bucket name |
| `s3_bucket_artifacts` | Artifacts bucket name |
| `s3_bucket_logs` | Logs bucket name |
| `dynamodb_conversations_table` | Conversations table name |
| `dynamodb_agent_state_table` | Agent state table name |
| `bedrock_guardrail_id` | Guardrail ID |
| `secrets_api_keys_arn` | API keys secret ARN |
| `resource_group_name` | Resource group name |
| `agentcore_gateway_id` | AgentCore Gateway ID |
| `agentcore_gateway_url` | AgentCore Gateway URL |
| `agentcore_runtime_id` | Agent Runtime ID |
| `agentcore_runtime_arn` | Agent Runtime ARN |

## Deploy

```bash
cd agentcore/
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## Post-Deploy

1. Verify AgentCore Gateway status is `READY`
2. Verify Agent Runtime status is `READY`
3. Update secrets in Secrets Manager (api-keys, bedrock-config, app-secrets)
4. Verify Resource Group contains tagged resources

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.5.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.0 |
| <a name="requirement_sops"></a> [sops](#requirement\_sops) | ~> 1.0.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 6.0 |
| <a name="provider_sops"></a> [sops](#provider\_sops) | ~> 1.0.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_docker_hub_secret"></a> [docker\_hub\_secret](#module\_docker\_hub\_secret) | hashicorp/aws | ~> 1.0 |
| <a name="module_dynamodb_agent_state"></a> [dynamodb\_agent\_state](#module\_dynamodb\_agent\_state) | terraform-aws-modules/dynamodb-table/aws | ~> 4.0 |
| <a name="module_dynamodb_conversations"></a> [dynamodb\_conversations](#module\_dynamodb\_conversations) | terraform-aws-modules/dynamodb-table/aws | ~> 4.0 |
| <a name="module_ecr"></a> [ecr](#module\_ecr) | terraform-aws-modules/ecr/aws | ~> 2.0 |
| <a name="module_s3_data"></a> [s3\_data](#module\_s3\_data) | terraform-aws-modules/s3-bucket/aws | n/a |
| <a name="module_s3_logs"></a> [s3\_logs](#module\_s3\_logs) | terraform-aws-modules/s3-bucket/aws | n/a |
| <a name="module_secrets"></a> [secrets](#module\_secrets) | hashicorp/aws | n/a |

## Resources

| Name | Type |
|------|------|
| [aws_bedrock_guardrail.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_guardrail) | resource |
| [aws_bedrock_guardrail_version.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_guardrail_version) | resource |
| [aws_bedrockagentcore_agent_runtime.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime) | resource |
| [aws_bedrockagentcore_gateway.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_gateway) | resource |
| [aws_bedrockagentcore_oauth2_credential_provider.custom_microsoft](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_oauth2_credential_provider) | resource |
| [aws_cloudwatch_log_delivery.gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery) | resource |
| [aws_cloudwatch_log_delivery.runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery) | resource |
| [aws_cloudwatch_log_delivery_destination.gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery_destination) | resource |
| [aws_cloudwatch_log_delivery_destination.runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery_destination) | resource |
| [aws_cloudwatch_log_delivery_source.gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery_source) | resource |
| [aws_cloudwatch_log_delivery_source.runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery_source) | resource |
| [aws_cloudwatch_log_group.gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_cloudwatch_log_group.runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_cloudwatch_log_resource_policy.agentcore_log_delivery](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_resource_policy) | resource |
| [aws_ecr_pull_through_cache_rule.docker_hub](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_pull_through_cache_rule) | resource |
| [aws_iam_role.agent_runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role.gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role.gh_actions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.agent_runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy.gh_actions_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_resourcegroups_group.agentcore](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/resourcegroups_group) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_iam_openid_connect_provider.github_actions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_openid_connect_provider) | data source |
| [aws_iam_policy_document.agent_runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.assume_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_secretsmanager_secret_version.bedrock_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_secret_version) | data source |
| [aws_vpc.selected](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc) | data source |
| [sops_file.docker_hub](https://registry.terraform.io/providers/carlpett/sops/latest/docs/data-sources/file) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_agent_runtime_container_uri"></a> [agent\_runtime\_container\_uri](#input\_agent\_runtime\_container\_uri) | Container image URI for AgentCore Agent Runtime | `string` | `"<account-id>.dkr.ecr.us-east-1.amazonaws.com/aifoundation:latest"` | no |
| <a name="input_agentcore_microsoft_client_id"></a> [agentcore\_microsoft\_client\_id](#input\_agentcore\_microsoft\_client\_id) | Client ID for Microsoft Oauth2 credential provider | `string` | n/a | yes |
| <a name="input_agentcore_microsoft_client_secret"></a> [agentcore\_microsoft\_client\_secret](#input\_agentcore\_microsoft\_client\_secret) | Client secret for Microsoft Oauth2 credential provider | `string` | n/a | yes |
| <a name="input_availability_zones"></a> [availability\_zones](#input\_availability\_zones) | Availability zones | `list(string)` | <pre>[<br>  "us-east-1a",<br>  "us-east-1b"<br>]</pre> | no |
| <a name="input_aws_region"></a> [aws\_region](#input\_aws\_region) | AWS region | `string` | `"us-east-1"` | no |
| <a name="input_bedrock_model_id"></a> [bedrock\_model\_id](#input\_bedrock\_model\_id) | Bedrock model ID | `string` | `"anthropic.claude-sonnet-4-20250514-v1:0"` | no |
| <a name="input_environment"></a> [environment](#input\_environment) | Environment name | `string` | `"dev"` | no |
| <a name="input_existing_private_subnet_ids"></a> [existing\_private\_subnet\_ids](#input\_existing\_private\_subnet\_ids) | Existing private subnet IDs used by AgentCore | `list(string)` | `["<subnet-id-1>", "<subnet-id-2>"]` | no |
| <a name="input_existing_public_subnet_ids"></a> [existing\_public\_subnet\_ids](#input\_existing\_public\_subnet\_ids) | Existing public subnet IDs used by AgentCore | `list(string)` | `[]` | no |
| <a name="input_existing_vpc_id"></a> [existing\_vpc\_id](#input\_existing\_vpc\_id) | Existing VPC ID used by AgentCore | `string` | `"<your-vpc-id>"` | no |
| <a name="input_gateway_target_lambda_arn"></a> [gateway\_target\_lambda\_arn](#input\_gateway\_target\_lambda\_arn) | Lambda ARN for Gateway Target MCP integration | `string` | `""` | no |
| <a name="input_lambda_memory_size"></a> [lambda\_memory\_size](#input\_lambda\_memory\_size) | Lambda memory size in MB | `number` | `512` | no |
| <a name="input_lambda_runtime"></a> [lambda\_runtime](#input\_lambda\_runtime) | Lambda runtime | `string` | `"python3.12"` | no |
| <a name="input_lambda_timeout"></a> [lambda\_timeout](#input\_lambda\_timeout) | Lambda timeout in seconds | `number` | `300` | no |
| <a name="input_private_subnet_cidrs"></a> [private\_subnet\_cidrs](#input\_private\_subnet\_cidrs) | CIDR blocks for private subnets | `list(string)` | <pre>[<br>  "10.0.1.0/24",<br>  "10.0.2.0/24"<br>]</pre> | no |
| <a name="input_project_name"></a> [project\_name](#input\_project\_name) | Project name used for resource naming | `string` | `"ai-foundation"` | no |
| <a name="input_public_subnet_cidrs"></a> [public\_subnet\_cidrs](#input\_public\_subnet\_cidrs) | CIDR blocks for public subnets | `list(string)` | <pre>[<br>  "10.0.101.0/24",<br>  "10.0.102.0/24"<br>]</pre> | no |
| <a name="input_secrets_kms_key_arn"></a> [secrets\_kms\_key\_arn](#input\_secrets\_kms\_key\_arn) | KMS key ARN used to encrypt Secrets Manager secrets | `string` | `"arn:aws:kms:us-east-1:<account-id>:key/<key-id>"` | no |
| <a name="input_vpc_cidr"></a> [vpc\_cidr](#input\_vpc\_cidr) | CIDR block for VPC | `string` | `"10.0.0.0/16"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_agentcore_gateway_id"></a> [agentcore\_gateway\_id](#output\_agentcore\_gateway\_id) | Bedrock AgentCore Gateway ID |
| <a name="output_agentcore_gateway_url"></a> [agentcore\_gateway\_url](#output\_agentcore\_gateway\_url) | Bedrock AgentCore Gateway URL |
| <a name="output_agentcore_runtime_arn"></a> [agentcore\_runtime\_arn](#output\_agentcore\_runtime\_arn) | Bedrock AgentCore Agent Runtime ARN |
| <a name="output_agentcore_runtime_id"></a> [agentcore\_runtime\_id](#output\_agentcore\_runtime\_id) | Bedrock AgentCore Agent Runtime ID |
| <a name="output_bedrock_guardrail_id"></a> [bedrock\_guardrail\_id](#output\_bedrock\_guardrail\_id) | Bedrock guardrail ID |
| <a name="output_cloudwatch_log_group_gateway"></a> [cloudwatch\_log\_group\_gateway](#output\_cloudwatch\_log\_group\_gateway) | CloudWatch log group for AgentCore Gateway |
| <a name="output_cloudwatch_log_group_runtime"></a> [cloudwatch\_log\_group\_runtime](#output\_cloudwatch\_log\_group\_runtime) | CloudWatch log group for AgentCore Runtime |
| <a name="output_dynamodb_agent_state_table"></a> [dynamodb\_agent\_state\_table](#output\_dynamodb\_agent\_state\_table) | DynamoDB agent state table name |
| <a name="output_dynamodb_conversations_table"></a> [dynamodb\_conversations\_table](#output\_dynamodb\_conversations\_table) | DynamoDB conversations table name |
| <a name="output_private_subnets"></a> [private\_subnets](#output\_private\_subnets) | Private subnet IDs |
| <a name="output_public_subnets"></a> [public\_subnets](#output\_public\_subnets) | Public subnet IDs |
| <a name="output_resource_group_arn"></a> [resource\_group\_arn](#output\_resource\_group\_arn) | AWS Resource Group ARN |
| <a name="output_resource_group_name"></a> [resource\_group\_name](#output\_resource\_group\_name) | AWS Resource Group name |
| <a name="output_s3_bucket_data"></a> [s3\_bucket\_data](#output\_s3\_bucket\_data) | Data S3 bucket name |
| <a name="output_s3_bucket_logs"></a> [s3\_bucket\_logs](#output\_s3\_bucket\_logs) | Logs S3 bucket name |
| <a name="output_secrets_api_keys_arn"></a> [secrets\_api\_keys\_arn](#output\_secrets\_api\_keys\_arn) | Secrets Manager ARN for API keys |
| <a name="output_vpc_id"></a> [vpc\_id](#output\_vpc\_id) | VPC ID |
<!-- END_TF_DOCS -->