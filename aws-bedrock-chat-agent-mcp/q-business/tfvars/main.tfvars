spacelift_stack_branch = "prod"

aws_region                   = "us-east-1"
application_name             = "enterprise-qbusiness-sharepoint-prod"
application_description      = "Enterprise Q Business application with SharePoint integration (Prod)"
identity_center_instance_arn = "arn:aws:sso:::instance/<sso-instance-id>"
index_capacity_units         = 25

sharepoint_tenant_id = "<your-tenant-id>"

# S3 certificate bucket (shared across data sources using OAuth2Certificate)
sharepoint_s3_bucket_name = "ai-foundation-dev-data"
sharepoint_s3_kms_key_arn = "arn:aws:kms:us-east-1:<account-id>:key/<key-id>"

# SharePoint Data Sources
sharepoint_data_sources = {
  "teams" = {
    site_urls           = ["https://teams.<your-domain.com>/sites/<site-name>"]
    domain              = "teams.<your-domain.com>"
    secret_name         = "QBusiness-SharePoint-<secret-suffix>"
    auth_type           = "OAuth2Certificate"
    s3_certificate_name = "<org>-quick-sharepoint/<certificate-hash>.crt"
    enable_acl          = true
    sync_schedule       = "cron(0 0 * * ? *)"
  }

  "intranet" = {
    site_urls           = ["https://intranet.<your-domain.com>/sites/<site-name>"]
    domain              = "intranet.<your-domain.com>"
    secret_name         = "QBusiness-SharePoint-<secret-suffix>"
    auth_type           = "OAuth2Certificate"
    s3_certificate_name = "<org>-quick-sharepoint/<certificate-hash>.crt"
    enable_acl          = false
    sync_schedule       = "cron(0 0 * * ? *)"
  }

  "collaboration" = {
    site_urls           = [
      "https://collaboration.<your-domain.com>/sites/<site-name-1>",
      "https://collaboration.<your-domain.com>/sites/<site-name-2>",
      "https://collaboration.<your-domain.com>/sites/<site-name-3>",
      "https://collaboration.<your-domain.com>/sites/<site-name-4>",
      "https://collaboration.<your-domain.com>/sites/<site-name-5>",
    ]
    domain              = "collaboration.<your-domain.com>"
    secret_name         = "QBusiness-SharePoint-<secret-suffix>"
    auth_type           = "OAuth2Certificate"
    s3_certificate_name = "<org>-quick-sharepoint/<certificate-hash>.crt"
    enable_acl          = true
    sync_schedule       = "cron(0 0 * * ? *)"
  }
}
