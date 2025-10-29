# Aurora Serverless v2 Global Database Configuration

# DB Subnet Group for us-east-1
resource "aws_db_subnet_group" "aurora_us_east_1" {
  provider    = aws.us_east_1
  name        = "pyth-oracle-aurora-subnet-group-us-east-1"
  subnet_ids  = [aws_subnet.private_us_east_1_a.id, aws_subnet.private_us_east_1_b.id]
  description = "Subnet group for Aurora database in us-east-1"

  tags = {
    Name        = "pyth-oracle-aurora-subnet-group-us-east-1"
    Environment = "production"
  }
}

# DB Subnet Group for us-west-2
resource "aws_db_subnet_group" "aurora_us_west_2" {
  provider    = aws.us_west_2
  name        = "pyth-oracle-aurora-subnet-group-us-west-2"
  subnet_ids  = [aws_subnet.private_us_west_2_a.id, aws_subnet.private_us_west_2_b.id]
  description = "Subnet group for Aurora database in us-west-2"

  tags = {
    Name        = "pyth-oracle-aurora-subnet-group-us-west-2"
    Environment = "production"
  }
}

# DB Subnet Group for eu-west-1
resource "aws_db_subnet_group" "aurora_eu_west_1" {
  provider    = aws.eu_west_1
  name        = "pyth-oracle-aurora-subnet-group-eu-west-1"
  subnet_ids  = [aws_subnet.private_eu_west_1_a.id, aws_subnet.private_eu_west_1_b.id]
  description = "Subnet group for Aurora database in eu-west-1"

  tags = {
    Name        = "pyth-oracle-aurora-subnet-group-eu-west-1"
    Environment = "production"
  }
}

# Security Group for Aurora
resource "aws_security_group" "aurora_us_east_1" {
  provider    = aws.us_east_1
  name        = "pyth-oracle-aurora-sg-us-east-1"
  description = "Security group for Aurora database"
  vpc_id      = aws_vpc.us_east_1.id

  ingress {
    description     = "MySQL/Aurora from ECS tasks"
    from_port       = 3306
    to_port         = 3306
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
    Name        = "pyth-oracle-aurora-sg-us-east-1"
    Environment = "production"
  }
}

# Aurora Cluster - Primary (us-east-1)
resource "aws_rds_cluster" "primary" {
  provider = aws.us_east_1
  
  cluster_identifier      = "pyth-oracle-primary"
  engine                  = "aurora-mysql"
  engine_mode             = "provisioned"
  engine_version          = "8.0.mysql_aurora.3.04.1"
  database_name           = "pythoracle"
  master_username         = "admin"
  master_password         = random_password.aurora_password.result
  
  db_subnet_group_name    = aws_db_subnet_group.aurora_us_east_1.name
  vpc_security_group_ids  = [aws_security_group.aurora_us_east_1.id]
  
  serverlessv2_scaling_configuration {
    max_capacity = 2
    min_capacity = 0.5
  }

  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"
  
  enabled_cloudwatch_logs_exports = ["error", "slow_query", "general"]
  
  skip_final_snapshot       = false
  final_snapshot_identifier = "pyth-oracle-final-snapshot-${timestamp()}"

  tags = {
    Name        = "pyth-oracle-aurora-primary"
    Environment = "production"
  }

  depends_on = [aws_db_subnet_group.aurora_us_east_1]
}

# Aurora Instance - Primary
resource "aws_rds_cluster_instance" "primary" {
  provider = aws.us_east_1
  
  identifier         = "pyth-oracle-primary-instance"
  cluster_identifier = aws_rds_cluster.primary.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.primary.engine
  engine_version     = aws_rds_cluster.primary.engine_version
  
  performance_insights_enabled = true
  
  tags = {
    Name        = "pyth-oracle-primary-instance"
    Environment = "production"
  }
}

# Aurora Global Database
resource "aws_rds_global_cluster" "pyth_oracle" {
  provider                  = aws.us_east_1
  global_cluster_identifier = "pyth-oracle-global"
  engine                    = "aurora-mysql"
  engine_version            = "8.0.mysql_aurora.3.04.1"
  database_name             = "pythoracle"
  
  tags = {
    Name        = "pyth-oracle-global-cluster"
    Environment = "production"
  }
}

# Associate primary cluster with global cluster
resource "aws_rds_cluster_instance" "primary_global" {
  provider = aws.us_east_1
  
  identifier         = "pyth-oracle-primary-global"
  cluster_identifier = aws_rds_cluster.primary.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.primary.engine
  
  tags = {
    Name = "pyth-oracle-primary-global"
  }
  
  depends_on = [aws_rds_global_cluster.pyth_oracle]
}

