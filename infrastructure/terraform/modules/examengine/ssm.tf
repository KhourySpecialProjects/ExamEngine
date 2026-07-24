resource "aws_ssm_parameter" "cluster_name" {
  name  = "/examengine/${var.environment}/cluster-name"
  type  = "String"
  value = aws_ecs_cluster.cluster.name

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_ssm_parameter" "backend_service" {
  name  = "/examengine/${var.environment}/backend-service"
  type  = "String"
  value = aws_ecs_service.backend.name

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_ssm_parameter" "frontend_service" {
  name  = "/examengine/${var.environment}/frontend-service"
  type  = "String"
  value = aws_ecs_service.frontend.name

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_ssm_parameter" "backend_repo_uri" {
  name  = "/examengine/${var.environment}/backend-repo-uri"
  type  = "String"
  value = data.aws_ecr_repository.backend_repo.repository_url

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_ssm_parameter" "frontend_repo_uri" {
  name  = "/examengine/${var.environment}/frontend-repo-uri"
  type  = "String"
  value = data.aws_ecr_repository.frontend_repo.repository_url

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_ssm_parameter" "domain_name" {
  name  = "/examengine/${var.environment}/domain-name"
  type  = "String"
  value = var.domain_name

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
