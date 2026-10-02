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
  description = "IP público IPv4 do grupo no formato CIDR /32, autorizado a conectar ao PostgreSQL."
  type        = string

  validation {
    condition = can(
      cidrnetmask(var.allowed_client_ipv4_cidr) == "255.255.255.255"
    )
    error_message = "Informe somente o IP público do grupo, por exemplo 198.51.100.25/32."
  }
}

variable "vpc_cidr" {
  description = "Bloco IPv4 privado reservado para a VPC isolada do laboratório."
  type        = string
  default     = "10.73.0.0/16"

  validation {
    condition = can(cidrhost(var.vpc_cidr, 0)) && try(
      tonumber(split("/", var.vpc_cidr)[1]) == 16,
      false
    )
    error_message = "Informe um bloco IPv4 CIDR /16 válido para a VPC, pois as sub-redes do laboratório são /24."
  }
}

variable "availability_zone_count" {
  description = "Quantidade de zonas usadas para sub-redes e mount targets do EFS."
  type        = number
  default     = 2

  validation {
    condition = (
      var.availability_zone_count >= 2 &&
      var.availability_zone_count <= 3 &&
      floor(var.availability_zone_count) == var.availability_zone_count
    )
    error_message = "O laboratório usa de duas a três zonas de disponibilidade."
  }
}

variable "rds_instance_class" {
  description = "Classe da instância PostgreSQL. Confira a disponibilidade e os custos na região selecionada."
  type        = string
  default     = "db.t3.micro"
}

variable "rds_database_name" {
  description = "Nome inicial do banco PostgreSQL."
  type        = string
  default     = "storage_lab"

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{0,62}$", var.rds_database_name))
    error_message = "O nome do banco deve começar com uma letra e conter apenas letras, números e underscore."
  }
}

variable "rds_master_username" {
  description = "Usuário administrativo inicial do PostgreSQL. A senha é gerenciada pelo RDS/Secrets Manager."
  type        = string
  default     = "labadmin"

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{0,62}$", var.rds_master_username))
    error_message = "Use um nome de usuário PostgreSQL válido, começando com uma letra."
  }
}

variable "efs_test_instance_type" {
  description = "Tipo da EC2 temporária usada apenas para montar e testar o EFS pela V1."
  type        = string
  default     = "t3.micro"
}
