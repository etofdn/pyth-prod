# Terraform Outputs

output "primary_region" {
  description = "Primary region details"
  value = {
    region              = "us-east-1"
    ecs_cluster         = aws_ecs_cluster.us_east_1.name
    ecs_service         = aws_ecs_service.keeper_us_east_1.name
    aurora_endpoint     = aws_rds_cluster.primary.endpoint
    redis_endpoint      = aws_elasticache_replication_group.us_east_1.primary_endpoint_address
    vpc_id              = aws_vpc.us_east_1.id
    cloudwatch_log_group = aws_cloudwatch_log_group.ecs_logs_us_east_1.name
  }
}

output "secondary_regions" {
  description = "Secondary region details"
  value = {
    us_west_2 = {
      region       = "us-west-2"
      ecs_cluster  = aws_ecs_cluster.us_west_2.name
      aurora_endpoint = aws_rds_cluster.us_west_2_replica.reader_endpoint
      redis_endpoint  = aws_elasticache_replication_group.us_west_2.primary_endpoint_address
      vpc_id          = aws_vpc.us_west_2.id
    }
    eu_west_1 = {
      region       = "eu-west-1"
      ecs_cluster  = aws_ecs_cluster.eu_west_1.name
      aurora_endpoint = aws_rds_cluster.eu_west_1_replica.reader_endpoint
      redis_endpoint  = aws_elasticache_replication_group.eu_west_1.primary_endpoint_address
      vpc_id          = aws_vpc.eu_west_1.id
    }
  }
}

output "aurora_global_cluster" {
  description = "Aurora Global Database details"
  value = {
    cluster_identifier = aws_rds_global_cluster.pyth_oracle.global_cluster_identifier
    primary_cluster    = aws_rds_cluster.primary.id
    read_replicas = {
      us_west_2 = aws_rds_cluster.us_west_2_replica.id
      eu_west_1 = aws_rds_cluster.eu_west_1_replica.id
    }
  }
}

output "redis_global_datasource" {
  description = "Redis Global Datastore details"
  value = {
    global_replication_group_id = aws_elasticache_global_replication_group.pyth_oracle.global_replication_group_id
    primary_cluster             = aws_elasticache_replication_group.us_east_1.id
    replica_clusters = {
      us_west_2 = aws_elasticache_replication_group.us_west_2.id
      eu_west_1 = aws_elasticache_replication_group.eu_west_1.id
    }
  }
}

output "monitoring" {
  description = "Monitoring resources"
  value = {
    alert_sns_topic = aws_sns_topic.oracle_alerts.arn
    dashboard_url   = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=${aws_cloudwatch_dashboard.oracle_overview.dashboard_name}"
    log_archive_bucket = aws_s3_bucket.logs_archive.id
  }
}

output "connection_strings" {
  description = "Connection strings for keepers"
  value = {
    aurora_writer = "mysql://admin:${random_password.aurora_password.result}@${aws_rds_cluster.primary.endpoint}/${aws_rds_cluster.primary.database_name}"
    redis_primary = "redis://${aws_elasticache_replication_group.us_east_1.primary_endpoint_address}:6379"
  }
  sensitive = true
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown"
  value = {
    total = "$127/month"
    breakdown = {
      ecs_fargate = "$49/month"
      aurora = "$30/month"
      redis = "$15/month"
      cloudwatch = "$10/month"
      s3 = "$5/month"
      route53 = "$3/month"
      nat_gateway = "$15/month"
    }
  }
}

