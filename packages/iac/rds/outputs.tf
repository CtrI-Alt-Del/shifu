output "aws_region" {
  description = "Região AWS usada pelo laboratório."
  value       = var.aws_region
}

output "db_instance_identifier" {
  description = "Identificador da instância RDS."
  value       = aws_db_instance.rds_lab.identifier
}

output "db_endpoint" {
  description = "Endpoint (host) do PostgreSQL, sem a porta."
  value       = aws_db_instance.rds_lab.address
}

output "db_port" {
  description = "Porta do PostgreSQL."
  value       = aws_db_instance.rds_lab.port
}

output "db_name" {
  description = "Nome do banco criado na instância."
  value       = aws_db_instance.rds_lab.db_name
}

output "db_username" {
  description = "Usuário mestre do banco."
  value       = aws_db_instance.rds_lab.username
}

output "db_security_group_id" {
  description = "Security Group da instância, com uma única regra de entrada."
  value       = aws_security_group.rds_lab.id
}

output "allowed_cidr" {
  description = "IP público autorizado a acessar o banco."
  value       = var.allowed_cidr
}

output "db_master_password" {
  description = "Senha do usuário mestre. Sensível: não copie para o relatório nem para prints."
  value       = random_password.master.result
  sensitive   = true
}
