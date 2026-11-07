resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Public HTTPS entry point"
  vpc_id      = aws_vpc.staging.id

  tags = { Name = "${local.name}-alb" }
}

resource "aws_security_group" "web" {
  name        = "${local.name}-web"
  description = "Web BFF tasks"
  vpc_id      = aws_vpc.staging.id

  tags = { Name = "${local.name}-web" }
}

resource "aws_security_group" "server" {
  name        = "${local.name}-server"
  description = "FastAPI tasks"
  vpc_id      = aws_vpc.staging.id

  tags = { Name = "${local.name}-server" }
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "PostgreSQL from application tasks"
  vpc_id      = aws_vpc.staging.id

  tags = { Name = "${local.name}-rds" }
}

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis"
  description = "Redis from server tasks"
  vpc_id      = aws_vpc.staging.id

  tags = { Name = "${local.name}-redis" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  count = local.is_https_enabled ? 1 : 0

  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_web" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.web.id
  from_port                    = 7000
  to_port                      = 7000
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_server" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.server.id
  from_port                    = 7777
  to_port                      = 7777
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "web_from_alb" {
  security_group_id            = aws_security_group.web.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 7000
  to_port                      = 7000
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "server_from_web" {
  security_group_id            = aws_security_group.server.id
  referenced_security_group_id = aws_security_group.web.id
  from_port                    = 7777
  to_port                      = 7777
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "server_from_alb" {
  security_group_id            = aws_security_group.server.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 7777
  to_port                      = 7777
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_web" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.web.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_server" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.server.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_server" {
  security_group_id            = aws_security_group.redis.id
  referenced_security_group_id = aws_security_group.server.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "web_to_server" {
  security_group_id            = aws_security_group.web.id
  referenced_security_group_id = aws_security_group.server.id
  from_port                    = 7777
  to_port                      = 7777
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "web_to_rds" {
  security_group_id            = aws_security_group.web.id
  referenced_security_group_id = aws_security_group.rds.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "server_to_rds" {
  security_group_id            = aws_security_group.server.id
  referenced_security_group_id = aws_security_group.rds.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "server_to_redis" {
  security_group_id            = aws_security_group.server.id
  referenced_security_group_id = aws_security_group.redis.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "web_https" {
  security_group_id = aws_security_group.web.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "server_https" {
  security_group_id = aws_security_group.server.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

# The server fetches the Web app's signing keys from the public origin to check
# sessions. Over plain HTTP that is port 80, so the server needs it open. With
# HTTPS the request uses port 443, which `server_https` already allows.
resource "aws_vpc_security_group_egress_rule" "server_http_jwks" {
  count = local.is_https_enabled ? 0 : 1

  security_group_id = aws_security_group.server.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  description       = "Fetch the Web signing keys from the public origin over plain HTTP"
}

resource "aws_vpc_security_group_egress_rule" "web_dns_udp" {
  security_group_id = aws_security_group.web.id
  cidr_ipv4         = var.vpc_cidr
  from_port         = 53
  to_port           = 53
  ip_protocol       = "udp"
}

resource "aws_vpc_security_group_egress_rule" "web_dns_tcp" {
  security_group_id = aws_security_group.web.id
  cidr_ipv4         = var.vpc_cidr
  from_port         = 53
  to_port           = 53
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "server_dns_udp" {
  security_group_id = aws_security_group.server.id
  cidr_ipv4         = var.vpc_cidr
  from_port         = 53
  to_port           = 53
  ip_protocol       = "udp"
}

resource "aws_vpc_security_group_egress_rule" "server_dns_tcp" {
  security_group_id = aws_security_group.server.id
  cidr_ipv4         = var.vpc_cidr
  from_port         = 53
  to_port           = 53
  ip_protocol       = "tcp"
}
