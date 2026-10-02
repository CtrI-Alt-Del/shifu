output "aws_region" {
  description = "Região AWS usada pelo laboratório."
  value       = var.aws_region
}

output "vpc_id" {
  description = "VPC isolada do laboratório."
  value       = aws_vpc.storage_lab.id
}

output "s3_bucket_name" {
  description = "Bucket S3 do laboratório."
  value       = aws_s3_bucket.storage_lab.bucket
}

output "s3_public_demo_url" {
  description = "URL do único objeto público de demonstração."
  value       = "https://${aws_s3_bucket.storage_lab.bucket_regional_domain_name}/academic/storage-activity/public/exemplo.txt"
}

output "dynamodb_table_name" {
  description = "Tabela DynamoDB de eventos fictícios."
  value       = aws_dynamodb_table.events.name
}

output "dynamodb_gsi_name" {
  description = "Índice secundário global da tabela de eventos."
  value       = "event-type-occurred-at-index"
}

output "rds_instance_identifier" {
  description = "Identificador da instância PostgreSQL."
  value       = aws_db_instance.storage_lab.identifier
}

output "rds_address" {
  description = "Endpoint DNS do PostgreSQL, sem credenciais."
  value       = aws_db_instance.storage_lab.address
}

output "rds_port" {
  description = "Porta PostgreSQL."
  value       = aws_db_instance.storage_lab.port
}

output "rds_database_name" {
  description = "Nome inicial do banco PostgreSQL."
  value       = aws_db_instance.storage_lab.db_name
}

output "rds_master_username" {
  description = "Usuário administrativo inicial do PostgreSQL."
  value       = aws_db_instance.storage_lab.username
}

output "rds_master_user_secret_arn" {
  description = "ARN do segredo gerenciado pelo RDS no Secrets Manager."
  value       = aws_db_instance.storage_lab.master_user_secret[0].secret_arn
}

output "efs_file_system_id" {
  description = "ID do sistema de arquivos EFS."
  value       = aws_efs_file_system.storage_lab.id
}

output "efs_access_point_id" {
  description = "Access point usado para montar o diretório do laboratório."
  value       = aws_efs_access_point.storage_lab.id
}

output "efs_test_instance_id" {
  description = "ID da EC2 temporária, acessível por AWS Systems Manager."
  value       = aws_instance.efs_test_client.id
}

output "efs_test_instance_public_ip" {
  description = "IP público da EC2 de teste; não há regra de entrada SSH."
  value       = aws_instance.efs_test_client.public_ip
}

output "efs_ssm_session_command" {
  description = "Comando para abrir uma sessão SSM com a EC2 de teste."
  value       = "aws ssm start-session --target ${aws_instance.efs_test_client.id} --region ${var.aws_region}"
}
