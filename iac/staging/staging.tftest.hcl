mock_provider "aws" {}

variables {
  hostname                  = "staging.example.com"
  certificate_arn           = "arn:aws:acm:us-east-1:123456789012:certificate/00000000-0000-0000-0000-000000000000"
  web_image_tag             = "0123456789abcdef-web"
  api_image_tag             = "0123456789abcdef-api"
  monthly_budget_usd        = 100
  budget_subscriber_emails  = ["platform-owner@example.com"]
  final_snapshot_identifier = "shifu-staging-final-test"
}

run "foundation_contract" {
  command = plan

  assert {
    condition     = length(aws_subnet.public) + length(aws_subnet.application) + length(aws_subnet.data) == 6
    error_message = "Staging must create six subnets across three tiers."
  }

  assert {
    condition     = aws_ecs_service.web.desired_count == 0 && aws_ecs_service.api.desired_count == 0
    error_message = "Phase zero must keep both services disabled."
  }

  assert {
    condition     = aws_ecs_task_definition.web.cpu == "512" && aws_ecs_task_definition.web.memory == "1024"
    error_message = "Web task sizing must remain 0.5 vCPU and 1 GiB."
  }

  assert {
    condition     = aws_ecs_task_definition.api.cpu == "512" && aws_ecs_task_definition.api.memory == "1024"
    error_message = "API task sizing must remain 0.5 vCPU and 1 GiB."
  }

  assert {
    condition     = aws_db_instance.postgres.engine_version == "17" && aws_db_instance.postgres.instance_class == "db.t4g.micro"
    error_message = "RDS must use PostgreSQL 17 on db.t4g.micro."
  }

  assert {
    condition     = aws_db_instance.postgres.backup_retention_period == 7 && aws_db_instance.postgres.skip_final_snapshot == false
    error_message = "Safe RDS defaults must retain seven-day backups and create a final snapshot."
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.transit_encryption_enabled && aws_elasticache_replication_group.redis.at_rest_encryption_enabled
    error_message = "Redis must encrypt data at rest and in transit."
  }

  assert {
    condition     = one(aws_lb_target_group.web.health_check).path == "/api/health" && one(aws_lb_target_group.api.health_check).path == "/health"
    error_message = "Web and API must use independent health checks."
  }

  assert {
    condition     = one(one(aws_lb_listener_rule.inngest.condition).path_pattern).values == toset(["/api/inngest"])
    error_message = "Only the exact Inngest callback path may route publicly to API."
  }

  assert {
    condition     = aws_cloudwatch_log_group.web.retention_in_days == 14 && aws_cloudwatch_log_group.api.retention_in_days == 14
    error_message = "Both application log groups must retain logs for 14 days."
  }

  assert {
    condition     = aws_ecr_repository.web.force_delete == false && aws_ecr_repository.api.force_delete == false
    error_message = "Safe mode must refuse force-deletion of ECR images."
  }
}

run "enabled_services" {
  command = plan

  variables {
    services_enabled = true
  }

  assert {
    condition     = aws_ecs_service.web.desired_count == 1 && aws_ecs_service.api.desired_count == 1
    error_message = "Enablement must run exactly one task for each service."
  }
}

run "explicit_purge" {
  command = plan

  variables {
    purge_data = true
  }

  assert {
    condition     = aws_db_instance.postgres.skip_final_snapshot && aws_db_instance.postgres.final_snapshot_identifier == null
    error_message = "Purge mode must explicitly skip the final RDS snapshot."
  }

  assert {
    condition     = aws_ecr_repository.web.force_delete && aws_ecr_repository.api.force_delete
    error_message = "Purge mode must permit managed ECR image cleanup."
  }
}
