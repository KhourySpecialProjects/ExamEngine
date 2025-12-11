resource "aws_lb" "examengine" {
  name               = "examengine-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.default.ids

  tags = {
    Name        = "examengine-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

data "aws_subnets" "default" {
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_vpc" "default" {
  default = true
}

resource "aws_lb_target_group" "backend" {
  name        = "examengine-backend-ip-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip" # Required for ECS Fargate with awsvpc network mode

  lifecycle {
    create_before_destroy = true
  }

  health_check {
    path                = "/docs"
    port                = "8000"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 5
    interval            = 30
  }

  tags = {
    Name        = "examengine-backend-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_lb_target_group" "frontend" {
  name        = "examengine-frontend-ip-${var.environment}"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  lifecycle {
    create_before_destroy = true
  }

  health_check {
    path                = "/"
    port                = "3000"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 5
    interval            = 30
  }

  tags = {
    Name        = "examengine-frontend-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Note: Target group attachments are now handled by ECS services
# EC2 target group attachments removed - ECS services will register tasks automatically

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.examengine.arn
  port              = 80
  protocol          = "HTTP"

  # Default - send to frontend
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.examengine.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = data.aws_acm_certificate.examengine.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_listener_rule" "api_https" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}

# Rule for /api/* - send to backend
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}
