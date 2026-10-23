resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${local.name}/web"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name}/api"
  retention_in_days = 14
}

resource "aws_ecs_cluster" "staging" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_service_discovery_private_dns_namespace" "staging" {
  name        = "${var.environment}.${var.project_name}.internal"
  description = "Private service discovery for Shifu staging"
  vpc         = aws_vpc.staging.id
}

resource "aws_service_discovery_service" "api" {
  name = "api"

  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.staging.id
    routing_policy = "MULTIVALUE"

    dns_records {
      ttl  = 10
      type = "A"
    }
  }
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${local.name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.web_execution.arn
  task_role_arn            = aws_iam_role.web_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "web"
      image     = "${aws_ecr_repository.web.repository_url}:${var.web_image_tag}"
      essential = true
      portMappings = [{
        name          = "web"
        containerPort = 7000
        hostPort      = 7000
        protocol      = "tcp"
        appProtocol   = "http"
      }]
      environment = [
        { name = "NODE_ENV", value = "production" },
        { name = "SHIFU_WEB_APP_PORT", value = "7000" },
        { name = "SHIFU_WEB_APP_URL", value = "https://${var.hostname}" },
        { name = "SHIFU_IDENTITY_API_URL", value = "http://${local.api_discovery_name}:7777" },
        { name = "SHIFU_TRUSTED_PROXY_IPS", value = var.vpc_cidr },
      ]
      secrets = [
        for key in local.web_secret_keys : {
          name      = key
          valueFrom = "${aws_secretsmanager_secret.web.arn}:${key}::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.web.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "web"
        }
      }
    },
  ])
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.api_execution.arn
  task_role_arn            = aws_iam_role.api_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
      essential = true
      portMappings = [{
        name          = "api"
        containerPort = 7777
        hostPort      = 7777
        protocol      = "tcp"
        appProtocol   = "http"
      }]
      environment = [
        { name = "SHIFU_SERVER_APP_PORT", value = "7777" },
        { name = "SHIFU_SERVER_APP_MODE", value = "staging" },
        { name = "SHIFU_AUTH_ISSUER", value = "https://${var.hostname}" },
        { name = "SHIFU_AUTH_AUDIENCE", value = "shifu-api" },
        { name = "SHIFU_AUTH_JWKS_URL", value = "https://${var.hostname}/api/auth/jwks" },
        { name = "SHIFU_EMAIL_PROVIDER", value = "resend" },
        { name = "SHIFU_CONFIRMATION_ACTION_ORIGIN", value = "https://${var.hostname}" },
        { name = "SHIFU_EMAIL_TIMEOUT_SECONDS", value = "10" },
        { name = "INNGEST_APP_ID", value = local.name },
        { name = "INNGEST_DEV", value = "0" },
        { name = "INNGEST_API_BASE_URL", value = "https://api.inngest.com" },
        { name = "INNGEST_EVENT_API_BASE_URL", value = "https://inn.gs" },
        { name = "TRUSTED_PROXY_IPS", value = var.vpc_cidr },
      ]
      secrets = [
        for key in local.api_secret_keys : {
          name      = key
          valueFrom = "${aws_secretsmanager_secret.api.arn}:${key}::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
    },
  ])
}

resource "aws_ecs_service" "web" {
  name            = "${local.name}-web"
  cluster         = aws_ecs_cluster.staging.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.services_enabled ? 1 : 0
  launch_type     = "FARGATE"

  health_check_grace_period_seconds = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.application[*].id
    security_groups  = [aws_security_group.web.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 7000
  }

  depends_on = [aws_lb_listener.https]
}

resource "aws_ecs_service" "api" {
  name            = "${local.name}-api"
  cluster         = aws_ecs_cluster.staging.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.services_enabled ? 1 : 0
  launch_type     = "FARGATE"

  health_check_grace_period_seconds = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.application[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 7777
  }

  service_registries {
    registry_arn   = aws_service_discovery_service.api.arn
    container_name = "api"
  }

  depends_on = [aws_lb_listener_rule.inngest]
}
