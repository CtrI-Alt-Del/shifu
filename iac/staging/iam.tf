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

resource "aws_iam_role" "server_execution" {
  name               = "${local.name}-server-execution"
  assume_role_policy = local.ecs_assume_role_policy
}

resource "aws_iam_role" "web_task" {
  name               = "${local.name}-web-task"
  assume_role_policy = local.ecs_assume_role_policy
}

resource "aws_iam_role" "server_task" {
  name               = "${local.name}-server-task"
  assume_role_policy = local.ecs_assume_role_policy
}

resource "aws_iam_role_policy_attachment" "web_execution" {
  role       = aws_iam_role.web_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "server_execution" {
  role       = aws_iam_role.server_execution.name
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

resource "aws_iam_role_policy" "server_secret" {
  name = "read-server-runtime-secret"
  role = aws_iam_role.server_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadServerRuntimeSecret"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.server.arn]
    }]
  })
}
