variable "aws_region" {
  description = "Região AWS do laboratório acadêmico DynamoDB."
  type        = string
  default     = "us-east-2"

  validation {
    condition     = var.aws_region == "us-east-2"
    error_message = "O laboratório do grupo usa a região us-east-2."
  }
}

variable "project_name" {
  description = "Prefixo para nomear a tabela do laboratório."
  type        = string
  default     = "shifu-dynamodb-lab"

  validation {
    condition     = can(regex("^shifu-dynamodb-lab(-[a-z0-9]+)*$", var.project_name)) && length(var.project_name) <= 30
    error_message = "Use o prefixo shifu-dynamodb-lab, seguido opcionalmente por letras minúsculas, números e hífens."
  }
}
