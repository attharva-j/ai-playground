# Q Business Application, Index, Retriever, and SharePoint Data Sources
resource "awscc_qbusiness_application" "main" {
  display_name                 = var.application_name
  description                  = var.application_description
  identity_center_instance_arn = var.identity_center_instance_arn

  tags = [{
    key   = "Environment"
    value = local.environment
  }, {
    key   = "ManagedBy"
    value = "Terraform"
  }]
}

# Index for document storage and search
resource "awscc_qbusiness_index" "main" {
  application_id = awscc_qbusiness_application.main.application_id
  display_name   = "${var.application_name}-index"
  type           = "ENTERPRISE"

  capacity_configuration = {
    units = var.index_capacity_units
  }

  tags = [{
    key   = "Environment"
    value = local.environment
  }, {
    key   = "ManagedBy"
    value = "Terraform"
  }]
}

# Native index retriever - connects the app to the index for queries
resource "awscc_qbusiness_retriever" "main" {
  application_id = awscc_qbusiness_application.main.application_id
  display_name   = "${var.application_name}-retriever"
  type           = "NATIVE_INDEX"

  configuration = {
    native_index_configuration = {
      index_id = awscc_qbusiness_index.main.index_id
    }
  }

  tags = [{
    key   = "Environment"
    value = local.environment
  }, {
    key   = "ManagedBy"
    value = "Terraform"
  }]
}

# SharePoint Data Sources - each data source crawls SharePoint sites under a specific domain
resource "awscc_qbusiness_data_source" "sharepoint" {
  for_each = var.sharepoint_data_sources

  application_id = awscc_qbusiness_application.main.application_id
  index_id       = awscc_qbusiness_index.main.index_id
  display_name   = "SharePoint-${each.key}"
  role_arn       = aws_iam_role.qbusiness_datasource[each.key].arn

  configuration = jsonencode({
    type                  = "SHAREPOINT"
    syncMode              = "FULL_CRAWL"
    ingestionMode         = "SCHEDULED"
    secretArn             = data.aws_secretsmanager_secret.sharepoint[each.key].arn
    enableIdentityCrawler = each.value.enable_identity_crawler
    identityLoggingStatus = each.value.enable_identity_crawler ? "ENABLED" : "DISABLED"

    connectionConfiguration = {
      repositoryEndpointMetadata = {
        tenantId = var.sharepoint_tenant_id
        siteUrls = each.value.site_urls
        domain   = each.value.domain
        repositoryAdditionalProperties = {
          onPremVersion     = ""
          s3certificateName = each.value.s3_certificate_name
          authType          = each.value.auth_type
          s3bucketName      = var.sharepoint_s3_bucket_name
          version           = "Online"
        }
      }
    }

    # Field mappings - maps SharePoint fields to Q Business index fields
    repositoryConfigurations = {
      file = {
        fieldMappings = [
          { dataSourceFieldName = "title", indexFieldName = "_document_title", indexFieldType = "STRING" },
          { dataSourceFieldName = "lastModifiedDateTime", indexFieldName = "_last_updated_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "sourceUri", indexFieldName = "_source_uri", indexFieldType = "STRING" },
          { dataSourceFieldName = "createdAt", indexFieldName = "_created_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "author", indexFieldName = "_authors", indexFieldType = "STRING_LIST" },
          { dataSourceFieldName = "category", indexFieldName = "_category", indexFieldType = "STRING" }
        ]
      }
      event = {
        fieldMappings = [
          { dataSourceFieldName = "title", indexFieldName = "_document_title", indexFieldType = "STRING" },
          { dataSourceFieldName = "lastModifiedDateTime", indexFieldName = "_last_updated_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "sourceUri", indexFieldName = "_source_uri", indexFieldType = "STRING" },
          { dataSourceFieldName = "createdDate", indexFieldName = "_created_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "category", indexFieldName = "_category", indexFieldType = "STRING" }
        ]
      }
      page = {
        fieldMappings = [
          { dataSourceFieldName = "createdDateTime", indexFieldName = "_created_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "lastModifiedDateTime", indexFieldName = "_last_updated_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "title", indexFieldName = "_document_title", indexFieldType = "STRING" },
          { dataSourceFieldName = "sourceUri", indexFieldName = "_source_uri", indexFieldType = "STRING" },
          { dataSourceFieldName = "category", indexFieldName = "_category", indexFieldType = "STRING" }
        ]
      }
      link = {
        fieldMappings = [
          { dataSourceFieldName = "createdAt", indexFieldName = "_created_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "lastModifiedDateTime", indexFieldName = "_last_updated_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "title", indexFieldName = "_document_title", indexFieldType = "STRING" },
          { dataSourceFieldName = "sourceUri", indexFieldName = "_source_uri", indexFieldType = "STRING" },
          { dataSourceFieldName = "category", indexFieldName = "_category", indexFieldType = "STRING" }
        ]
      }
      attachment = {
        fieldMappings = [
          { dataSourceFieldName = "parentCreatedDate", indexFieldName = "_created_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "sourceUri", indexFieldName = "_source_uri", indexFieldType = "STRING" },
          { dataSourceFieldName = "category", indexFieldName = "_category", indexFieldType = "STRING" }
        ]
      }
      comment = {
        fieldMappings = [
          { dataSourceFieldName = "createdDateTime", indexFieldName = "_created_at", indexFieldType = "DATE", dateFieldFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'" },
          { dataSourceFieldName = "sourceUri", indexFieldName = "_source_uri", indexFieldType = "STRING" },
          { dataSourceFieldName = "author", indexFieldName = "_authors", indexFieldType = "STRING_LIST" },
          { dataSourceFieldName = "category", indexFieldName = "_category", indexFieldType = "STRING" }
        ]
      }
    }

    # Crawl settings - override any default by adding to additional_properties in the tfvars entry
    additionalProperties = merge(
      local.default_additional_properties,
      { crawlAcl = each.value.enable_acl },
      each.value.additional_properties
    )
  })

  sync_schedule = each.value.sync_schedule

  tags = [{
    key   = "Environment"
    value = local.environment
  }, {
    key   = "ManagedBy"
    value = "Terraform"
  }]
}
