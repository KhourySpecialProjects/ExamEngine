# Main VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "examengine-vpc-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Internet Gateway for public subnets
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "examengine-igw-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Public subnets (alb only)
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "examengine-public-${count.index + 1}-${var.environment}"
    Tier        = "Public"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Route table for public subnets
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

tags = {
    Name        = "examengine-public-rt-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Associate public subnets with public route table
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private App Subnets (ECS Fargate tasks)
resource "aws_subnet" "private_app" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 11}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "examengine-private-app-${count.index + 1}-${var.environment}"
    Tier        = "Application"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count  = 2
  domain = "vpc"

  tags = {
    Name        = "examengine-nat-eip-${count.index + 1}-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  depends_on = [aws_internet_gateway.main]
}

# NAT Gateways in public subnets
resource "aws_nat_gateway" "main" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name        = "examengine-nat-${count.index + 1}-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  depends_on = [aws_internet_gateway.main]
}

# Route tables for private app subnets (one per AZ for NAT redundancy)
resource "aws_route_table" "private_app" {
  count  = 2
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = {
    Name        = "examengine-private-app-rt-${count.index + 1}-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Associate private app subnets with their route tables
resource "aws_route_table_association" "private_app" {
  count          = 2
  subnet_id      = aws_subnet.private_app[count.index].id
  route_table_id = aws_route_table.private_app[count.index].id
}

# Private db subnets (RDS only - completely isolated)
resource "aws_subnet" "private_db" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 21}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "examengine-private-db-${count.index + 1}-${var.environment}"
    Tier        = "Database"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# DB Subnet Group for RDS
resource "aws_db_subnet_group" "main" {
  name       = "examengine-db-subnet-group-${var.environment}"
  subnet_ids = aws_subnet.private_db[*].id

  tags = {
    Name        = "examengine-db-subnet-group-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Route table for database subnets
resource "aws_route_table" "private_db" {
  vpc_id = aws_vpc.main.id
  # No routes - database subnets are completely isolated

  tags = {
    Name        = "examengine-private-db-rt-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Associate DB subnets with DB route table
resource "aws_route_table_association" "private_db" {
  count          = 2
  subnet_id      = aws_subnet.private_db[count.index].id
  route_table_id = aws_route_table.private_db.id
}

# VPC Endpoints (S3, ECR)
# S3 Gateway Endpoint
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.aws_region}.s3"

  route_table_ids = concat(
    aws_route_table.private_app[*].id,
    [aws_route_table.private_db.id]
  )

  tags = {
    Name        = "examengine-s3-endpoint-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
  name        = "examengine-vpc-endpoints-${var.environment}"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTPS from ECS tasks"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "examengine-vpc-endpoints-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ECR API Endpoint
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "examengine-ecr-api-endpoint-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ECR DKR Endpoint
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "examengine-ecr-dkr-endpoint-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# CloudWatch Logs Endpoint (for ECS logging)
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "examengine-logs-endpoint-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
