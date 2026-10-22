locals {
  name = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.additional_tags,
  )

  all_subnet_cidrs = concat(
    var.public_subnet_cidrs,
    var.application_subnet_cidrs,
    var.data_subnet_cidrs,
  )

  api_discovery_name = "api.${aws_service_discovery_private_dns_namespace.staging.name}"

  web_secret_keys = [
    "BETTER_AUTH_DATABASE_URL",
    "BETTER_AUTH_SECRET",
    "SHIFU_BFF_SHARED_SECRET",
  ]

  api_required_secret_keys = [
    "DATABASE_URL",
    "AGENTOS_DATABASE_URL",
    "REDIS_URL",
    "INNGEST_EVENT_KEY",
    "INNGEST_SIGNING_KEY",
    "SHIFU_RESEND_API_KEY",
    "SHIFU_RESEND_FROM",
    "SHIFU_BFF_SHARED_SECRET",
    "SHIFU_COMMUNICATION_ENCRYPTION_KEYS",
    "DIAGNOSTIC_REVISION_HMAC_KEY",
  ]

  api_secret_keys = var.openrouter_enabled ? concat(
    local.api_required_secret_keys,
    ["OPENROUTER_API_KEY"],
  ) : local.api_required_secret_keys
}

check "subnet_layout" {
  assert {
    condition     = length(local.all_subnet_cidrs) == 6 && length(distinct(local.all_subnet_cidrs)) == 6
    error_message = "The public, application and data tiers must use six distinct subnet CIDRs."
  }

  assert {
    condition = alltrue([
      for cidr in local.all_subnet_cidrs :
      slice(split(".", cidrhost(var.vpc_cidr, 0)), 0, 2) == slice(split(".", cidrhost(cidr, 0)), 0, 2)
    ])
    error_message = "Every subnet must be contained by vpc_cidr."
  }
}
