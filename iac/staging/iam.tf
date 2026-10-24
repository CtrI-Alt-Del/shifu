locals {
  ecs_assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role" "web_execution" {
  name               = "${local.name}-web-execution"
  assume_role_policy = local.ecs_assume_role_policy
}

resource "aws_iam_role" "api_execution" {
  name               = "${local.name}-api-execution"
  assume_role_policy = local.ecs_assume_role_policy
}

resource "aws_iam_role" "web_task" {
  name               = "${local.name}-web-task"
  assume_role_policy = local.ecs_assume_role_policy
}

resource "aws_iam_role" "api_task" {
  name               = "${local.name}-api-task"
  assume_role_policy = local.ecs_assume_role_policy
}

resource "aws_iam_role_policy_attachment" "web_execution" {
  role       = aws_iam_role.web_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "api_execution" {
  role       = aws_iam_role.api_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "web_secret" {
  name = "read-web-runtime-secret"
  role = aws_iam_role.web_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadWebRuntimeSecret"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.web.arn]
    }]
  })
}

resource "aws_iam_role_policy" "api_secret" {
  name = "read-api-runtime-secret"
  role = aws_iam_role.api_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadApiRuntimeSecret"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.api.arn]
    }]
  })
}
