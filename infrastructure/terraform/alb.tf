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

# Target group for backend (port 8000)
resource "aws_lb_target_group" "backend" {
  name     = "examengine-backend-${var.environment}"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

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

# Target group for frontend (port 3000)
resource "aws_lb_target_group" "frontend" {
  name     = "examengine-frontend-${var.environment}"
  port     = 3000
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

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

# Register EC2 with backend target group
resource "aws_lb_target_group_attachment" "backend" {
  target_group_arn = aws_lb_target_group.backend.arn
  target_id        = aws_instance.examengine.id
  port             = 8000
}

# Register EC2 with frontend target group
resource "aws_lb_target_group_attachment" "frontend" {
  target_group_arn = aws_lb_target_group.frontend.arn
  target_id        = aws_instance.examengine.id
  port             = 3000
}

# ALB Listener on port 80
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
