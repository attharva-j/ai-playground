resource "aws_resourcegroups_group" "agentcore" {
  name        = "${local.name_prefix}-resources"
  description = "Resource group for AI Foundation AgentCore resources"

  resource_query {
    type = "TAG_FILTERS_1_0"
    query = jsonencode({
      ResourceTypeFilters = ["AWS::AllSupported"]
      TagFilters = [
        {
          Key    = "Project"
          Values = [var.project_name]
        },
        {
          Key    = "Environment"
          Values = [var.environment]
        }
      ]
    })
  }

  tags = {
    Name        = "${local.name_prefix}-resources"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
