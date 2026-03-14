data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Look up Secrets Manager secrets for each SharePoint data source.
data "aws_secretsmanager_secret" "sharepoint" {
  for_each = var.sharepoint_data_sources
  name     = each.value.secret_name
}