output "qbusiness_application_id" {
  description = "The Q Business application ID"
  value       = awscc_qbusiness_application.main.application_id
}

output "qbusiness_index_id" {
  description = "The Q Business index ID"
  value       = awscc_qbusiness_index.main.index_id
}

output "sharepoint_datasource_ids" {
  description = "Map of SharePoint data source IDs keyed by data source name"
  value       = { for k, v in awscc_qbusiness_data_source.sharepoint : k => v.data_source_id }
}
