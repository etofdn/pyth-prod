# ElastiCache Redis Global Datastore Configuration

# Parameter Group for Redis
resource "aws_elasticache_parameter_group" "redis_us_east_1" {
  provider = aws.us_east_1
  name     = "pyth-oracle-redis-params-us-east-1"
  family   = "redis7.x"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = {
    Name        = "pyth-oracle-redis-params-us-east-1"
    Environment = "production"
  }
}

# Subnet Group for Redis
resource "aws_elasticache_subnet_group" "redis_us_east_1" {
  provider    = aws.us_east_1
  name        = "pyth-oracle-redis-subnet-group-us-east-1"
  subnet_ids  = [aws_subnet.private_us_east_1_a.id, aws_subnet.private_us_east_1_b.id]
  description = "Subnet group for Redis in us-east-1"

  tags = {
    Name        = "pyth-oracle-redis-subnet-group-us-east-1"
    Environment = "production"
  }
}

# Security Group for Redis
resource "aws_security_group" "redis_us_east_1" {
  provider    = aws.us_east_1
  name        = "pyth-oracle-redis-sg-us-east-1"
  description = "Security group for Redis"
  vpc_id      = aws_vpc.us_east_1.id

  ingress {
    description     = "Redis from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_us_east_1.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "pyth-oracle-redis-sg-us-east-1"
    Environment = "production"
  }
}

# Replication Group (Primary) - us-east-1
resource "aws_elasticache_replication_group" "us_east_1" {
  provider                      = aws.us_east_1
  replication_group_id          = "pyth-oracle-redis-us-east-1"
  description                   = "Redis for Pyth Oracle state management"
  
  engine                        = "redis"
  engine_version                = "7.1"
  node_type                     = "cache.t4g.micro"  # ARM-based for cost savings
  port                          = 6379
  parameter_group_name          = aws_elasticache_parameter_group.redis_us_east_1.name
  
  num_cache_clusters            = 2  # For high availability
  automatic_failover_enabled    = true
  multi_az_enabled             = true
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = true
  
  subnet_group_name             = aws_elasticache_subnet_group.redis_us_east_1.name
  security_group_ids            = [aws_security_group.redis_us_east_1.id]
  
  auto_minor_version_upgrade    = true
  snapshot_retention_limit      = 7
  snapshot_window              = "03:00-05:00"
  
  tags = {
    Name        = "pyth-oracle-redis-us-east-1"
    Environment = "production"
  }
  
  depends_on = [
    aws_elasticache_subnet_group.redis_us_east_1,
    aws_security_group.redis_us_east_1
  ]
}

# Global Replication Group
resource "aws_elasticache_global_replication_group" "pyth_oracle" {
  provider                      = aws.us_east_1
  global_replication_group_id_suffix = "pyth-oracle-global"
  primary_replication_group_id       = aws_elasticache_replication_group.us_east_1.id
  
  global_replication_group_description = "Global Redis for Pyth Oracle multi-region"

  engine_version = aws_elasticache_replication_group.us_east_1.engine_version

  tags = {
    Name        = "pyth-oracle-redis-global"
    Environment = "production"
  }
}

# Replica in us-west-2
resource "aws_elasticache_replication_group" "us_west_2" {
  provider                      = aws.us_west_2
  replication_group_id          = "pyth-oracle-redis-us-west-2"
  description                   = "Redis replica for Pyth Oracle in us-west-2"
  
  global_replication_group_id   = aws_elasticache_global_replication_group.pyth_oracle.global_replication_group_id
  
  num_cache_clusters            = 1
  automatic_failover_enabled    = false  # Replica doesn't need failover
  
  subnet_group_name             = aws_elasticache_subnet_group.redis_us_west_2.name
  security_group_ids            = [aws_security_group.redis_us_west_2.id]
  
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = true
  
  tags = {
    Name        = "pyth-oracle-redis-us-west-2"
    Environment = "production"
  }

  depends_on = [
    aws_elasticache_global_replication_group.pyth_oracle,
    aws_elasticache_subnet_group.redis_us_west_2,
    aws_security_group.redis_us_west_2
  ]
}

# Replica in eu-west-1
resource "aws_elasticache_replication_group" "eu_west_1" {
  provider                      = aws.eu_west_1
  replication_group_id          = "pyth-oracle-redis-eu-west-1"
  description                   = "Redis replica for Pyth Oracle in eu-west-1"
  
  global_replication_group_id   = aws_elasticache_global_replication_group.pyth_oracle.global_replication_group_id
  
  num_cache_clusters            = 1
  automatic_failover_enabled    = false
  
  subnet_group_name             = aws_elasticache_subnet_group.redis_eu_west_1.name
  security_group_ids            = [aws_security_group.redis_eu_west_1.id]
  
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = true
  
  tags = {
    Name        = "pyth-oracle-redis-eu-west-1"
    Environment = "production"
  }

  depends_on = [
    aws_elasticache_global_replication_group.pyth_oracle,
    aws_elasticache_subnet_group.redis_eu_west_1,
    aws_security_group.redis_eu_west_1
  ]
}

# Supporting resources for us-west-2 and eu-west-1
resource "aws_elasticache_subnet_group" "redis_us_west_2" {
  provider    = aws.us_west_2
  name        = "pyth-oracle-redis-subnet-group-us-west-2"
  subnet_ids  = [aws_subnet.private_us_west_2_a.id, aws_subnet.private_us_west_2_b.id]
  description = "Subnet group for Redis in us-west-2"

  tags = {
    Name        = "pyth-oracle-redis-subnet-group-us-west-2"
    Environment = "production"
  }
}

resource "aws_elasticache_subnet_group" "redis_eu_west_1" {
  provider    = aws.eu_west_1
  name        = "pyth-oracle-redis-subnet-group-eu-west-1"
  subnet_ids  = [aws_subnet.private_eu_west_1_a.id, aws_subnet.private_eu_west_1_b.id]
  description = "Subnet group for Redis in eu-west-1"

  tags = {
    Name        = "pyth-oracle-redis-subnet-group-eu-west-1"
    Environment = "production"
  }
}

resource "aws_security_group" "redis_us_west_2" {
  provider    = aws.us_west_2
  name        = "pyth-oracle-redis-sg-us-west-2"
  description = "Security group for Redis"
  vpc_id      = aws_vpc.us_west_2.id

  ingress {
    description     = "Redis from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_us_west_2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "pyth-oracle-redis-sg-us-west-2"
    Environment = "production"
  }
}

resource "aws_security_group" "redis_eu_west_1" {
  provider    = aws.eu_west_1
  name        = "pyth-oracle-redis-sg-eu-west-1"
  description = "Security group for Redis"
  vpc_id      = aws_vpc.eu_west_1.id

  ingress {
    description     = "Redis from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_eu_west_1.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "pyth-oracle-redis-sg-eu-west-1"
    Environment = "production"
  }
}

