module "dynamodb_conversations" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "~> 4.0"

  name      = "${local.name_prefix}-conversations"
  hash_key  = "session_id"
  range_key = "timestamp"

  billing_mode = "PAY_PER_REQUEST"

  attributes = [
    { name = "session_id", type = "S" },
    { name = "timestamp", type = "N" },
    { name = "user_id", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "user-index"
      hash_key        = "user_id"
      projection_type = "ALL"
    }
  ]

  ttl_attribute_name = "ttl"
  ttl_enabled        = true

  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  point_in_time_recovery_enabled = true
  server_side_encryption_enabled = true

  tags = {
    Name    = "${local.name_prefix}-conversations"
    Purpose = "conversation-history"
  }
}

module "dynamodb_agent_state" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "~> 4.0"

  name     = "${local.name_prefix}-agent-state"
  hash_key = "agent_id"

  billing_mode = "PAY_PER_REQUEST"

  attributes = [
    { name = "agent_id", type = "S" }
  ]

  ttl_attribute_name = "ttl"
  ttl_enabled        = true

  point_in_time_recovery_enabled = true
  server_side_encryption_enabled = true

  tags = {
    Name    = "${local.name_prefix}-agent-state"
    Purpose = "agent-state"
  }
}
