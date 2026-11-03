# Rede padrão da conta: nenhuma VPC, sub-rede, NAT ou gateway novo é criado.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

resource "aws_db_subnet_group" "rds_lab" {
  name       = "${var.project_name}-subnets"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name = "${var.project_name}-subnets"
  }
}

resource "aws_security_group" "rds_lab" {
  name        = "${var.project_name}-postgres"
  description = "PostgreSQL do laboratorio RDS: acesso somente do IP do grupo"
  vpc_id      = data.aws_vpc.default.id

  tags = {
    Name = "${var.project_name}-postgres"
  }
}

resource "aws_vpc_security_group_ingress_rule" "postgres_from_group_ip" {
  security_group_id = aws_security_group.rds_lab.id
  description       = "PostgreSQL somente do IP publico do grupo"
  cidr_ipv4         = var.allowed_cidr
  from_port         = local.database_port
  to_port           = local.database_port
  ip_protocol       = "tcp"
}
