output "table_name" {
  description = "Nome exclusivo da tabela acadêmica DynamoDB."
  value       = aws_dynamodb_table.activity.name
}

output "table_arn" {
  description = "ARN da tabela acadêmica DynamoDB."
  value       = aws_dynamodb_table.activity.arn
}

output "region" {
  description = "Região AWS do laboratório."
  value       = var.aws_region
}

output "gsi_name" {
  description = "Índice secundário global para consulta por tipo de evento e dia."
  value       = "EventTypeDayIndex"
}
