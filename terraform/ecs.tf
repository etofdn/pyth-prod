# ECS Fargate Configuration for Multi-Region Deployment

# ECS Cluster in us-east-1
resource "aws_ecs_cluster" "us_east_1" {
  provider = aws.us_east_1
  name     = "pyth-oracle-cluster-us-east-1"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "pyth-oracle-cluster-us-east-1"
    Environment = "production"
  }
}

# ECS Cluster in us-west-2
resource "aws_ecs_cluster" "us_west_2" {
  provider = aws.us_west_2
  name     = "pyth-oracle-cluster-us-west-2"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "pyth-oracle-cluster-us-west-2"
    Environment = "production"
  }
}

# ECS Cluster in eu-west-1
resource "aws_ecs_cluster" "eu_west_1" {
  provider = aws.eu_west_1
  name     = "pyth-oracle-cluster-eu-west-1"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "pyth-oracle-cluster-eu-west-1"
    Environment = "production"
  }
}

# Task Execution Role - us-east-1
resource "aws_iam_role" "ecs_task_execution_role_us_east_1" {
  provider = aws.us_east_1
  name     = "pyth-oracle-task-exec-role-us-east-1"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_us_east_1" {
  provider   = aws.us_east_1
  role       = aws_iam_role.ecs_task_execution_role_us_east_1.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Role - us-east-1
resource "aws_iam_role" "ecs_task_role_us_east_1" {
  provider = aws.us_east_1
  name     = "pyth-oracle-task-role-us-east-1"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs_logs_us_east_1" {
  provider          = aws.us_east_1
  name              = "/ecs/pyth-oracle-keeper"
  retention_in_days = 30

  tags = {
    Name        = "pyth-oracle-logs-us-east-1"
    Environment = "production"
  }
}

# Task Definition - us-east-1
resource "aws_ecs_task_definition" "keeper_us_east_1" {
  provider             = aws.us_east_1
  family               = "pyth-oracle-keeper-us-east-1"
  network_mode         = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                  = "512"   # 0.5 vCPU
  memory               = "1024"  # 1GB
  task_role_arn        = aws_iam_role.ecs_task_role_us_east_1.arn
  execution_role_arn   = aws_iam_role.ecs_task_execution_role_us_east_1.arn

  container_definitions = jsonencode([{
    name  = "pyth-keeper"
    image = "${var.account_id}.dkr.ecr.us-east-1.amazonaws.com/pyth-oracle:latest"

    portMappings = [{
      containerPort = 9090
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "REGION"
        value = "us-east-1"
      },
      {
        name  = "PRIMARY_REGION"
        value = "true"
      },
      {
        name  = "REPLICA_COUNT"
        value = "2"
      }
    ]

    secrets = [
      {
        name      = "PRIVATE_KEY"
        valueFrom = aws_secretsmanager_secret.private_key_us_east_1.arn
      },
      {
        name      = "RPC_URL"
        valueFrom = "${aws_secretsmanager_secret.rpc_url.arn}:rpc-url::"
      },
      {
        name      = "CONTRACT_ADDRESS"
        valueFrom = "${aws_secretsmanager_secret.contract_address.arn}:contract-address::"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs_us_east_1.name
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "keeper"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "node /app/healthcheck.js"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 40
    }
  }])

  tags = {
    Name        = "pyth-oracle-task-def-us-east-1"
    Environment = "production"
  }
}

# ECS Service - us-east-1 (Primary with 2 replicas)
resource "aws_ecs_service" "keeper_us_east_1" {
  provider      = aws.us_east_1
  name          = "pyth-oracle-service-us-east-1"
  cluster       = aws_ecs_cluster.us_east_1.id
  desired_count = 2  # Primary region has 2 keepers

  task_definition = aws_ecs_task_definition.keeper_us_east_1.arn
  launch_type     = "FARGATE"
  platform_version = "LATEST"

  network_configuration {
    subnets          = [aws_subnet.private_us_east_1_a.id, aws_subnet.private_us_east_1_b.id]
    security_groups  = [aws_security_group.ecs_us_east_1.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.keeper_us_east_1.arn
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  enable_execute_command = true

  tags = {
    Name        = "pyth-oracle-service-us-east-1"
    Environment = "production"
  }

  depends_on = [
    aws_service_discovery_service.keeper_us_east_1
  ]
}

# Similar configuration for us-west-2 and eu-west-1 (simplified)
# Note: Full implementation would include all 3 regions with similar resources

# Security Group for ECS tasks
resource "aws_security_group" "ecs_us_east_1" {
  provider    = aws.us_east_1
  name        = "pyth-oracle-ecs-sg-us-east-1"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.us_east_1.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "pyth-oracle-ecs-sg-us-east-1"
    Environment = "production"
  }
}

# Service Discovery for internal communication
resource "aws_service_discovery_private_dns_namespace" "pyth_us_east_1" {
  provider = aws.us_east_1
  name     = "pyth-oracle.local"
  vpc      = aws_vpc.us_east_1.id
}

resource "aws_service_discovery_service" "keeper_us_east_1" {
  provider = aws.us_east_1
  name     = "keeper"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.pyth_us_east_1.id

    dns_records {
      ttl  = 10
      type = "A"
    }
  }
}

