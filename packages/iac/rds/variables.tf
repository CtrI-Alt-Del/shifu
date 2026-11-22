variable "aws_region" {
  description = "Região AWS do laboratório RDS do Shifu."
  type        = string
  default     = "us-east-2"

  validation {
    condition     = var.aws_region == "us-east-2"
    error_message = "O laboratório RDS do Shifu usa a região us-east-2."
  }
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
  description = "Versão principal do PostgreSQL usada pelo staging do Shifu."
  type        = string
  default     = "17"

  validation {
    condition     = can(regex("^17(\\.[0-9]+)?$", var.engine_version))
    error_message = "O laboratório usa PostgreSQL 17: informe '17' ou '17.<menor>'."
  }
}

variable "instance_class" {
  description = "Classe da instância usada pelo staging do Shifu."
  type        = string
  default     = "db.t4g.micro"

  validation {
    condition     = var.instance_class == "db.t4g.micro"
    error_message = "O laboratório usa a classe db.t4g.micro, igual ao staging."
  }
}

variable "db_master_password" {
  description = "Senha efêmera do usuário mestre. Forneça por TF_VAR_db_master_password no processo local."
  type        = string
  sensitive   = true
  ephemeral   = true

  validation {
    condition     = length(var.db_master_password) >= 16 && length(var.db_master_password) <= 41
    error_message = "A senha temporária deve ter entre 16 e 41 caracteres."
  }
}
