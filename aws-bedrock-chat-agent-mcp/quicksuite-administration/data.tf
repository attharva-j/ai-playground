data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_iam_account_alias" "current" {}
data "aws_ssoadmin_instances" "current" {}

data "aws_identitystore_group" "creator_idc_group" {
  identity_store_id = local.identity_store_id

  alternate_identifier {
    unique_attribute {
      attribute_path  = "DisplayName"
      attribute_value = var.idc_groups.creator
    }
  }
}

data "aws_identitystore_group_memberships" "creator_idc_members" {
  identity_store_id = local.identity_store_id
  group_id          = data.aws_identitystore_group.creator_idc_group.group_id
}

data "aws_identitystore_user" "creator_idc_user" {
  for_each          = { for m in coalesce(data.aws_identitystore_group_memberships.creator_idc_members.group_memberships, []) : m.member_id.user_id => m }
  identity_store_id = local.identity_store_id
  user_id           = each.key
}


