locals {
  name_prefix = "${var.project_name}-${var.environment}"

  s3_buckets = {
    data = {
      name       = "${local.name_prefix}-data"
      versioning = true
    }
    artifacts = {
      name       = "${local.name_prefix}-artifacts"
      versioning = true
    }
    logs = {
      name       = "${local.name_prefix}-logs"
      versioning = false
    }
  }
}
