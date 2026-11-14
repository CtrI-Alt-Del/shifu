output "alb_dns_name" {
  description = "ALB DNS name for the operator-managed hostname record."
  value       = aws_lb.staging.dns_name
}

output "public_origin" {
  description = "Public base URL of staging: the hostname over HTTPS, or the ALB address over plain HTTP."
  value       = local.public_origin
}

output "deployer_user_name" {
  description = "IAM user for the GitHub Actions app deploy. Create its access key in the IAM console."
  value       = aws_iam_user.deployer.name
}

output "terraform_user_name" {
  description = "IAM user for the GitHub Actions Terraform apply. Create its access key in the IAM console."
  value       = aws_iam_user.terraform.name
}

output "ecs_cluster_name" {
  description = "ECS cluster used for services and the one-off migration task."
  value       = aws_ecs_cluster.staging.name
}

output "web_service_name" {
  description = "Web ECS service name."
  value       = aws_ecs_service.web.name
}

output "server_service_name" {
  description = "Server ECS service name."
  value       = aws_ecs_service.server.name
}

output "server_task_definition_arn" {
  description = "Server task definition used with an Alembic command override."
  value       = aws_ecs_task_definition.server.arn
}

output "application_subnet_ids" {
  description = "Private application subnet IDs for services and migration tasks."
  value       = aws_subnet.application[*].id
}

output "server_security_group_id" {
  description = "Server security group used by the one-off migration task."
  value       = aws_security_group.server.id
}

output "web_repository_url" {
  description = "Private ECR repository URL for Web images."
  value       = aws_ecr_repository.web.repository_url
}

output "server_repository_url" {
  description = "Private ECR repository URL for server images."
  value       = aws_ecr_repository.server.repository_url
}

output "web_secret_arn" {
  description = "Web secret metadata ARN; values are populated outside Terraform."
  value       = aws_secretsmanager_secret.web.arn
}

output "server_secret_arn" {
  description = "Server secret metadata ARN; values are populated outside Terraform."
  value       = aws_secretsmanager_secret.server.arn
}

output "rds_master_secret_arn" {
  description = "AWS-managed RDS master secret ARN for private operator use."
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}

output "server_private_dns_name" {
  description = "Private Cloud Map name used only inside the VPC."
  value       = local.server_discovery_name
}

output "services_enabled" {
  description = "Whether the services are configured for one desired task each."
  value       = var.services_enabled
}
