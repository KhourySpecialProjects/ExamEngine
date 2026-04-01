# AWS Secrets Manager
# Stores sensitive credentials securely (DATABASE_URL, SECRET_KEY)

# Database URL Secret
resource "aws_secretsmanager_secret" "database_url" {
  name        = "examengine/${var.environment}/database-url"
  description = "PostgreSQL connection string for ExamEngine"

  tags = {
    Name        = "examengine-database-url-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = var.database_url
}

# Application Secret Key (JWT signing)
resource "aws_secretsmanager_secret" "secret_key" {
  name        = "examengine/${var.environment}/secret-key"
  description = "JWT secret key for ExamEngine backend"

  tags = {
    Name        = "examengine-secret-key-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_secretsmanager_secret_version" "secret_key" {
  secret_id     = aws_secretsmanager_secret.secret_key.id
  secret_string = var.secret_key
}

# IAM Policy for ECS tasks to read secrets
resource "aws_iam_role_policy" "ecs_secrets_policy" {
  name = "examengine-ecs-secrets-policy-${var.environment}"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.database_url.arn,
          aws_secretsmanager_secret.secret_key.arn
        ]
      }
    ]
  })
}
