variable "spacelift_stack_branch" {
  description = "The primary branch associated with the Spacelift stack, typically indicating the environment."
  type        = string
}

variable "idc_groups" {
  description = "IAM Identity Center group names for each QuickSuite persona."
  type = object({
    admin_pro  = string
    author_pro = string
    creator    = string
    general    = string
  })
}
