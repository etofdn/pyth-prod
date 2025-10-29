# CloudWatch Monitoring and Alerting Configuration

# SNS Topic for alerts
resource "aws_sns_topic" "oracle_alerts" {
  provider = aws.us_east_1
  name     = "pyth-oracle-alerts"

  tags = {
    Name        = "pyth-oracle-alerts"
    Environment = "production"
  }
}

# CloudWatch Alarms

# Alarm: Oracle Stale (> 60s)
resource "aws_cloudwatch_metric_alarm" "oracle_stale" {
  provider            = aws.us_east_1
  alarm_name          = "pyth-oracle-stale"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "OracleStale"
  namespace           = "PythOracle"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "60"
  alarm_description   = "Oracle price staleness exceeded 60 seconds"
  alarm_actions       = [aws_sns_topic.oracle_alerts.arn]
  treat_missing_data  = "breaching"

  tags = {
    Name        = "pyth-oracle-stale-alarm"
    Environment = "production"
  }
}

# Alarm: SSE Connection Down
resource "aws_cloudwatch_metric_alarm" "sse_down" {
  provider            = aws.us_east_1
  alarm_name          = "pyth-oracle-sse-down"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "4"
  metric_name         = "SSEConnected"
  namespace           = "PythOracle"
  period              = "30"
  statistic           = "Minimum"
  threshold           = "1"
  alarm_description   = "SSE connection down for more than 2 minutes"
  alarm_actions       = [aws_sns_topic.oracle_alerts.arn]

  tags = {
    Name        = "pyth-oracle-sse-down-alarm"
    Environment = "production"
  }
}

# Alarm: Transaction Failure Rate
resource "aws_cloudwatch_metric_alarm" "tx_failure_rate" {
  provider            = aws.us_east_1
  alarm_name          = "pyth-oracle-tx-failure-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "TransactionFailureRate"
  namespace           = "PythOracle"
  period              = "300"
  statistic           = "Average"
  threshold           = "0.1"
  alarm_description   = "Transaction failure rate exceeded 10%"
  alarm_actions       = [aws_sns_topic.oracle_alerts.arn]

  tags = {
    Name        = "pyth-oracle-tx-failure-rate-alarm"
    Environment = "production"
  }
}

# Alarm: Low Wallet Balance
resource "aws_cloudwatch_metric_alarm" "low_balance" {
  provider            = aws.us_east_1
  alarm_name          = "pyth-oracle-low-balance"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "WalletBalance"
  namespace           = "PythOracle"
  period              = "300"
  statistic           = "Minimum"
  threshold           = "1"
  alarm_description   = "Wallet balance below 1 AVAX"
  alarm_actions       = [aws_sns_topic.oracle_alerts.arn]
  unit                = "None"

  tags = {
    Name        = "pyth-oracle-low-balance-alarm"
    Environment = "production"
  }
}

# Alarm: ECS Task Stopped
resource "aws_cloudwatch_metric_alarm" "ecs_task_stopped" {
  provider            = aws.us_east_1
  alarm_name          = "pyth-oracle-ecs-task-stopped"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "DesiredTaskCount"
  namespace           = "AWS/ECS"
  period              = "60"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "All ECS tasks stopped"
  alarm_actions       = [aws_sns_topic.oracle_alerts.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.us_east_1.name
    ServiceName = aws_ecs_service.keeper_us_east_1.name
  }

  tags = {
    Name        = "pyth-oracle-ecs-task-stopped-alarm"
    Environment = "production"
  }
}

# CloudWatch Log Group for Aurora
resource "aws_cloudwatch_log_group" "aurora_slow_query" {
  provider          = aws.us_east_1
  name              = "/aws/rds/cluster/pyth-oracle-primary/slowquery"
  retention_in_days = 7

  tags = {
    Name        = "pyth-oracle-aurora-slow-query-logs"
    Environment = "production"
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "oracle_overview" {
  provider        = aws.us_east_1
  dashboard_name  = "pyth-oracle-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["PythOracle", "PriceUpdateLatency"],
            ["PythOracle", "SSEConnected", { "stat" = "Average" }],
            [".", "TransactionSuccess", { "stat" = "Sum" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Oracle Performance Overview"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { "stat" = "Average" }],
            ["AWS/ECS", "MemoryUtilization", { "stat" = "Average" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "ECS Resource Utilization"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6

        properties = {
          metrics = [
            ["PythOracle", "OracleStale"],
            ["PythOracle", "LastUpdateAge"],
            [".", "WalletBalance"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Oracle Health Metrics"
          period  = 300
        }
      }
    ]
  })
}

# S3 Bucket for long-term log storage
resource "aws_s3_bucket" "logs_archive" {
  provider = aws.us_east_1
  bucket   = "pyth-oracle-logs-archive-${var.account_id}"

  tags = {
    Name        = "pyth-oracle-logs-archive"
    Environment = "production"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs_lifecycle" {
  provider = aws.us_east_1
  bucket   = aws_s3_bucket.logs_archive.id

  rule {
    id     = "transition_to_glacier"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }

  rule {
    id     = "expire_old_logs"
    status = "Enabled"

    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_versioning" "logs_versioning" {
  provider = aws.us_east_1
  bucket   = aws_s3_bucket.logs_archive.id

  versioning_configuration {
    status = "Enabled"
  }
}

