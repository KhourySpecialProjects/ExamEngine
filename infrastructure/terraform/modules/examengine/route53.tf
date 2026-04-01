# Route53 Hosted Zone
resource "aws_route53_zone" "main" {
  name = var.domain_name

  tags = {
    Name        = "examengine-${var.domain_name}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# A record pointing domain to ALB
resource "aws_route53_record" "alb" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.examengine.dns_name
    zone_id                = aws_lb.examengine.zone_id
    evaluate_target_health = true
  }
}
