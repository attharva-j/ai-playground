data "aws_iam_openid_connect_provider" "github_actions" {
  arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

resource "aws_iam_role_policy" "gh_actions_policy" {
  name = "container-builder-policy"
  role = aws_iam_role.gh_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:DescribeRepositories",
          "ecr:ListImages",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:CreateRepository",
          "ecr:PutLifecyclePolicy",
          "ecr:TagResource",
          "ecr:BatchImportUpstreamImage",
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "bedrock-agentcore:UpdateAgentRuntime"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:ecr-pullthroughcache/docker-*"
      },
      {
        Sid      = "PassAgentCoreRuntimeExecutionRole"
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = aws_iam_role.agent_runtime.arn
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "bedrock-agentcore.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "gh_actions" {
  name = "gh-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.github_actions.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:<github-org>/ai-foundation:*"
          }
        }
      }
    ]
  })
}
