output "alb_dns_name" {
  description = "ALB DNS name for the operator-managed hostname record."
  value       = aws_lb.staging.dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster used for services and the one-off migration task."
  value       = aws_ecs_cluster.staging.name
}

output "web_service_name" {
  description = "Web ECS service name."
  value       = aws_ecs_service.web.name
}

output "api_service_name" {
  description = "API ECS service name."
  value       = aws_ecs_service.api.name
}

output "api_task_definition_arn" {
  description = "Server task definition used with an Alembic command override."
  value       = aws_ecs_task_definition.api.arn
}

output "application_subnet_ids" {
  description = "Private application subnet IDs for services and migration tasks."
  value       = aws_subnet.application[*].id
}

output "api_security_group_id" {
  description = "API security group used by the one-off migration task."
  value       = aws_security_group.api.id
}

output "web_repository_url" {
  description = "Private ECR repository URL for Web images."
  value       = aws_ecr_repository.web.repository_url
}

output "api_repository_url" {
  description = "Private ECR repository URL for API images."
  value       = aws_ecr_repository.api.repository_url
}

output "web_secret_arn" {
  description = "Web secret metadata ARN; values are populated outside Terraform."
  value       = aws_secretsmanager_secret.web.arn
}

output "api_secret_arn" {
  description = "API secret metadata ARN; values are populated outside Terraform."
  value       = aws_secretsmanager_secret.api.arn
}

output "rds_master_secret_arn" {
  description = "AWS-managed RDS master secret ARN for private operator use."
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}

output "api_private_dns_name" {
  description = "Private Cloud Map name used only inside the VPC."
  value       = local.api_discovery_name
}

output "services_enabled" {
  description = "Whether the services are configured for one desired task each."
  value       = var.services_enabled
}
