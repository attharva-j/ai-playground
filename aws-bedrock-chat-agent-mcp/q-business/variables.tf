variable "spacelift_stack_branch" {
  description = "The primary branch associated with the Spacelift stack, typically indicating the environment."
  type        = string
}

variable "aws_region" {
  description = "AWS region for Q Business deployment"
  type        = string
  default     = "us-east-1"
}

# --- Q Business Application ---

variable "application_name" {
  description = "Name of the Q Business application"
  type        = string
}

variable "application_description" {
  description = "Description of the Q Business application"
  type        = string
  default     = "Q Business application with SharePoint integration"
}

variable "identity_center_instance_arn" {
  description = "ARN of the AWS IAM Identity Center instance"
  type        = string
}

variable "index_capacity_units" {
  description = "Number of capacity units for the index"
  type        = number
  default     = 1
}

# --- SharePoint Tenant & Certificate ---

variable "sharepoint_tenant_id" {
  description = "SharePoint tenant ID"
  type        = string
}

variable "sharepoint_s3_bucket_name" {
  description = "S3 bucket name containing the public certificate for Entra ID App-Only auth"
  type        = string
  default     = ""
}

variable "sharepoint_s3_kms_key_arn" {
  description = "KMS key ARN used for S3 bucket encryption (SSE-KMS). Leave empty if bucket uses SSE-S3."
  type        = string
  default     = ""
}

# --- SharePoint Data Sources ---

variable "sharepoint_data_sources" {
  description = "Map of SharePoint data sources. Each key becomes the data source display name suffix."
  type = map(object({
    site_urls               = list(string)           # SharePoint site collection root URLs (must NOT include /Lists/... paths)
    domain                  = string                  # SharePoint domain (e.g., "teams.<your-domain.com>")
    secret_name             = string                  # AWS Secrets Manager secret name with SharePoint credentials
    auth_type               = optional(string, "OAuth2Certificate") # "OAuth2Certificate" or "OAuth2App"
    s3_certificate_name     = optional(string, "")    # S3 key for .crt file (required for OAuth2Certificate)
    enable_acl              = optional(bool, true)     # Enable ACL crawling for document-level access control
    enable_identity_crawler = optional(bool, true)     # Enable identity crawler for user/group sync
    sync_schedule           = optional(string, "cron(0 0 * * ? *)") # Cron schedule or "" for on-demand only
    additional_properties   = optional(map(any), {})   # Override default crawl settings (see locals.tf for defaults)
  }))

  validation {
    condition = alltrue([
      for k, v in var.sharepoint_data_sources :
      v.auth_type != "OAuth2Certificate" || v.s3_certificate_name != ""
    ])
    error_message = "s3_certificate_name is required when auth_type is OAuth2Certificate."
  }
}
