output "aws_region" {
  description = "Região AWS usada pelo laboratório."
  value       = var.aws_region
}

output "s3_bucket_name" {
  description = "Bucket S3 do laboratório."
  value       = aws_s3_bucket.storage_lab.bucket
}

output "s3_public_demo_url" {
  description = "URL do único objeto público de demonstração."
  value       = "https://${aws_s3_bucket.storage_lab.bucket_regional_domain_name}/academic/storage-activity/public/exemplo.txt"
}

