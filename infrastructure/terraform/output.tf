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
