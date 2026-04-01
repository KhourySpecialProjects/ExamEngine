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
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Encryption
  storage_encrypted = true

  # Backups
  backup_retention_period = 7
  skip_final_snapshot     = false
  final_snapshot_identifier = "examengine-final-${var.environment}-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Migration safety: Create new RDS before destroying old one
  lifecycle {
    create_before_destroy = true
    ignore_changes = [final_snapshot_identifier]
  }

  tags = {
    Name        = "examengine-db-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
