data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  availability_zones = slice(
    data.aws_availability_zones.available.names,
    0,
    var.availability_zone_count
  )

  common_tags = {
    Project     = "Shifu"
    Environment = "storage-lab"
    ManagedBy   = "Terraform"
    Purpose     = "Academic V1 storage activity"
  }
}
