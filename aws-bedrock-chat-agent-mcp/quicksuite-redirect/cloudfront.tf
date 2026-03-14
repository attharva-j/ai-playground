resource "aws_cloudfront_function" "redirect" {
  name    = "quicksuite-vanity-redirect"
  runtime = "cloudfront-js-2.0"
  code    = file("${path.module}/src/index.js")
}

module "cloudfront" {
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "~> 6.4.0"

  aliases = [var.redirect_zone]

  comment             = "QuickSuite Vanity Redirect"
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = "PriceClass_200"
  retain_on_delete    = false
  wait_for_deployment = false

  origin = {
    dummy = {
      domain_name = "<your-domain.com>"
      custom_origin_config = {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "https-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  default_cache_behavior = {
    target_origin_id       = "dummy"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD"]
    cached_methods  = ["GET", "HEAD"]
    compress        = true

    function_association = {
      viewer-request = {
        function_arn = aws_cloudfront_function.redirect.arn
      }
    }
  }

  viewer_certificate = {
    acm_certificate_arn = module.acm.acm_certificate_arn
    ssl_support_method  = "sni-only"
  }
}
