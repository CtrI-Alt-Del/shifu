resource "aws_secretsmanager_secret" "web" {
  name                    = "${local.name}/web"
  description             = "Web/BFF runtime configuration populated outside Terraform"
  recovery_window_in_days = var.purge_data ? 0 : 7

  tags = { Service = "web" }
}

resource "aws_secretsmanager_secret" "server" {
  name                    = "${local.name}/server"
  description             = "FastAPI runtime configuration populated outside Terraform"
  recovery_window_in_days = var.purge_data ? 0 : 7

  tags = { Service = "server" }
}
