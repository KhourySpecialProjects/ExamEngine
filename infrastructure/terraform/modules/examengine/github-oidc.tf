# GitHub Actions OIDC Provider
# Allows GitHub Actions to assume IAM roles without long-lived credentials

# OIDC Provider for GitHub
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",  # GitHub's certificate thumbprint
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"   # Backup thumbprint
  ]

  tags = {
    Name        = "github-actions-oidc-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IAM Role for GitHub Actions
resource "aws_iam_role" "github_actions" {
  name = "examengine-github-actions-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:KhourySpecialProjects/ExamEngine:ref:refs/heads/${var.deploy_branch}"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "examengine-github-actions-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Policy for GitHub Actions (ECR + ECS permissions)
resource "aws_iam_role_policy" "github_actions_policy" {
  name = "examengine-github-actions-policy-${var.environment}"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRGetAuthorizationToken"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECRPushPullImages"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = [
          data.aws_ecr_repository.frontend_repo.arn,
          data.aws_ecr_repository.backend_repo.arn
        ]
      },
      {
        Sid    = "ECSUpdateService"
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices"
        ]
        Resource = [
          "arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:service/${aws_ecs_cluster.cluster.name}/*"
        ]
      },
      {
        Sid    = "ECSDescribeCluster"
        Effect = "Allow"
        Action = [
          "ecs:DescribeClusters"
        ]
        Resource = [
          aws_ecs_cluster.cluster.arn
        ]
      },
      {
        Sid    = "SSMGetParameters"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/examengine/${var.environment}/*"
        ]
      }
    ]
  })
}
