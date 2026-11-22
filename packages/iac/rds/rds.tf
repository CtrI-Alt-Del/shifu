resource "random_id" "execution" {
  byte_length = 5
}

resource "aws_db_instance" "rds_lab" {
  identifier = "${var.project_name}-${lower(random_id.execution.hex)}"

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name             = local.database_name
  username            = local.master_username
  password_wo         = var.db_master_password
  password_wo_version = 5
  port                = local.database_port

  multi_az               = false
  publicly_accessible    = true
  db_subnet_group_name   = aws_db_subnet_group.rds_lab.name
  vpc_security_group_ids = [aws_security_group.rds_lab.id]

  backup_retention_period    = 0
  copy_tags_to_snapshot      = true
  auto_minor_version_upgrade = true
  apply_immediately          = true

  # Somente laboratório: facilita o encerramento. O snapshot manual é a evidência.
  skip_final_snapshot = true
  deletion_protection = false

  tags = {
    Name = var.project_name
  }
}
