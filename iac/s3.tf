resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "storage_lab" {
  bucket        = "${var.project_name}-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name = "${var.project_name}-bucket"
  }
}

resource "aws_s3_bucket_ownership_controls" "storage_lab" {
  bucket = aws_s3_bucket.storage_lab.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "storage_lab" {
  bucket = aws_s3_bucket.storage_lab.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_versioning" "storage_lab" {
  bucket = aws_s3_bucket.storage_lab.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "storage_lab" {
  bucket = aws_s3_bucket.storage_lab.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "storage_lab" {
  bucket = aws_s3_bucket.storage_lab.id

  rule {
    id     = "archive-lab-objects-after-30-days"
    status = "Enabled"

    filter {
      prefix = "academic/storage-activity/archive/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  depends_on = [aws_s3_bucket_versioning.storage_lab]
}

resource "aws_s3_bucket_policy" "public_demo_object" {
  bucket = aws_s3_bucket.storage_lab.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "ReadOnlySinglePublicLabObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.storage_lab.arn}/academic/storage-activity/public/exemplo.txt"
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.storage_lab]
}
