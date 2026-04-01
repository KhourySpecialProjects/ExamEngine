resource "aws_acm_certificate" "examengine" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name        = "examengine-cert-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Create DNS validation records in Route53
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.examengine.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = aws_route53_zone.main.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

# Wait for certificate to be validated before ALB can use it
resource "aws_acm_certificate_validation" "examengine" {
  certificate_arn         = aws_acm_certificate.examengine.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}
