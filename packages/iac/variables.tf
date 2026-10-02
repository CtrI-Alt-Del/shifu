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
