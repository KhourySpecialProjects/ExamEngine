resource "aws_security_group" "ec2" {
  name        = "examengine-ec2-${var.environment}"
  description = "Security group for ExamEngine EC2"

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  # HTTP
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "examengine-ec2-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Security group for RDS
resource "aws_security_group" "rds" {
  name        = "examengine-rds-${var.environment}"
  description = "Security group for ExamEngine RDS"

  # PostgreSQL access from EC2 only
  ingress {
    description     = "PostgreSQL from EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "examengine-rds-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
