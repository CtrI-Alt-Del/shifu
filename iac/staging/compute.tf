resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${local.name}/web"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "server" {
  name              = "/ecs/${local.name}/server"
  retention_in_days = 14
}

resource "aws_ecs_cluster" "staging" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "staging" {
  cluster_name       = aws_ecs_cluster.staging.name
  capacity_providers = ["FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }
}

resource "aws_service_discovery_private_dns_namespace" "staging" {
  name        = "${var.environment}.${var.project_name}.internal"
  description = "Private service discovery for Shifu staging"
  vpc         = aws_vpc.staging.id
}

resource "aws_service_discovery_service" "server" {
  name = "server"

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
    cpu_architecture        = "ARM64"
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
        { name = "SHIFU_WEB_APP_URL", value = local.public_origin },
        { name = "SHIFU_USE_SECURE_COOKIES", value = tostring(local.is_https_enabled) },
        { name = "SHIFU_IDENTITY_API_URL", value = "http://${local.server_discovery_name}:7777" },
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

resource "aws_ecs_task_definition" "server" {
  family                   = "${local.name}-server"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.server_execution.arn
  task_role_arn            = aws_iam_role.server_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name      = "server"
      image     = "${aws_ecr_repository.server.repository_url}:${var.server_image_tag}"
      essential = true
      portMappings = [{
        name          = "server"
        containerPort = 7777
        hostPort      = 7777
        protocol      = "tcp"
        appProtocol   = "http"
      }]
      environment = [
        { name = "SHIFU_SERVER_APP_PORT", value = "7777" },
        { name = "SHIFU_SERVER_APP_MODE", value = "staging" },
        { name = "SHIFU_AUTH_ISSUER", value = local.public_origin },
        { name = "SHIFU_AUTH_AUDIENCE", value = "shifu-api" },
        { name = "SHIFU_AUTH_JWKS_URL", value = "${local.public_origin}/api/auth/jwks" },
        { name = "SHIFU_EMAIL_PROVIDER", value = "resend" },
        { name = "SHIFU_CONFIRMATION_ACTION_ORIGIN", value = local.public_origin },
        { name = "SHIFU_EMAIL_TIMEOUT_SECONDS", value = "10" },
        { name = "INNGEST_APP_ID", value = local.name },
        { name = "INNGEST_DEV", value = "0" },
        { name = "INNGEST_API_BASE_URL", value = "https://api.inngest.com" },
        { name = "INNGEST_EVENT_API_BASE_URL", value = "https://inn.gs" },
        { name = "TRUSTED_PROXY_IPS", value = var.vpc_cidr },
      ]
      secrets = [
        for key in local.server_secret_keys : {
          name      = key
          valueFrom = "${aws_secretsmanager_secret.server.arn}:${key}::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.server.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "server"
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

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }

  health_check_grace_period_seconds = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.application[*].id
    security_groups  = [aws_security_group.web.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 7000
  }

  depends_on = [aws_lb_listener.http, aws_lb_listener.https, aws_ecs_cluster_capacity_providers.staging]
}

resource "aws_ecs_service" "server" {
  name            = "${local.name}-server"
  cluster         = aws_ecs_cluster.staging.id
  task_definition = aws_ecs_task_definition.server.arn
  desired_count   = var.services_enabled ? 1 : 0

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }

  health_check_grace_period_seconds = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.application[*].id
    security_groups  = [aws_security_group.server.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.server.arn
    container_name   = "server"
    container_port   = 7777
  }

  service_registries {
    registry_arn   = aws_service_discovery_service.server.arn
    container_name = "server"
  }

  depends_on = [aws_lb_listener_rule.inngest, aws_ecs_cluster_capacity_providers.staging]
}
