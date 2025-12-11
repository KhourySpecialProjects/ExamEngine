data "aws_acm_certificate" "examengine" {
  domain   = "theexameengine.nunext.dev"
  statuses = ["ISSUED"]
}
