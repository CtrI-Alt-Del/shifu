resource "aws_security_group" "rds" {
  name        = "${var.project_name}-postgres"
  description = "PostgreSQL access restricted to the group's current public IPv4 address."
  vpc_id      = aws_vpc.storage_lab.id

  tags = {
    Name = "${var.project_name}-postgres"
  }
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_group" {
  security_group_id = aws_security_group.rds.id
  description       = "PostgreSQL from the group's single public IPv4 address."
  cidr_ipv4         = var.allowed_client_ipv4_cidr
  from_port         = 5432
  to_port           = 5432
  ip_protocol       = "tcp"
}
