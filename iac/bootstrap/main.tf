locals {
  common_tags = merge(
    {
      Project     = "shifu"
      Environment = "staging"
      ManagedBy   = "terraform"
      Component   = "terraform-backend"
    },
    var.additional_tags,
  )
}

resource "aws_s3_bucket" "state" {
  bucket        = var.state_bucket_name
  force_destroy = var.purge_backend
}

resource "aws_s3_bucket_ownership_controls" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }

    bucket_key_enabled = true
  }
}

data "aws_iam_policy_document" "state" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.state.arn,
      "${aws_s3_bucket.state.arn}/*",
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  dynamic "statement" {
    for_each = length(var.operator_principal_arns) == 0 ? [] : [var.operator_principal_arns]

    content {
      sid    = "AllowExplicitOperators"
      effect = "Allow"

      principals {
        type        = "AWS"
        identifiers = sort(tolist(statement.value))
      }

      actions = [
        "s3:GetBucketVersioning",
        "s3:ListBucket",
      ]
      resources = [aws_s3_bucket.state.arn]
    }
  }

  dynamic "statement" {
    for_each = length(var.operator_principal_arns) == 0 ? [] : [var.operator_principal_arns]

    content {
      sid    = "AllowExplicitOperatorStateObjects"
      effect = "Allow"

      principals {
        type        = "AWS"
        identifiers = sort(tolist(statement.value))
      }

      actions = [
        "s3:DeleteObject",
        "s3:GetObject",
        "s3:PutObject",
      ]
      resources = ["${aws_s3_bucket.state.arn}/*"]
    }
  }
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = data.aws_iam_policy_document.state.json

  depends_on = [aws_s3_bucket_public_access_block.state]
}
