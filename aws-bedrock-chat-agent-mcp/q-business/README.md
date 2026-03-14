# qbusiness-sharepoint-integration

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.10 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.30.0 |
| <a name="requirement_awscc"></a> [awscc](#requirement\_awscc) | ~> 1.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.30.0 |
| <a name="provider_awscc"></a> [awscc](#provider\_awscc) | ~> 1.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_iam_role.qbusiness_datasource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.qbusiness_datasource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [awscc_qbusiness_application.main](https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/qbusiness_application) | resource |
| [awscc_qbusiness_data_source.sharepoint](https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/qbusiness_data_source) | resource |
| [awscc_qbusiness_index.main](https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/qbusiness_index) | resource |
| [awscc_qbusiness_retriever.main](https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/qbusiness_retriever) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |
| [aws_secretsmanager_secret.sharepoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_secret) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_application_description"></a> [application\_description](#input\_application\_description) | Description of the Q Business application | `string` | `"Q Business application with SharePoint integration"` | no |
| <a name="input_application_name"></a> [application\_name](#input\_application\_name) | Name of the Q Business application | `string` | n/a | yes |
| <a name="input_aws_region"></a> [aws\_region](#input\_aws\_region) | AWS region for Q Business deployment | `string` | `"us-east-1"` | no |
| <a name="input_identity_center_instance_arn"></a> [identity\_center\_instance\_arn](#input\_identity\_center\_instance\_arn) | ARN of the AWS IAM Identity Center instance | `string` | n/a | yes |
| <a name="input_index_capacity_units"></a> [index\_capacity\_units](#input\_index\_capacity\_units) | Number of capacity units for the index | `number` | `1` | no |
| <a name="input_sharepoint_data_sources"></a> [sharepoint\_data\_sources](#input\_sharepoint\_data\_sources) | Map of SharePoint data sources. Each key becomes the data source display name suffix. | <pre>map(object({<br/>    site_urls               = list(string)<br/>    domain                  = string<br/>    secret_name             = string<br/>    auth_type               = optional(string, "OAuth2Certificate")<br/>    s3_certificate_name     = optional(string, "")<br/>    enable_acl              = optional(bool, true)<br/>    enable_identity_crawler = optional(bool, true)<br/>    sync_schedule           = optional(string, "cron(0 0 * * ? *)")<br/>    additional_properties   = optional(map(any), {})<br/>  }))</pre> | n/a | yes |
| <a name="input_sharepoint_s3_bucket_name"></a> [sharepoint\_s3\_bucket\_name](#input\_sharepoint\_s3\_bucket\_name) | S3 bucket name containing the public certificate for Entra ID App-Only auth | `string` | `""` | no |
| <a name="input_sharepoint_s3_kms_key_arn"></a> [sharepoint\_s3\_kms\_key\_arn](#input\_sharepoint\_s3\_kms\_key\_arn) | KMS key ARN used for S3 bucket encryption (SSE-KMS). Leave empty if bucket uses SSE-S3. | `string` | `""` | no |
| <a name="input_sharepoint_tenant_id"></a> [sharepoint\_tenant\_id](#input\_sharepoint\_tenant\_id) | SharePoint tenant ID | `string` | n/a | yes |
| <a name="input_spacelift_stack_branch"></a> [spacelift\_stack\_branch](#input\_spacelift\_stack\_branch) | The primary branch associated with the Spacelift stack, typically indicating the environment. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_qbusiness_application_id"></a> [qbusiness\_application\_id](#output\_qbusiness\_application\_id) | The Q Business application ID |
| <a name="output_qbusiness_index_id"></a> [qbusiness\_index\_id](#output\_qbusiness\_index\_id) | The Q Business index ID |
| <a name="output_sharepoint_datasource_ids"></a> [sharepoint\_datasource\_ids](#output\_sharepoint\_datasource\_ids) | Map of SharePoint data source IDs keyed by data source name |
<!-- END_TF_DOCS -->
