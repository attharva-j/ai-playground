# quicksuite-redirect

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

| Name | Source | Version |
|------|--------|---------|
| <a name="module_acm"></a> [acm](#module\_acm) | terraform-aws-modules/acm/aws | ~> 6.3.0 |
| <a name="module_cloudfront"></a> [cloudfront](#module\_cloudfront) | terraform-aws-modules/cloudfront/aws | ~> 6.4.0 |

## Resources

| Name | Type |
|------|------|
| [aws_cloudfront_function.redirect](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_function) | resource |
| [aws_route53_delegation_set.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_delegation_set) | resource |
| [aws_route53_record.cloudfront](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_record) | resource |
| [aws_route53_zone.managed](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_zone) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_redirect_zone"></a> [redirect\_zone](#input\_redirect\_zone) | n/a | `string` | n/a | yes |
| <a name="input_zone_names"></a> [zone\_names](#input\_zone\_names) | n/a | `string` | n/a | yes |

## Outputs

No outputs.
<!-- END_TF_DOCS -->
