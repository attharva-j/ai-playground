module "acm" {
  source  = "terraform-aws-modules/acm/aws"
  version = "~> 6.3.0"

  domain_name = var.redirect_zone
  zone_id     = aws_route53_zone.managed[var.redirect_zone].id

  validation_method = "DNS"

  wait_for_validation = true
}
