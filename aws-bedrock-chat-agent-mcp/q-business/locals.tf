locals {
  environment  = var.spacelift_stack_branch == "main" ? "prod" : "nonprod"
  account_name = data.aws_caller_identity.current.account_id

  # Default crawl settings for SharePoint data sources.
  default_additional_properties = {
    inclusionFileTypePatterns          = []
    crawlPages                         = true
    deletionProtectionThreshold        = "0"
    proxyPort                          = ""
    includeSupportedFileType           = false
    isCrawlAdGroupMapping              = true
    crawlListData                      = true
    crawlComments                      = true
    fieldForUserId                     = "uuid"
    enableDeletionProtection           = false
    inclusionOneNoteSectionNamePatterns = []
    crawlFiles                         = true
    linkTitleFilterRegEx               = []
    exclusionOneNoteSectionNamePatterns = []
    exclusionFilePath                  = []
    exclusionFileTypePatterns          = []
    inclusionOneNotePageNamePatterns   = []
    maxFileSizeInMegaBytes             = "50"
    isCrawlLocalGroupMapping           = true
    crawlEvents                        = true
    pageTitleFilterRegEx               = []
    crawlLinks                         = true
    crawlAttachment                    = true
    exclusionOneNotePageNamePatterns   = []
    exclusionFileNamePatterns          = []
    eventTitleFilterRegEx              = []
    inclusionFileNamePatterns          = []
    inclusionFilePath                  = []
  }

  tags = {
    ManagedBy   = "Terraform"
    Environment = local.environment
    Application = "QBusiness"
  }
}
