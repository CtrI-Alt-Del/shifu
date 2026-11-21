locals {
  common_tags = {
    Project     = "Shifu"
    Environment = "rds-lab"
    ManagedBy   = "Terraform"
    Purpose     = "Academic RDS storage activity"
  }

  database_name   = "shifu"
  master_username = "shifu_admin"
  database_port   = 5432
}
