variable "aws_region" {
  description = "Região AWS do laboratório. Ajuste conforme a conta e a região escolhida pelo grupo."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefixo curto, minúsculo e sem espaços para nomear os recursos."
  type        = string
  default     = "shifu-rds-lab"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]*(-[a-z0-9]+)*$", var.project_name)) && length(var.project_name) >= 3 && length(var.project_name) <= 40
    error_message = "Use de 3 a 40 caracteres: letras minúsculas, números e hífens; comece com letra, sem hífen no fim nem hífens seguidos."
  }
}

variable "allowed_cidr" {
  description = "Único IP público autorizado a acessar o PostgreSQL, em formato /32. Exemplo: 203.0.113.10/32."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{1,3}(\\.[0-9]{1,3}){3}/32$", var.allowed_cidr)) && can(cidrhost(var.allowed_cidr, 0))
    error_message = "Informe um único IPv4 válido com máscara /32, por exemplo 203.0.113.10/32."
  }

  validation {
    condition     = !contains(["0.0.0.0/0", "0.0.0.0/32"], var.allowed_cidr)
    error_message = "O banco não pode ficar aberto à internet: informe o IP público do grupo, não 0.0.0.0."
  }
}

variable "engine_version" {
  description = "Versão do PostgreSQL. Use '16' para a versão menor padrão do RDS ou fixe uma versão listada pela AWS CLI, como '16.x'."
  type        = string
  default     = "16"

  validation {
    condition     = can(regex("^16(\\.[0-9]+)?$", var.engine_version))
    error_message = "O laboratório usa PostgreSQL 16: informe '16' ou '16.<menor>'."
  }
}

variable "instance_class" {
  description = "Classe da instância. O laboratório usa db.t3.micro; confirme a elegibilidade e o custo na conta do grupo."
  type        = string
  default     = "db.t3.micro"
}
