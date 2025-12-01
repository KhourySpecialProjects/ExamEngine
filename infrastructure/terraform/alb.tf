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

resource "aws_lb_target_group" "examengine" {
  name     = "examengine-${var.environment}"
  port     = 80
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 10
  }

  tags = {
    Name        = "examengine-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

data "aws_vpc" "default" {
  default = true
}

resource "aws_lb_target_group_attachment" "examengine" {
  target_group_arn = aws_lb_target_group.examengine.arn
  target_id        = aws_instance.examengine.id
  port             = 80
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.examengine.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.examengine.arn
  }
}
