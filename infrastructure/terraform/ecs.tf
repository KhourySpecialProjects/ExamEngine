resource "aws_ecs_cluster" "cluster" {
    name = "ee-cluster"
}

resource "aws_ecs_task_definition" "frontend-task" {
    family = "examengine-frontend"
    requires_compatibilities = ["FARGATE"]
    network_mode = "awsvpc"
    cpu = "512"
    memory = "1024"

    execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
    task_role_arn = aws_iam_role.ecs_task_role.arn 

    container_definitions = jsonencode([
        {
            name      = "frontend-repo"
            image     = "${data.aws_ecr_repository.frontend_repo.repository_url}:latest"
            essential = true
            environment = [
                {
                    name  = "NODE_ENV"
                    value = "production"
                },
                {
                    name  = "NEXT_PUBLIC_API_URL"
                    value = var.frontend_url != "" ? var.frontend_url : "http://${aws_lb.examengine.dns_name}"
                }
            ]
            portMappings = [
                {
                    containerPort = 3000
                    hostPort      = 3000
                    protocol      = "tcp"
                }
            ]
            logConfiguration = {
                logDriver = "awslogs"
                options = {
                    "awslogs-group"         = aws_cloudwatch_log_group.frontend_logs.name
                    "awslogs-region"        = var.aws_region
                    "awslogs-stream-prefix" = "frontend"
                }
            }
            healthCheck = {
                command     = ["CMD-SHELL", "curl -f http://localhost:3000 || exit 1"]
                interval    = 30
                timeout     = 5
                retries     = 5
                startPeriod = 60
            }
        }
    ])
}

resource "aws_ecs_task_definition" "backend-task" {
    family = "examengine-backend"
    requires_compatibilities = ["FARGATE"]
    network_mode = "awsvpc"
    
    execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
    task_role_arn = aws_iam_role.ecs_task_role.arn 
    cpu = "512"
    memory = "1024"

    container_definitions = jsonencode([
        {
            name      = "backend-repo"
            image     = "${data.aws_ecr_repository.backend_repo.repository_url}:latest"
            essential = true
            environment = [
                {
                    name  = "DATABASE_URL"
                    value = var.database_url
                },
                {
                    name  = "AWS_ACCESS_KEY_ID"
                    value = var.aws_access_key_id
                },
                {
                    name  = "AWS_SECRET_ACCESS_KEY"
                    value = var.aws_secret_access_key
                },
                {
                    name  = "AWS_REGION"
                    value = var.aws_region
                },
                {
                    name  = "AWS_S3_BUCKET"
                    value = var.bucket_name
                },
                {
                    name  = "SECRET_KEY"
                    value = var.secret_key
                },
                {
                    name  = "ENVIRONMENT"
                    value = "production"
                },
                {
                    name  = "DEBUG"
                    value = "false"
                },
                {
                    name  = "FRONTEND_URL"
                    value = var.frontend_url != "" ? var.frontend_url : "http://${aws_lb.examengine.dns_name}"
                }
            ]
            portMappings = [
                {
                    containerPort = 8000
                    hostPort      = 8000
                    protocol      = "tcp"
                }
            ]
            logConfiguration = {
                logDriver = "awslogs"
                options = {
                    "awslogs-group"         = aws_cloudwatch_log_group.backend_logs.name
                    "awslogs-region"        = var.aws_region
                    "awslogs-stream-prefix" = "backend"
                }
            }
            healthCheck = {
                command     = ["CMD-SHELL", "curl -f http://localhost:8000/docs || exit 1"]
                interval    = 30
                timeout     = 10
                retries     = 3
                startPeriod = 15
            }
        }
    ])
}


data "aws_ecr_repository" "frontend_repo" {
    name = "next-web"
}

data "aws_ecr_repository" "backend_repo" {
    name = "fastapi-backend"
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "backend_logs" {
    name              = "/ecs/examengine-backend-${var.environment}"
    retention_in_days = 7

    tags = {
        Name        = "examengine-backend-logs-${var.environment}"
        Environment = var.environment
        ManagedBy   = "Terraform"
    }
}

resource "aws_cloudwatch_log_group" "frontend_logs" {
    name              = "/ecs/examengine-frontend-${var.environment}"
    retention_in_days = 7

    tags = {
        Name        = "examengine-frontend-logs-${var.environment}"
        Environment = var.environment
        ManagedBy   = "Terraform"
    }
}
