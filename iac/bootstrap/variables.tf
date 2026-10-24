variable "aws_region" {
  description = "AWS region for the staging state bucket."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "The staging backend must be created in us-east-1."
  }
}

variable "state_bucket_name" {
  description = "Globally unique S3 bucket name for Terraform state."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.state_bucket_name))
    error_message = "state_bucket_name must be a valid globally unique S3 bucket name."
  }
}

variable "purge_backend" {
  description = "Explicitly permit deletion of a non-empty backend bucket during final teardown."
  type        = bool
  default     = false
}

variable "operator_principal_arns" {
  description = "Optional IAM principal ARNs allowed to access state in addition to the applying identity."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.operator_principal_arns : can(regex("^arn:aws:iam::[0-9]{12}:(role|user)/", arn))
    ])
    error_message = "Every operator principal must be an AWS IAM role or user ARN."
  }
}

variable "additional_tags" {
  description = "Additional non-secret tags for the backend resources."
  type        = map(string)
  default     = {}
}
