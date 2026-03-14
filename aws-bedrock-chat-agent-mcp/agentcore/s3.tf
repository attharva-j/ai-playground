module "s3_data" {
  source = "terraform-aws-modules/s3-bucket/aws"

  name       = local.s3_buckets.data.name
  versioning = true

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm     = "aws:kms"
        kms_master_key_id = null
      }
      bucket_key_enabled = true
    }
  }

  lifecycle_rule = [
    {
      id     = "archive-old-data"
      status = "Enabled"
      transition = [
        { days = 90, storage_class = "STANDARD_IA" },
        { days = 180, storage_class = "GLACIER" }
      ]
    }
  ]
}

module "s3_logs" {
  source = "terraform-aws-modules/s3-bucket/aws"

  name       = local.s3_buckets.logs.name
  versioning = false

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm     = "aws:kms"
        kms_master_key_id = null
      }
      bucket_key_enabled = true
    }
  }

  lifecycle_rule = [
    {
      id     = "expire-old-logs"
      status = "Enabled"
      transition = [
        { days = 30, storage_class = "STANDARD_IA" },
        { days = 90, storage_class = "GLACIER" }
      ]
      expiration = {
        days = 365
      }
    }
  ]
}
