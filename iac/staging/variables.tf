variable "aws_region" {
  description = "AWS region for staging resources."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "The contracted staging region is us-east-1."
  }
}

variable "project_name" {
  description = "Short project name used in resource names and tags."
  type        = string
  default     = "shifu"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,20}$", var.project_name))
    error_message = "project_name must be a short lowercase slug."
  }
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "staging"

  validation {
    condition     = var.environment == "staging"
    error_message = "This root is intentionally limited to staging."
  }
}

variable "vpc_cidr" {
  description = "Private /16 CIDR for the staging VPC."
  type        = string
  default     = "10.20.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0)) && endswith(var.vpc_cidr, "/16")
    error_message = "vpc_cidr must be a valid /16 CIDR."
  }
}

variable "availability_zones" {
  description = "Exactly two available us-east-1 availability zones."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]

  validation {
    condition = (
      length(var.availability_zones) == 2 &&
      length(distinct(var.availability_zones)) == 2 &&
      alltrue([for az in var.availability_zones : startswith(az, "us-east-1")])
    )
    error_message = "Provide exactly two distinct us-east-1 availability zones."
  }
}

variable "public_subnet_cidrs" {
  description = "One public subnet CIDR per availability zone."
  type        = list(string)
  default     = ["10.20.0.0/24", "10.20.1.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2 && alltrue([for cidr in var.public_subnet_cidrs : can(cidrhost(cidr, 0))])
    error_message = "Provide two valid public subnet CIDRs."
  }
}

variable "application_subnet_cidrs" {
  description = "One private application subnet CIDR per availability zone."
  type        = list(string)
  default     = ["10.20.10.0/24", "10.20.11.0/24"]

  validation {
    condition     = length(var.application_subnet_cidrs) == 2 && alltrue([for cidr in var.application_subnet_cidrs : can(cidrhost(cidr, 0))])
    error_message = "Provide two valid application subnet CIDRs."
  }
}

variable "data_subnet_cidrs" {
  description = "One private data subnet CIDR per availability zone."
  type        = list(string)
  default     = ["10.20.20.0/24", "10.20.21.0/24"]

  validation {
    condition     = length(var.data_subnet_cidrs) == 2 && alltrue([for cidr in var.data_subnet_cidrs : can(cidrhost(cidr, 0))])
    error_message = "Provide two valid data subnet CIDRs."
  }
}

variable "hostname" {
  description = "Public staging hostname; DNS remains operator-managed."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$", var.hostname))
    error_message = "hostname must be a valid DNS hostname."
  }
}

variable "certificate_arn" {
  description = "ARN of an existing ACM certificate for hostname."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:acm:us-east-1:[0-9]{12}:certificate/[0-9a-f-]+$", var.certificate_arn))
    error_message = "certificate_arn must identify a us-east-1 ACM certificate."
  }
}

variable "web_image_tag" {
  description = "Immutable, non-latest deployment tag for the Web image."
  type        = string

  validation {
    condition     = var.web_image_tag != "latest" && can(regex("^[A-Za-z0-9_][A-Za-z0-9_.-]{6,127}$", var.web_image_tag))
    error_message = "web_image_tag must be an immutable tag of at least seven characters and cannot be latest."
  }
}

variable "api_image_tag" {
  description = "Immutable, non-latest deployment tag for the API image."
  type        = string

  validation {
    condition     = var.api_image_tag != "latest" && can(regex("^[A-Za-z0-9_][A-Za-z0-9_.-]{6,127}$", var.api_image_tag))
    error_message = "api_image_tag must be an immutable tag of at least seven characters and cannot be latest."
  }
}

variable "services_enabled" {
  description = "Enable one Web and one API task only after secrets and migration are ready."
  type        = bool
  default     = false
}

variable "openrouter_enabled" {
  description = "Reference OPENROUTER_API_KEY only after that optional JSON key has been populated."
  type        = bool
  default     = false
}

variable "purge_data" {
  description = "Explicitly skip the RDS final snapshot and force-delete managed ECR images during teardown."
  type        = bool
  default     = false
}

variable "final_snapshot_identifier" {
  description = "Unique final RDS snapshot identifier used by safe teardown."
  type        = string
  default     = "shifu-staging-final-snapshot"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,253}[a-z0-9]$", var.final_snapshot_identifier))
    error_message = "final_snapshot_identifier must be a valid RDS snapshot identifier."
  }
}

variable "monthly_budget_usd" {
  description = "Monthly staging cost budget in USD."
  type        = number

  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "monthly_budget_usd must be greater than zero."
  }
}

variable "budget_subscriber_emails" {
  description = "Non-secret e-mail addresses that receive budget notifications."
  type        = set(string)

  validation {
    condition = (
      length(var.budget_subscriber_emails) > 0 &&
      alltrue([for email in var.budget_subscriber_emails : can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", email))])
    )
    error_message = "Provide at least one valid budget subscriber e-mail address."
  }
}

variable "additional_tags" {
  description = "Additional non-secret tags applied to staging resources."
  type        = map(string)
  default     = {}
}
