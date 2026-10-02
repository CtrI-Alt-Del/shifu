output "aws_region" {
  description = "Região AWS usada pelo laboratório."
  value       = var.aws_region
}

output "s3_bucket_name" {
  description = "Bucket S3 do laboratório."
  value       = aws_s3_bucket.storage_lab.bucket
}

output "s3_public_demo_url" {
  description = "URL do único objeto público de demonstração."
  value       = "https://${aws_s3_bucket.storage_lab.bucket_regional_domain_name}/academic/storage-activity/public/exemplo.txt"
}

output "vpc_id" {
  description = "VPC isolada usada pelo RDS do laboratório."
  value       = aws_vpc.storage_lab.id
}

output "rds_instance_identifier" {
  description = "Identificador da instância PostgreSQL."
  value       = aws_db_instance.storage_lab.identifier
}

output "rds_address" {
  description = "Endpoint DNS do RDS, sem credenciais."
  value       = aws_db_instance.storage_lab.address
}

output "rds_port" {
  description = "Porta PostgreSQL."
  value       = aws_db_instance.storage_lab.port
}

output "rds_database_name" {
  description = "Nome do banco inicial no RDS."
  value       = aws_db_instance.storage_lab.db_name
}

output "rds_engine_version" {
  description = "Versão efetivamente selecionada pelo RDS para PostgreSQL."
  value       = aws_db_instance.storage_lab.engine_version_actual
}

output "rds_instance_class" {
  description = "Classe da instância RDS."
  value       = aws_db_instance.storage_lab.instance_class
}

output "rds_multi_az" {
  description = "Indica se o laboratório usa implantação Multi-AZ."
  value       = aws_db_instance.storage_lab.multi_az
}

output "rds_allocated_storage_gib" {
  description = "Armazenamento alocado para o banco, em GiB."
  value       = aws_db_instance.storage_lab.allocated_storage
}

output "rds_master_username" {
  description = "Usuário administrativo inicial do RDS."
  value       = aws_db_instance.storage_lab.username
}

output "rds_master_user_secret_arn" {
  description = "ARN do segredo da senha mestre gerenciado pelo RDS no Secrets Manager."
  value       = aws_db_instance.storage_lab.master_user_secret[0].secret_arn
}

output "dynamodb_table_name" {
  description = "Tabela DynamoDB que registra os eventos fictícios de usuários."
  value       = aws_dynamodb_table.events.name
}

output "dynamodb_gsi_name" {
  description = "Índice secundário global para consulta por tipo e data do evento."
  value       = "event-type-occurred-at-index"
}
