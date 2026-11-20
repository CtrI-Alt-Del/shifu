mock_provider "aws" {
  mock_data "aws_vpc" {
    defaults = {
      id         = "vpc-0123456789abcdef0"
      cidr_block = "172.31.0.0/16"
    }
  }

  mock_data "aws_subnets" {
    defaults = {
      ids = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
    }
  }
}

mock_provider "random" {
  mock_resource "random_id" {
    defaults = {
      hex = "a1b2c3d4e5"
    }
  }
}

variables {
  aws_region         = "us-east-2"
  project_name       = "shifu-rds-lab-test"
  allowed_cidr       = "198.51.100.25/32"
  engine_version     = "17"
  instance_class     = "db.t4g.micro"
  db_master_password = "temporary-test-password-17"
}

run "staging_mirror_and_safe_teardown" {
  command = apply

  assert {
    condition = (
      aws_db_instance.rds_lab.engine == "postgres" &&
      aws_db_instance.rds_lab.engine_version == "17" &&
      aws_db_instance.rds_lab.instance_class == "db.t4g.micro" &&
      aws_db_instance.rds_lab.db_name == "shifu" &&
      aws_db_instance.rds_lab.allocated_storage == 20 &&
      aws_db_instance.rds_lab.storage_type == "gp3" &&
      aws_db_instance.rds_lab.storage_encrypted &&
      aws_db_instance.rds_lab.multi_az == false &&
      aws_db_instance.rds_lab.backup_retention_period == 0 &&
      aws_db_instance.rds_lab.skip_final_snapshot &&
      aws_db_instance.rds_lab.deletion_protection == false
    )
    error_message = "RDS lab must mirror the requested staging database settings and permit explicit cleanup."
  }

  assert {
    condition = (
      aws_vpc_security_group_ingress_rule.postgres_from_group_ip.cidr_ipv4 == "198.51.100.25/32" &&
      aws_vpc_security_group_ingress_rule.postgres_from_group_ip.from_port == 5432 &&
      aws_vpc_security_group_ingress_rule.postgres_from_group_ip.to_port == 5432 &&
      aws_vpc_security_group_ingress_rule.postgres_from_group_ip.ip_protocol == "tcp"
    )
    error_message = "Only PostgreSQL TCP from the configured IPv4 /32 may reach the lab."
  }

  assert {
    condition     = aws_db_instance.rds_lab.identifier == "${var.project_name}-${lower(random_id.execution.hex)}"
    error_message = "Each lab execution must receive a unique database identifier."
  }

  assert {
    condition     = aws_db_instance.rds_lab.password_wo_version == 5
    error_message = "The master password must use the write-only provider argument version."
  }
}

run "reject_unrestricted_ingress" {
  command = plan

  variables {
    allowed_cidr = "0.0.0.0/0"
  }

  expect_failures = [var.allowed_cidr]
}