# Read Replica in us-west-2
resource "aws_rds_cluster" "us_west_2_replica" {
  provider = aws.us_west_2
  
  cluster_identifier   = "pyth-oracle-us-west-2"
  engine               = aws_rds_global_cluster.pyth_oracle.engine
  engine_version       = aws_rds_global_cluster.pyth_oracle.engine_version
  global_cluster_identifier = aws_rds_global_cluster.pyth_oracle.id
  database_name        = "pythoracle"
  
  db_subnet_group_name    = aws_db_subnet_group.aurora_us_west_2.name
  vpc_security_group_ids  = [aws_security_group.aurora_us_west_2.id]
  
  serverlessv2_scaling_configuration {
    max_capacity = 2
    min_capacity = 0.5
  }

  skip_final_snapshot = true

  tags = {
    Name        = "pyth-oracle-aurora-us-west-2"
    Environment = "production"
  }

  depends_on = [
    aws_db_subnet_group.aurora_us_west_2,
    aws_rds_global_cluster.pyth_oracle
  ]
}

resource "aws_rds_cluster_instance" "us_west_2_replica" {
  provider = aws.us_west_2
  
  identifier         = "pyth-oracle-us-west-2-instance"
  cluster_identifier = aws_rds_cluster.us_west_2_replica.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.us_west_2_replica.engine
  
  tags = {
    Name = "pyth-oracle-us-west-2-instance"
  }
}

# Read Replica in eu-west-1
resource "aws_rds_cluster" "eu_west_1_replica" {
  provider = aws.eu_west_1
  
  cluster_identifier   = "pyth-oracle-eu-west-1"
  engine               = aws_rds_global_cluster.pyth_oracle.engine
  engine_version       = aws_rds_global_cluster.pyth_oracle.engine_version
  global_cluster_identifier = aws_rds_global_cluster.pyth_oracle.id
  database_name        = "pythoracle"
  
  db_subnet_group_name    = aws_db_subnet_group.aurora_eu_west_1.name
  vpc_security_group_ids  = [aws_security_group.aurora_eu_west_1.id]
  
  serverlessv2_scaling_configuration {
    max_capacity = 2
    min_capacity = 0.5
  }

  skip_final_snapshot = true

  tags = {
    Name        = "pyth-oracle-aurora-eu-west-1"
    Environment = "production"
  }

  depends_on = [
    aws_db_subnet_group.aurora_eu_west_1,
    aws_rds_global_cluster.pyth_oracle
  ]
}

resource "aws_rds_cluster_instance" "eu_west_1_replica" {
  provider = aws.eu_west_1
  
  identifier         = "pyth-oracle-eu-west-1-instance"
  cluster_identifier = aws_rds_cluster.eu_west_1_replica.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.eu_west_1_replica.engine
  
  tags = {
    Name = "pyth-oracle-eu-west-1-instance"
  }
}

# Data source for Aurora password
data "aws_secretsmanager_secret_version" "aurora_password" {
  provider  = aws.us_east_1
  secret_id = aws_secretsmanager_secret.aurora_password.id
}

# Security groups for other regions
resource "aws_security_group" "aurora_us_west_2" {
  provider    = aws.us_west_2
  name        = "pyth-oracle-aurora-sg-us-west-2"
  description = "Security group for Aurora database"
  vpc_id      = aws_vpc.us_west_2.id

  ingress {
    description = "MySQL/Aurora from ECS tasks"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    security_groups = [aws_security_group.ecs_us_west_2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "pyth-oracle-aurora-sg-us-west-2"
    Environment = "production"
  }
}

resource "aws_security_group" "aurora_eu_west_1" {
  provider    = aws.eu_west_1
  name        = "pyth-oracle-aurora-sg-eu-west-1"
  description = "Security group for Aurora database"
  vpc_id      = aws_vpc.eu_west_1.id

  ingress {
    description = "MySQL/Aurora from ECS tasks"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    security_groups = [aws_security_group.ecs_eu_west_1.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "pyth-oracle-aurora-sg-eu-west-1"
    Environment = "production"
  }
}

resource "aws_security_group" "ecs_us_west_2" {
  provider    = aws.us_west_2
  name        = "pyth-oracle-ecs-sg-us-west-2"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.us_west_2.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "pyth-oracle-ecs-sg-us-west-2"
    Environment = "production"
  }
}

resource "aws_security_group" "ecs_eu_west_1" {
  provider    = aws.eu_west_1
  name        = "pyth-oracle-ecs-sg-eu-west-1"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.eu_west_1.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "pyth-oracle-ecs-sg-eu-west-1"
    Environment = "production"
  }
}

