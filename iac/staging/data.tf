resource "aws_db_instance" "postgres" {
  identifier = local.name

  engine         = "postgres"
  engine_version = "17"
  instance_class = "db.t4g.micro"

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "shifu"
  username = "shifu_admin"
  port     = 5432

  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.staging.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period = 7
  copy_tags_to_snapshot   = true

  deletion_protection       = false
  skip_final_snapshot       = var.purge_data
  final_snapshot_identifier = var.purge_data ? null : var.final_snapshot_identifier

  auto_minor_version_upgrade = true
  apply_immediately          = false

  tags = { Name = local.name }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = local.name
  description          = "Shifu staging Redis OSS"

  engine               = "redis"
  engine_version       = "7.1"
  node_type            = "cache.t4g.micro"
  num_cache_clusters   = 1
  parameter_group_name = "default.redis7"
  port                 = 6379

  automatic_failover_enabled = false
  multi_az_enabled           = false

  subnet_group_name  = aws_elasticache_subnet_group.staging.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  transit_encryption_mode    = "required"

  snapshot_retention_limit = 1
  apply_immediately        = false

  lifecycle {
    # AUTH is activated with ElastiCache's SET strategy after creation. Terraform
    # must neither receive the token nor remove this externally managed setting.
    ignore_changes = [auth_token, auth_token_update_strategy]
  }

  tags = { Name = local.name }
}
