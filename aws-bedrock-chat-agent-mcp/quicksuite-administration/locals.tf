locals {
  environment  = var.spacelift_stack_branch == "main" ? "prod" : "nonprod"
  account_name = replace(replace(data.aws_iam_account_alias.current.id, "company-", ""), "/-[a-z]+$/", "")
  role_groups = {
    admin_pro = [var.idc_groups.admin_pro]
    author_pro = [var.idc_groups.author_pro, var.idc_groups.creator]
    reader_pro = [var.idc_groups.general]
  }
   identity_store_id = tolist(data.aws_ssoadmin_instances.current.identity_store_ids)[0]
}
