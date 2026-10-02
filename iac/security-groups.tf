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

resource "aws_vpc_security_group_egress_rule" "rds_egress" {
  security_group_id = aws_security_group.rds.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "efs_mount_targets" {
  name        = "${var.project_name}-efs"
  description = "NFS access to EFS only from the temporary laboratory client."
  vpc_id      = aws_vpc.storage_lab.id

  tags = {
    Name = "${var.project_name}-efs"
  }
}

resource "aws_vpc_security_group_ingress_rule" "efs_from_test_client" {
  security_group_id            = aws_security_group.efs_mount_targets.id
  description                  = "NFS from the SSM-managed EFS test client."
  referenced_security_group_id = aws_security_group.efs_test_client.id
  from_port                    = 2049
  to_port                      = 2049
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "efs_mount_targets_egress" {
  security_group_id = aws_security_group.efs_mount_targets.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "efs_test_client" {
  name        = "${var.project_name}-efs-client"
  description = "No inbound ports; outbound access for SSM and the EFS mount."
  vpc_id      = aws_vpc.storage_lab.id

  tags = {
    Name = "${var.project_name}-efs-client"
  }
}

resource "aws_vpc_security_group_egress_rule" "efs_test_client_egress" {
  security_group_id = aws_security_group.efs_test_client.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
