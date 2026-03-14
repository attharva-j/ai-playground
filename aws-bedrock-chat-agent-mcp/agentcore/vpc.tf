data "aws_vpc" "selected" {
  id = var.existing_vpc_id
}

resource "aws_security_group" "agentcore_runtime" {
  count = local.is_production && length(var.existing_security_group_ids) == 0 ? 1 : 0

  name        = "${local.name_prefix}-agentcore-runtime-sg"
  description = "Security group for AgentCore runtime in VPC mode (internet enabled)"
  vpc_id      = data.aws_vpc.selected.id

  ingress {
    description      = "Allow HTTPS from Internet"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-agentcore-runtime-sg"
  }
}

locals {
  is_production = contains(["prod", "production"], lower(var.environment))

  vpc_id             = data.aws_vpc.selected.id
  private_subnet_ids = var.existing_private_subnet_ids
  public_subnet_ids  = var.existing_public_subnet_ids

  agent_runtime_security_group_ids = length(var.existing_security_group_ids) > 0 ? var.existing_security_group_ids : (
    local.is_production ? [aws_security_group.agentcore_runtime[0].id] : []
  )
}
