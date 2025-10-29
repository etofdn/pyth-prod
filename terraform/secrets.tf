# AWS Secrets Manager Configuration

# Primary Private Key Secret - us-east-1
resource "aws_secretsmanager_secret" "private_key_us_east_1" {
  provider = aws.us_east_1
  name     = "pyth-oracle/private-key-us-east-1"
  
  description = "Private key for Pyth Oracle keeper in us-east-1"
  
  tags = {
    Name        = "pyth-oracle-private-key-us-east-1"
    Environment = "production"
  }
}

resource "aws_secretsmanager_secret_version" "private_key_us_east_1" {
  provider      = aws.us_east_1
  secret_id     = aws_secretsmanager_secret.private_key_us_east_1.id
  secret_string = "CHANGE_ME_REPLACE_WITH_ACTUAL_PRIVATE_KEY"
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

# RPC URL Secret
resource "aws_secretsmanager_secret" "rpc_url" {
  provider = aws.us_east_1
  name     = "pyth-oracle/rpc-url"
  
  description = "RPC URL for blockchain connection"
  
  tags = {
    Name        = "pyth-oracle-rpc-url"
    Environment = "production"
  }
}

resource "aws_secretsmanager_secret_version" "rpc_url" {
  provider      = aws.us_east_1
  secret_id     = aws_secretsmanager_secret.rpc_url.id
  secret_string = jsonencode({
    rpc-url = "wss://testnet-eto-y246d.avax-test.network/ext/bc/2hpQwDpDGEa4915WnAp6MP7qCcoP35jqUHFji7p3o9E99UBJmk/ws?token=da37bf16c0a88bb35f2e5c48bc8ce1229913fb135de21d7769a02b21f6c2b0ce"
  })
}

# Contract Address Secret
resource "aws_secretsmanager_secret" "contract_address" {
  provider = aws.us_east_1
  name     = "pyth-oracle/contract-address"
  
  description = "Smart contract address for oracle updates"
  
  tags = {
    Name        = "pyth-oracle-contract-address"
    Environment = "production"
  }
}

resource "aws_secretsmanager_secret_version" "contract_address" {
  provider      = aws.us_east_1
  secret_id     = aws_secretsmanager_secret.contract_address.id
  secret_string = jsonencode({
    contract-address = "0x36df4CF7cB10eD741Ed6EC553365cf515bc07121"
  })
}

# Aurora Password
resource "aws_secretsmanager_secret" "aurora_password" {
  provider = aws.us_east_1
  name     = "pyth-oracle/aurora-password"
  
  description = "Aurora database master password"
  
  recovery_window_in_days = 30
  
  tags = {
    Name        = "pyth-oracle-aurora-password"
    Environment = "production"
  }
}

resource "random_password" "aurora_password" {
  length  = 32
  special = true
}

resource "aws_secretsmanager_secret_version" "aurora_password" {
  provider      = aws.us_east_1
  secret_id     = aws_secretsmanager_secret.aurora_password.id
  secret_string = random_password.aurora_password.result
}

# Rotation configuration for Aurora password
resource "aws_secretsmanager_secret_rotation" "aurora_password" {
  provider      = aws.us_east_1
  secret_id     = aws_secretsmanager_secret.aurora_password.id
  rotation_lambda_arn = aws_lambda_function.aurora_rotation.arn

  rotation_rules {
    automatically_after_days = 90
  }
}

# Lambda for password rotation
resource "aws_lambda_function" "aurora_rotation" {
  provider      = aws.us_east_1
  filename      = "aurora-rotation.zip"
  function_name = "aurora-password-rotation"
  role          = aws_iam_role.lambda_rotation.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 300

  environment {
    variables = {
      SECRET_ARN = aws_secretsmanager_secret.aurora_password.arn
      DATABASE   = aws_rds_cluster.primary.database_name
    }
  }

  tags = {
    Name        = "aurora-rotation-lambda"
    Environment = "production"
  }
}

# IAM role for Lambda rotation
resource "aws_iam_role" "lambda_rotation" {
  provider = aws.us_east_1
  name     = "lambda-aurora-rotation-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_rotation" {
  provider   = aws.us_east_1
  role       = aws_iam_role.lambda_rotation.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_rotation_secrets" {
  provider = aws.us_east_1
  role     = aws_iam_role.lambda_rotation.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage"
        ]
        Resource = aws_secretsmanager_secret.aurora_password.arn
      },
      {
        Effect = "Allow"
        Action = [
          "rds:DescribeDBClusters",
          "rds:ModifyDBCluster"
        ]
        Resource = aws_rds_cluster.primary.arn
      }
    ]
  })
}

