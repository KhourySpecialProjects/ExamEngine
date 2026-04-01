output "route53_nameservers" {
  description = "Add these as NS records in Porkbun"
  value       = module.examengine.route53_nameservers
}

output "website_url" {
  description = "URL of the application"
  value       = module.examengine.website_url
}

output "alb_dns_name" {
  description = "ALB DNS name (point your domain here)"
  value       = module.examengine.alb_dns_name
}

output "github_actions_role_arn" {
  description = "ARN of IAM role for GitHub Actions OIDC (add to GitHub repo settings as AWS_GITHUB_ACTIONS_ROLE_ARN)"
  value       = module.examengine.github_actions_role_arn
}

output "aws_account_id" {
  description = "AWS Account ID (add to GitHub Secrets as AWS_ACCOUNT_ID)"
  value       = module.examengine.aws_account_id
}

output "database_secret_arn" {
  description = "ARN of database URL secret in Secrets Manager"
  value       = module.examengine.database_secret_arn
}

output "secret_key_arn" {
  description = "ARN of application secret key in Secrets Manager"
  value       = module.examengine.secret_key_arn
}
