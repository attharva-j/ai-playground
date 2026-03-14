#// AdminPro ---------------------------------------------------------//#

data "aws_iam_policy_document" "quicksuite_admin_pro" {
  statement {
    sid    = "QuickSuiteAdminPro"
    effect = "Allow"
    actions = [
      "quicksight:*",
      "qbusiness:Chat*",
      "qbusiness:CheckDocumentAccess",
      "qbusiness:Get*",
      "qbusiness:List*",
      "qbusiness:SearchRelevantContent"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "QuickSuiteAdminProCalledVia"
    effect = "Allow"
    actions = [
      "s3:*",
      "textract:*",
      "comprehend:*",
      "bedrock:*",
      "bedrock-agentcore:*",
      "bedrock-mantle:*",
      "logs:*",
      "kms:Decrypt"
    ]
    resources = ["*"]

    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "aws:CalledVia"
      values   = ["quicksight.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "quicksuite_admin_pro" {
  name        = "QuickSuiteAdminPro"
  description = "For QuickSuite administration."
  policy      = data.aws_iam_policy_document.quicksuite_admin_pro.json

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_quicksight_iam_policy_assignment" "quicksuite_admin_pro" {
  assignment_name   = "QuickSuiteAdminPro"
  assignment_status = "ENABLED"
  policy_arn        = aws_iam_policy.quicksuite_admin_pro.arn
  identities {
    group = [var.idc_groups.admin_pro]
  }
}

#// AuthorPro --------------------------------------------------------//#

data "aws_iam_policy_document" "quicksuite_author_pro" {
  statement {
    sid    = "QuickSuiteAuthorPro"
    effect = "Allow"
    actions = [
      "quicksight:Batch*",
      "quicksight:CreateActionConnector",
      "quicksight:CreateAnalysis",
      "quicksight:CreateDashboard",
      "quicksight:CreateDataSet",
      "quicksight:CreateDataSource",
      "quicksight:CreateFlowTemplate",
      "quicksight:CreateEmailCustomizationTemplate",
      "quicksight:CreateFolder",
      "quicksight:CreateFolderMembership",
      "quicksight:CreateIngestion",
      "quicksight:CancelIngestion",
      "quicksight:CreateNamespace",
      "quicksight:CreateTopic",
      "quicksight:CreateRefreshSchedule",
      "quicksight:CreateTopicRefreshSchedule",
      "quicksight:DeleteActionConnector",
      "quicksight:DeleteAnalysis",
      "quicksight:DeleteDashboard",
      "quicksight:DeleteDataSet",
      "quicksight:DeleteDataSource",
      "quicksight:DeleteFlowTemplate",
      "quicksight:DeleteEmailCustomizationTemplate",
      "quicksight:DeleteFolder",
      "quicksight:DeleteFolderMembership",
      "quicksight:DeleteIngestion",
      "quicksight:DeleteNamespace",
      "quicksight:DeleteTopic",
      "quicksight:DeleteRefreshSchedule",
      "quicksight:DeleteTopicRefreshSchedule",
      "quicksight:Describe*",
      "quicksight:List*",
      "quicksight:Get*",
      "quicksight:Search*",
      "quicksight:UpdateChatConfiguration",
      "qbusiness:Chat*",
      "qbusiness:CheckDocumentAccess",
      "qbusiness:Get*",
      "qbusiness:List*",
      "qbusiness:SearchRelevantContent"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "QuickSuiteAuthorProS3"
    effect = "Allow"
    actions = [
      "s3:*",
    ]
    resources = ["*"]

    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "aws:CalledVia"
      values   = ["quicksight.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = ["Quick"]
    }
  }

  statement {
    sid    = "QuickSuiteAuthorProCalledVia"
    effect = "Allow"
    actions = [
      "textract:*",
      "comprehend:*",
      "bedrock:*",
      "bedrock-agentcore:*",
      "bedrock-mantle:*",
      "logs:*",
      "kms:Decrypt"
    ]
    resources = ["*"]

    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "aws:CalledVia"
      values   = ["quicksight.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "quicksuite_author_pro" {
  name        = "QuickSuiteAuthorPro"
  description = "QuickSuite AuthorPro IAM policy."
  policy      = data.aws_iam_policy_document.quicksuite_author_pro.json

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_quicksight_iam_policy_assignment" "quicksuite_author_pro" {
  assignment_name   = "QuickSuiteAuthorPro"
  assignment_status = "ENABLED"
  policy_arn        = aws_iam_policy.quicksuite_author_pro.arn
  identities {
    group = [var.idc_groups.author_pro]
  }
}

#// Creator ----------------------------------------------------------//#

data "aws_iam_policy_document" "quicksuite_creator" {
  statement {
    sid    = "QuickSuiteCreator"
    effect = "Allow"
    actions = [
      "quicksight:BatchGetPreferences",
      "quicksight:Describe*",
      "quicksight:List*",
      "quicksight:Get*",
      "quicksight:Search*",
      "quicksight:UpdateChatConfiguration",
      "qbusiness:Chat*",
      "qbusiness:CheckDocumentAccess",
      "qbusiness:Get*",
      "qbusiness:List*",
      "qbusiness:SearchRelevantContent"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "QuickSuiteCreatorS3"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["*"]

    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "aws:CalledVia"
      values   = ["quicksight.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = ["Quick"]
    }
  }

  statement {
    sid    = "QuickSuiteCreatorCalledVia"
    effect = "Allow"
    actions = [
      "logs:List*",
      "logs:Get*",
      "textract:Analyze*",
      "textract:DetectDocumentText",
      "textract:Get*",
      "textract:List*",
      "comprehend:Batch*",
      "comprehend:ClassifyDocument",
      "comprehend:ContainsPiiEntities",
      "comprehend:Describe*",
      "comprehend:Detect*",
      "comprehend:List*",
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:InvokeTool",
      "bedrock:Get*",
      "bedrock:OptimizePrompt",
      "bedrock:Retrieve",
      "bedrock:RenderPrompt",
      "bedrock:ValidateFlowDefinition",
      "bedrock-agentcore:CompleteResourceTokenAuth",
      "bedrock-agentcore:Connect*",
      "bedrock-agentcore:Get*",
      "bedrock-agentcore:List*",
      "bedrock-agentcore:InvokeAgent*",
      "kms:Decrypt"
    ]
    resources = ["*"]

    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "aws:CalledVia"
      values   = ["quicksight.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "quicksuite_creator" {
  name        = "QuickSuiteCreator"
  description = "QuickSuite Creator IAM policy."
  policy      = data.aws_iam_policy_document.quicksuite_creator.json

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_quicksight_iam_policy_assignment" "quicksuite_creator" {
  assignment_name   = "QuickSuiteCreator"
  assignment_status = "ENABLED"
  policy_arn        = aws_iam_policy.quicksuite_creator.arn
  identities {
    group = [var.idc_groups.creator]
  }
}

#// General ----------------------------------------------------------//#

data "aws_iam_policy_document" "quicksuite_general" {
  statement {
    sid    = "QuickSuiteGeneral"
    effect = "Allow"
    actions = [
      "quicksight:BatchGetPreferences",
      "quicksight:Describe*",
      "quicksight:List*",
      "quicksight:Get*",
      "quicksight:Search*",
      "qbusiness:Chat*",
      "qbusiness:CheckDocumentAccess",
      "qbusiness:Get*",
      "qbusiness:List*",
      "qbusiness:SearchRelevantContent"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "QuickSuiteGeneralS3"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["*"]

    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "aws:CalledVia"
      values   = ["quicksight.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = ["Quick"]
    }
  }

  statement {
    sid    = "QuickSuiteGeneralCalledVia"
    effect = "Allow"
    actions = [
      "logs:List*",
      "logs:Get*",
      "textract:Analyze*",
      "textract:DetectDocumentText",
      "textract:Get*",
      "textract:List*",
      "comprehend:Batch*",
      "comprehend:ClassifyDocument",
      "comprehend:ContainsPiiEntities",
      "comprehend:Describe*",
      "comprehend:Detect*",
      "comprehend:List*",
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:InvokeTool",
      "bedrock:Get*",
      "bedrock:OptimizePrompt",
      "bedrock:Retrieve",
      "bedrock:RenderPrompt",
      "bedrock:ValidateFlowDefinition",
      "bedrock-agentcore:CompleteResourceTokenAuth",
      "bedrock-agentcore:Connect*",
      "bedrock-agentcore:Get*",
      "bedrock-agentcore:List*",
      "bedrock-agentcore:InvokeAgent*",
      "kms:Decrypt"
    ]
    resources = ["*"]

    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "aws:CalledVia"
      values   = ["quicksight.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "quicksuite_general" {
  name        = "QuickSuiteGeneral"
  description = "QuickSuite General IAM policy."
  policy      = data.aws_iam_policy_document.quicksuite_general.json

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_quicksight_iam_policy_assignment" "quicksuite_general" {
  assignment_name   = "QuickSuiteGeneral"
  assignment_status = "ENABLED"
  policy_arn        = aws_iam_policy.quicksuite_general.arn
  identities {
    group = [var.idc_groups.general]
  }
}
