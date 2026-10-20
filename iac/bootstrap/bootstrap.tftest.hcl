mock_provider "aws" {}

run "secure_backend_defaults" {
  command = plan

  variables {
    state_bucket_name = "shifu-staging-state-example"
  }

  assert {
    condition     = aws_s3_bucket.state.force_destroy == false
    error_message = "Safe mode must not force-delete backend state."
  }

  assert {
    condition     = aws_s3_bucket_versioning.state.versioning_configuration[0].status == "Enabled"
    error_message = "Backend state versioning must be enabled."
  }

  assert {
    condition     = one(one(aws_s3_bucket_server_side_encryption_configuration.state.rule).apply_server_side_encryption_by_default).sse_algorithm == "AES256"
    error_message = "Backend state must use server-side encryption."
  }

  assert {
    condition     = aws_s3_bucket_public_access_block.state.restrict_public_buckets
    error_message = "Backend public access must be blocked."
  }
}

run "explicit_backend_purge" {
  command = plan

  variables {
    state_bucket_name = "shifu-staging-state-example"
    purge_backend     = true
  }

  assert {
    condition     = aws_s3_bucket.state.force_destroy
    error_message = "Explicit backend purge must permit deletion of versioned objects."
  }
}
