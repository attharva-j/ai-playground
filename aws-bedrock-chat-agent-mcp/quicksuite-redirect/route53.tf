resource "aws_route53_delegation_set" "this" {
  reference_name = "QuickSuiteRedirect"
}

resource "aws_route53_zone" "managed" {
  for_each          = var.zone_names
  name              = each.key
  comment           = "Domain for the QuickSuite vanity redirect"
  delegation_set_id = aws_route53_delegation_set.this.id
}

resource "aws_route53_record" "cloudfront" {
  zone_id = aws_route53_zone.managed[var.redirect_zone].zone_id
  name    = var.redirect_zone
  type    = "A"

  alias {
    name                   = module.cloudfront.cloudfront_distribution_domain_name
    zone_id                = module.cloudfront.cloudfront_distribution_hosted_zone_id
    evaluate_target_health = false
  }
}
