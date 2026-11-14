# A senha é gerada aqui e fica apenas no estado local, ignorado pelo Git.
resource "random_password" "master" {
  length  = 24
  special = false
}

resource "aws_db_instance" "rds_lab" {
  identifier = var.project_name

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = local.database_name
  username = local.master_username
  password = random_password.master.result
  port     = local.database_port

  multi_az               = false
  publicly_accessible    = true
  db_subnet_group_name   = aws_db_subnet_group.rds_lab.name
  vpc_security_group_ids = [aws_security_group.rds_lab.id]

  backup_retention_period    = 1
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
