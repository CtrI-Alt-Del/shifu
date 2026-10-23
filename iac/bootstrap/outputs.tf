output "state_bucket_name" {
  description = "S3 bucket name used by the staging backend."
  value       = aws_s3_bucket.state.id
}

output "state_bucket_region" {
  description = "AWS region containing the staging backend."
  value       = var.aws_region
}

output "staging_state_key" {
  description = "Recommended object key for staging state."
  value       = "staging/terraform.tfstate"
}
