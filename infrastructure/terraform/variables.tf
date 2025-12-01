variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# S3
variable "bucket_name" {
  description = "S3 bucket name for datasets"
  type        = string
}

# EC2
variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed to SSH"
  type        = string
  default     = "0.0.0.0/0" # Restrict this in production!
}

# RDS
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true #hidden in logs (same w all sensitive fields)
}

variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
}

variable "aws_access_key_id" {
  description = "AWS Access Key ID"
  type        = string
  sensitive   = true
}

variable "aws_secret_access_key" {
  description = "AWS Secret Access Key"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Secret key for backend application"
  type        = string
  sensitive   = true
}

variable "frontend_url" {
  description = "Frontend URL for CORS configuration"
  type        = string
  default     = "" # Will be constructed from ALB if not provided
}
