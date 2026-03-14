# quicksuite-administration

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.10 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.30.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 6.30.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_iam_policy.quicksuite_admin_pro](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_quicksight_account_settings.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_account_settings) | resource |
| [aws_quicksight_account_subscription.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_account_subscription) | resource |
| [aws_quicksight_iam_policy_assignment.quicksuite_admin_pro](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_iam_policy_assignment) | resource |
| [aws_quicksight_role_membership.role_groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_role_membership) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_iam_account_alias.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_account_alias) | data source |
| [aws_iam_policy_document.quicksuite_admin_pro](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |
| [aws_ssoadmin_instances.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssoadmin_instances) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_role_groups"></a> [role\_groups](#input\_role\_groups) | Groups to match to each of the QuickSuite roles. | <pre>object({<br/>    admin_pro  = optional(set(string), [])<br/>    admin      = optional(set(string), [])<br/>    author_pro = optional(set(string), [])<br/>    author     = optional(set(string), [])<br/>    reader_pro = optional(set(string), [])<br/>    reader     = optional(set(string), [])<br/>  })</pre> | n/a | yes |
| <a name="input_spacelift_stack_branch"></a> [spacelift\_stack\_branch](#input\_spacelift\_stack\_branch) | The primary branch associated with the Spacelift stack, typically indicating the environment. | `string` | n/a | yes |

## Outputs

No outputs.
<!-- END_TF_DOCS -->
