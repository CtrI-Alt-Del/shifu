locals {
  common_tags = {
    Project     = "Shifu"
    Environment = "dynamodb-lab"
    ManagedBy   = "Terraform"
    Purpose     = "Academic cloud storage activity"
  }
}

resource "random_id" "execution" {
  byte_length = 5
}
