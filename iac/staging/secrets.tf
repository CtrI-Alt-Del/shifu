resource "aws_secretsmanager_secret" "web" {
  name                    = "${local.name}/web"
  description             = "Web/BFF runtime configuration populated outside Terraform"
  recovery_window_in_days = var.purge_data ? 0 : 7

  tags = { Service = "web" }
}

resource "aws_secretsmanager_secret" "api" {
  name                    = "${local.name}/api"
  description             = "FastAPI runtime configuration populated outside Terraform"
  recovery_window_in_days = var.purge_data ? 0 : 7

  tags = { Service = "api" }
}
