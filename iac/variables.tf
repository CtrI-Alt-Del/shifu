variable "aws_region" {
  description = "Região AWS do laboratório. Ajuste conforme a conta e a região escolhida pelo grupo."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefixo curto, minúsculo e sem espaços para nomear os recursos."
  type        = string
  default     = "shifu-storage-lab"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,39}$", var.project_name))
    error_message = "Use de 3 a 40 caracteres: letras minúsculas, números e hífens; comece com letra ou número."
  }
}

variable "allowed_client_ipv4_cidr" {
  description = "IPv4 pública atual do grupo em formato /32; única origem autorizada ao PostgreSQL."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.allowed_client_ipv4_cidr)) && try(tonumber(split("/", var.allowed_client_ipv4_cidr)[1]) == 32, false)
    error_message = "Informe o IP público atual do grupo como CIDR /32, por exemplo 198.51.100.25/32."
  }
}

variable "vpc_cidr" {
  description = "Bloco IPv4 da VPC isolada do laboratório."
  type        = string
  default     = "10.73.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr)) && try(tonumber(split("/", var.vpc_cidr)[1]) == 16, false)
    error_message = "Informe um bloco IPv4 CIDR /16 válido para a VPC do laboratório."
  }
}

variable "availability_zone_count" {
  description = "Quantidade de zonas de disponibilidade usadas pelas sub-redes do RDS."
  type        = number
  default     = 2

  validation {
    condition = (
      var.availability_zone_count >= 2 &&
      var.availability_zone_count <= 3 &&
      floor(var.availability_zone_count) == var.availability_zone_count
    )
    error_message = "O grupo de sub-redes do RDS precisa de duas ou três zonas de disponibilidade."
  }
}

variable "rds_instance_class" {
  description = "Classe single-AZ compacta para o laboratório; confirme disponibilidade e preço na região."
  type        = string
  default     = "db.t3.micro"
}

variable "rds_database_name" {
  description = "Nome do banco PostgreSQL criado pelo RDS."
  type        = string
  default     = "storage_lab"

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{0,62}$", var.rds_database_name))
    error_message = "O nome do banco deve começar com uma letra e conter apenas letras, números e underscore."
  }
}

variable "rds_master_username" {
  description = "Usuário administrativo inicial do RDS; a senha é gerenciada pelo Secrets Manager."
  type        = string
  default     = "labadmin"

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{0,62}$", var.rds_master_username))
    error_message = "Use um nome de usuário PostgreSQL válido, começando com uma letra."
  }
}
