data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  state_bucket_arn = "arn:aws:s3:::${var.state_bucket_name}"

  ecs_arn_prefix = "arn:aws:ecs:${var.aws_region}:${local.account_id}"
  iam_arn_prefix = "arn:aws:iam::${local.account_id}"

  ecs_task_role_arns = [
    aws_iam_role.web_execution.arn,
    aws_iam_role.web_task.arn,
    aws_iam_role.server_execution.arn,
    aws_iam_role.server_task.arn,
  ]
}

# The AWS Free Plan project blocks OIDC identity providers, so GitHub Actions
# signs in with IAM user access keys. Terraform creates the users and their
# policies only. The access keys are created by an operator in the IAM console and
# stored as GitHub environment secrets, so they never enter the Terraform state.

resource "aws_iam_user" "deployer" {
  name = "${local.name}-deployer"
}

resource "aws_iam_user" "terraform" {
  name = "${local.name}-terraform"
}

data "aws_iam_policy_document" "deployer" {
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "EcrPushImages"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:ListImages",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [
      aws_ecr_repository.web.arn,
      aws_ecr_repository.server.arn,
    ]
  }

  statement {
    sid = "EcsDeployServices"
    actions = [
      "ecs:DescribeServices",
      "ecs:UpdateService",
    ]
    resources = [
      "${local.ecs_arn_prefix}:service/${aws_ecs_cluster.staging.name}/*",
    ]
  }

  statement {
    sid = "EcsRunMigrationTask"
    actions = [
      "ecs:DescribeTasks",
      "ecs:RunTask",
      "ecs:StopTask",
    ]
    resources = [
      "${local.ecs_arn_prefix}:task/${aws_ecs_cluster.staging.name}/*",
      "${local.ecs_arn_prefix}:task-definition/${local.name}-*:*",
    ]
  }

  statement {
    sid = "EcsTaskDefinitions"
    actions = [
      "ecs:DescribeTaskDefinition",
      "ecs:ListTasks",
      "ecs:RegisterTaskDefinition",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "PassTaskRolesToEcs"
    actions   = ["iam:PassRole"]
    resources = local.ecs_task_role_arns

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  statement {
    sid = "ReadServiceLogs"
    actions = [
      "logs:DescribeLogStreams",
      "logs:GetLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.web.arn}:*",
      "${aws_cloudwatch_log_group.server.arn}:*",
    ]
  }

  statement {
    sid = "ReadTargetHealth"
    actions = [
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeTargetHealth",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "terraform" {
  statement {
    sid       = "StateBucketList"
    actions   = ["s3:GetBucketVersioning", "s3:ListBucket"]
    resources = [local.state_bucket_arn]
  }

  statement {
    sid       = "StateObjects"
    actions   = ["s3:DeleteObject", "s3:GetObject", "s3:PutObject"]
    resources = ["${local.state_bucket_arn}/*"]
  }

  statement {
    sid = "StagingServices"
    actions = [
      "budgets:*",
      "ec2:*",
      "ecr:*",
      "ecs:*",
      "elasticache:*",
      "elasticloadbalancing:*",
      "logs:*",
      "rds:*",
      "route53:*",
      "secretsmanager:*",
      "servicediscovery:*",
      "tag:GetResources",
    ]
    resources = ["*"]

    condition {
      test     = "StringEqualsIfExists"
      variable = "aws:RequestedRegion"
      values   = [var.aws_region, "us-east-1"]
    }
  }

  statement {
    sid = "KmsForManagedSecrets"
    actions = [
      "kms:CreateGrant",
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:GenerateDataKey",
      "kms:ListAliases",
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values = [
        "elasticache.${var.aws_region}.amazonaws.com",
        "rds.${var.aws_region}.amazonaws.com",
        "secretsmanager.${var.aws_region}.amazonaws.com",
      ]
    }
  }

  statement {
    sid = "ManageStagingRoles"
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:PutRolePolicy",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:UpdateRole",
    ]
    resources = ["${local.iam_arn_prefix}:role/${local.name}-*"]
  }

  statement {
    sid       = "AttachOnlyTheEcsExecutionPolicy"
    actions   = ["iam:AttachRolePolicy", "iam:DetachRolePolicy"]
    resources = ["${local.iam_arn_prefix}:role/${local.name}-*"]

    condition {
      test     = "ArnEquals"
      variable = "iam:PolicyARN"
      values   = ["arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"]
    }
  }

  statement {
    sid       = "PassStagingRolesToEcs"
    actions   = ["iam:PassRole"]
    resources = ["${local.iam_arn_prefix}:role/${local.name}-*"]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  statement {
    sid       = "CreateServiceLinkedRoles"
    actions   = ["iam:CreateServiceLinkedRole"]
    resources = ["arn:aws:iam::*:role/aws-service-role/*"]

    condition {
      test     = "StringEquals"
      variable = "iam:AWSServiceName"
      values = [
        "ecs.amazonaws.com",
        "elasticache.amazonaws.com",
        "elasticloadbalancing.amazonaws.com",
        "rds.amazonaws.com",
      ]
    }
  }

  # Read-only access to the CI identities, so that refresh works. Terraform in CI
  # cannot change them: an operator applies changes to these users locally.
  statement {
    sid = "ReadCiIdentities"
    actions = [
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:GetUser",
      "iam:ListAttachedUserPolicies",
      "iam:ListPolicyVersions",
      "iam:ListUserPolicies",
      "iam:ListUserTags",
    ]
    resources = [
      "${local.iam_arn_prefix}:policy/${local.name}-*",
      "${local.iam_arn_prefix}:user/${local.name}-*",
    ]
  }
}

resource "aws_iam_policy" "deployer" {
  name        = "${local.name}-deployer"
  description = "Push images and update the staging ECS services."
  policy      = data.aws_iam_policy_document.deployer.json
}

resource "aws_iam_policy" "terraform" {
  name        = "${local.name}-terraform"
  description = "Plan and apply the staging Terraform root."
  policy      = data.aws_iam_policy_document.terraform.json
}

resource "aws_iam_user_policy_attachment" "deployer" {
  user       = aws_iam_user.deployer.name
  policy_arn = aws_iam_policy.deployer.arn
}

resource "aws_iam_user_policy_attachment" "terraform" {
  user       = aws_iam_user.terraform.name
  policy_arn = aws_iam_policy.terraform.arn
}
