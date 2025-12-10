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
