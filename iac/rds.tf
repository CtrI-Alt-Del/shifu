resource "aws_db_subnet_group" "storage_lab" {
  name       = "${var.project_name}-db-subnets"
  subnet_ids = aws_subnet.public[*].id

  tags = {
    Name = "${var.project_name}-db-subnets"
  }
}

resource "aws_db_instance" "storage_lab" {
  identifier                  = "${var.project_name}-postgres"
  engine                      = "postgres"
  instance_class              = var.rds_instance_class
  db_name                     = var.rds_database_name
  username                    = var.rds_master_username
  manage_master_user_password = true

  allocated_storage     = 20
  storage_type          = "gp3"
  storage_encrypted     = true
  publicly_accessible   = true
  multi_az              = false
  db_subnet_group_name  = aws_db_subnet_group.storage_lab.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 1
  auto_minor_version_upgrade = true
  deletion_protection        = false
  skip_final_snapshot        = true
  copy_tags_to_snapshot      = true

  tags = {
    Name = "${var.project_name}-postgres"
  }
}
