resource "aws_db_instance" "examengine" {
  identifier = "examengine-${var.environment}"

  # Engine
  engine         = "postgres"
  engine_version = "15"

  # Size
  instance_class    = var.db_instance_class
  allocated_storage = 20
  storage_type      = "gp3"

  # Database
  db_name  = "exam_engine_db"
  username = var.db_username
  password = var.db_password

  # Network
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  skip_final_snapshot    = var.environment != "prod"

  tags = {
    Name        = "examengine-db-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
