output "bucket_name" {
  value = aws_s3_bucket.examengine_datasets.bucket
}

output "rds_endpoint" {
  value = aws_db_instance.examengine.endpoint
}

output "rds_database_name" {
  value = aws_db_instance.examengine.db_name
}
output "alb_dns_name" {
  value = aws_lb.examengine.dns_name
}

output "cicd_user_access_key_id" {
  description = "Access Key ID for CI/CD user (add to GitHub Secrets as AWS_ACCESS_KEY_ID)"
  value       = aws_iam_access_key.cicd_user_key.id
  sensitive   = false
}

output "cicd_user_secret_access_key" {
  description = "Secret Access Key for CI/CD user (add to GitHub Secrets as AWS_SECRET_ACCESS_KEY)"
  value       = aws_iam_access_key.cicd_user_key.secret
  sensitive   = true
}

output "aws_account_id" {
  description = "AWS Account ID (add to GitHub Secrets as AWS_ACCOUNT_ID)"
  value       = data.aws_caller_identity.current.account_id
}

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets (ALB)"
  value       = aws_subnet.public[*].id
}

output "private_app_subnet_ids" {
  description = "IDs of private app subnets (ECS)"
  value       = aws_subnet.private_app[*].id
}

output "private_db_subnet_ids" {
  description = "IDs of private DB subnets (RDS)"
  value       = aws_subnet.private_db[*].id
}

output "nat_gateway_ips" {
  description = "Elastic IPs of NAT Gateways"
  value       = aws_eip.nat[*].public_ip
}

# DNS Output
output "website_url" {
  description = "URL of the application"
  value       = "https://theexameengine.nunext.dev"
}
