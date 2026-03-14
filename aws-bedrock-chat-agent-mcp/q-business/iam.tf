
# IAM Role per Data Source - each data source gets its own role for clean isolation
resource "aws_iam_role" "qbusiness_datasource" {
  for_each = var.sharepoint_data_sources

  name = "${var.application_name}-ds-${each.key}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "qbusiness.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "qbusiness_datasource" {
  for_each = var.sharepoint_data_sources

  name = "${var.application_name}-ds-${each.key}-policy"
  role = aws_iam_role.qbusiness_datasource[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      # S3 access for certificate (only if bucket is configured)
      var.sharepoint_s3_bucket_name != "" ? [
        {
          Sid    = "AllowsAmazonQToGetS3Objects"
          Effect = "Allow"
          Action = [
            "s3:GetObject"
          ]
          Resource = [
            "arn:aws:s3:::${var.sharepoint_s3_bucket_name}/*"
          ]
          Condition = {
            StringEquals = {
              "aws:ResourceAccount" = data.aws_caller_identity.current.account_id
            }
          }
        }
      ] : [],
      # KMS decrypt for S3 bucket encryption (only if KMS key is configured)
      var.sharepoint_s3_kms_key_arn != "" ? [
        {
          Sid    = "AllowsAmazonQToDecryptS3"
          Effect = "Allow"
          Action = [
            "kms:Decrypt"
          ]
          Resource = [
            var.sharepoint_s3_kms_key_arn
          ]
        }
      ] : [],
      # Core permissions
      [
        {
          Sid    = "AllowsAmazonQToGetSecret"
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue"
          ]
          Resource = data.aws_secretsmanager_secret.sharepoint[each.key].arn
        },
        {
          Sid    = "AllowsAmazonQToDecryptSecret"
          Effect = "Allow"
          Action = [
            "kms:Decrypt"
          ]
          Resource = "arn:aws:kms:${var.aws_region}:${data.aws_caller_identity.current.account_id}:key/*"
          Condition = {
            StringLike = {
              "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
            }
          }
        },
        {
          Sid    = "AllowsAmazonQToIngestDocuments"
          Effect = "Allow"
          Action = [
            "qbusiness:BatchPutDocument",
            "qbusiness:BatchDeleteDocument"
          ]
          Resource = [
            "arn:aws:qbusiness:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.main.application_id}",
            "arn:aws:qbusiness:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.main.application_id}/index/${awscc_qbusiness_index.main.index_id}"
          ]
        },
        # IAM Policy for Principal Mapping (Identity Crawler)
        {
          Sid    = "AllowsAmazonQToIngestPrincipalMapping"
          Effect = "Allow"
          Action = [
            "qbusiness:PutGroup",
            "qbusiness:CreateUser",
            "qbusiness:DeleteGroup",
            "qbusiness:UpdateUser",
            "qbusiness:GetUser",
            "qbusiness:ListGroups"
          ]
          Resource = [
            "arn:aws:qbusiness:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.main.application_id}",
            "arn:aws:qbusiness:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.main.application_id}/index/${awscc_qbusiness_index.main.index_id}",
            "arn:aws:qbusiness:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${awscc_qbusiness_application.main.application_id}/index/${awscc_qbusiness_index.main.index_id}/data-source/*"
          ]
        }
      ]
    )
  })
}
