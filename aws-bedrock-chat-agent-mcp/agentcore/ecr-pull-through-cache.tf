data "sops_file" "docker_hub" {
  source_file = "${path.module}/secrets/docker-hub.${var.environment}.yaml"
}

module "docker_hub_secret" {
  source  = "hashicorp/aws"
  version = "~> 1.0"

  secrets = [
    {
      name                    = "ecr-pullthroughcache/docker"
      secret_key_value        = data.sops_file.docker_hub.data
      recovery_window_in_days = 7
    }
  ]
}

resource "aws_ecr_pull_through_cache_rule" "docker_hub" {
  ecr_repository_prefix = "docker-hub"
  upstream_registry_url = "registry-1.docker.io"
  credential_arn        = one(values(module.docker_hub_secret.secret_arns))
}
