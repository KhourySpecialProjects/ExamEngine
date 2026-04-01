data "aws_acm_certificate" "examengine" {
  domain   = var.domain_name
  statuses = ["ISSUED"]
}
