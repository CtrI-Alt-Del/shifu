resource "aws_dynamodb_table" "events" {
  name         = "${var.project_name}-events-${random_id.bucket_suffix.hex}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "event_key"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "event_key"
    type = "S"
  }

  attribute {
    name = "event_type"
    type = "S"
  }

  attribute {
    name = "occurred_at"
    type = "S"
  }

  global_secondary_index {
    name = "event-type-occurred-at-index"

    key_schema {
      attribute_name = "event_type"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "occurred_at"
      key_type       = "RANGE"
    }

    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-events"
  }
}
