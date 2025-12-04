resource "aws_ecs_cluster" "cluster" {
  name = "ee-cluster"
}

resource "aws_ecs_task_definition" "frontend-task" {
  family                   = "examengine-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn

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
          value = var.frontend_url != "" ? "${var.frontend_url}/api" : "http://${aws_lb.examengine.dns_name}/api"
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
  family                   = "examengine-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn
  cpu                = "512"
  memory             = "1024"

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

resource "aws_ecs_task_definition" "backend-add-admin-task" {
  family                   = "examengine-backend-add-admin"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn
  cpu                = "512"
  memory             = "1024"

  container_definitions = jsonencode([
    {
      name      = "backend-add-admin"
      image     = "${data.aws_ecr_repository.backend_repo.repository_url}:latest"
      essential = true

      command = ["python", "script/add_admin.py"]

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

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend-add-admin"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "backend-reset-db-task" {
  family                   = "examengine-backend-reset-db"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn
  cpu                = "512"
  memory             = "1024"

  container_definitions = jsonencode([
    {
      name      = "backend-reset-db"
      image     = "${data.aws_ecr_repository.backend_repo.repository_url}:latest"
      essential = true

      # Run the database reset script instead of the API server
      command = ["python", "src/schemas/reset_database.py"]

      environment = [
        {
          name  = "DATABASE_URL"
          value = var.database_url
        },
        # Ensure Python can import `db` module from src/schemas
        {
          name  = "PYTHONPATH"
          value = "/app/src/schemas"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend-reset-db"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "backend-drop-conflicts-table-task" {
  family                   = "examengine-backend-drop-conflicts"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn
  cpu                = "256"
  memory             = "512"

  container_definitions = jsonencode([
    {
      name      = "backend-drop-conflicts"
      image     = "${data.aws_ecr_repository.backend_repo.repository_url}:latest"
      essential = true

      # Use Python to drop legacy tables that aren't in current schema
      command = [
        "python", "-c",
        "import os; from sqlalchemy import create_engine, text; engine = create_engine(os.getenv('DATABASE_URL')); conn = engine.connect(); conn.execute(text('DROP TABLE IF EXISTS conflicts CASCADE')); conn.execute(text('DROP TABLE IF EXISTS students CASCADE')); conn.commit(); conn.close(); print('✅ Dropped legacy tables (conflicts, students)')"
      ]

      environment = [
        {
          name  = "DATABASE_URL"
          value = var.database_url
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend-drop-conflicts"
        }
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

resource "aws_security_group" "ecs_tasks" {
  name        = "examengine-ecs-tasks-${var.environment}"
  description = "Security group for ECS tasks"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Frontend from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Backend from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "examengine-ecs-tasks-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ECS Service for Frontend
resource "aws_ecs_service" "frontend" {
  name            = "examengine-frontend-service-${var.environment}"
  cluster         = aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.frontend-task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend-repo"
    container_port   = 3000
  }

  health_check_grace_period_seconds = 60

  depends_on = [
    aws_lb_listener.http,
    aws_iam_role_policy_attachment.ecs_exec_policy_attach
  ]

  tags = {
    Name        = "examengine-frontend-service-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ECS Service for Backend
resource "aws_ecs_service" "backend" {
  name            = "examengine-backend-service-${var.environment}"
  cluster         = aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.backend-task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend-repo"
    container_port   = 8000
  }

  health_check_grace_period_seconds = 60

  depends_on = [
    aws_lb_listener.http,
    aws_iam_role_policy_attachment.ecs_exec_policy_attach
  ]

  tags = {
    Name        = "examengine-backend-service-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
