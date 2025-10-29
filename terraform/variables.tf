# Terraform Variables

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "pyth-oracle"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "regions" {
  description = "AWS regions to deploy to"
  type        = map(string)
  default = {
    us_east_1 = "us-east-1"
    us_west_2 = "us-west-2"
    eu_west_1 = "eu-west-1"
  }
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type = map(number)
  default = {
    us_east_1 = 2  # Primary region
    us_west_2 = 1  # Standby region
    eu_west_1 = 1  # Standby region
  }
}

variable "aurora_instance_class" {
  description = "Aurora instance class"
  type        = string
  default     = "db.serverless"
}

variable "aurora_min_capacity" {
  description = "Aurora serverless minimum capacity"
  type        = number
  default     = 0.5
}

variable "aurora_max_capacity" {
  description = "Aurora serverless maximum capacity"
  type        = number
  default     = 2
}

variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.t4g.micro"
}

variable "redis_num_clusters" {
  description = "Number of Redis cache clusters"
  type        = number
  default     = 2
}

variable "container_image" {
  description = "Docker image for keeper"
  type        = string
  default     = "pyth-oracle:latest"
}

variable "container_cpu" {
  description = "Container CPU units"
  type        = number
  default     = 512  # 0.5 vCPU
}

variable "container_memory" {
  description = "Container memory in MB"
  type        = number
  default     = 1024  # 1GB
}

variable "keep_price_history_days" {
  description = "Number of days to keep price history"
  type        = number
  default     = 90
}

variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "enable_alerting" {
  description = "Enable SNS alerting"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

variable "pagerduty_integration_key" {
  description = "PagerDuty integration key"
  type        = string
  sensitive   = true
}

