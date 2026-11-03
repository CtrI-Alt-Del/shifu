locals {
  common_tags = {
    Project     = "Shifu"
    Environment = "rds-lab"
    ManagedBy   = "Terraform"
    Purpose     = "Academic V1 RDS activity"
  }

  database_name   = "shifu_lab"
  master_username = "shifu_admin"
  database_port   = 5432
}
