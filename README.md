# Pyth Oracle Multi-Region Production Deployment

Production-ready Pyth Oracle keeper system with high availability, cross-region failover, and comprehensive monitoring deployed on AWS.

## Architecture

- **3 AWS Regions**: us-east-1 (primary), us-west-2, eu-west-1 (standby)
- **ECS Fargate Spot**: Cost-optimized container deployment
- **Aurora Serverless v2 Global**: Multi-region database with automatic scaling
- **ElastiCache Global Datastore**: Redis for distributed state coordination
- **CloudWatch**: Centralized monitoring, logging, and alerting
- **Cost**: ~$127/month

## Features

✅ **Multi-Region Deployment** - Automatic failover across 3 regions  
✅ **Leader Election** - Distributed coordination via Redis  
✅ **Nonce Management** - Atomic nonce coordination prevents conflicts  
✅ **Data Persistence** - Historical prices stored in Aurora (90-day retention)  
✅ **Comprehensive Monitoring** - CloudWatch dashboards and SNS alerts  
✅ **Graceful Shutdown** - Clean disconnection on scale-down  
✅ **Cost Optimized** - Fargate Spot, Aurora Serverless, ARM-based Redis

## Quick Start

### 1. Prerequisites

- AWS account with access to us-east-1, us-west-2, eu-west-1
- Terraform >= 1.5.0
- AWS CLI configured
- Node.js 18+

### 2. Configure Secrets

```bash
# Set your AWS credentials
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key

# Configure Terraform variables
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Review deployment plan
terraform plan

# Deploy infrastructure
terraform apply

# Save outputs
terraform output > ../deployment-outputs.json
```

### 4. Build and Deploy Docker Image

```bash
# Build image
docker build -t pyth-oracle:latest .

# Tag for ECR
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker tag pyth-oracle:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/pyth-oracle:latest

# Push to all regions
aws ecr create-repository --repository-name pyth-oracle --region us-east-1 2>/dev/null || true
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/pyth-oracle:latest

# Repeat for us-west-2 and eu-west-1
aws ecr create-repository --repository-name pyth-oracle --region us-west-2 2>/dev/null || true
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/pyth-oracle:latest

aws ecr create-repository --repository-name pyth-oracle --region eu-west-1 2>/dev/null || true
docker push $AWS_ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com/pyth-oracle:latest
```

### 5. Update Task Definitions

```bash
# Update account ID in ECS task definitions
cd terraform
terraform apply -var="account_id=$AWS_ACCOUNT_ID"
```

### 6. Verify Deployment

```bash
# Check ECS services
aws ecs list-services --cluster pyth-oracle-cluster-us-east-1 --region us-east-1

# Check Aurora clusters
aws rds describe-db-clusters --region us-east-1

# Check Redis replication groups
aws elasticache describe-replication-groups --region us-east-1

# View CloudWatch dashboard
aws cloudwatch get-dashboard --dashboard-name pyth-oracle-overview --region us-east-1
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PRIVATE_KEY` | Wallet private key | `0x...` |
| `RPC_URL` | Blockchain RPC endpoint | `wss://...` |
| `CONTRACT_ADDRESS` | Oracle contract address | `0x36df4CF7cB...` |
| `REGION` | AWS region | `us-east-1` |
| `REDIS_URL` | Redis connection string | `redis://...` |
| `AURORA_WRITER_ENDPOINT` | Aurora writer endpoint | `cluster.xxx.us-east-1.rds.amazonaws.com` |
| `AURORA_PASSWORD` | Aurora database password | `***` |

### Terraform Variables

Edit `terraform/terraform.tfvars`:

```hcl
account_id = "123456789012"
alert_email = "admin@example.com"
pagerduty_integration_key = "your_key_here"
```

## Monitoring

### CloudWatch Dashboard

Access the dashboard:
```
AWS Console > CloudWatch > Dashboards > pyth-oracle-overview
```

### Key Metrics

- Oracle staleness (seconds)
- Transaction success rate
- SSE connection status
- Wallet balance
- Gas costs

### Alerts

Critical alerts are sent to SNS topic `pyth-oracle-alerts`:
- Oracle stale > 60s
- SSE connection down > 2 minutes
- Transaction failure rate > 10%
- Wallet balance < 1 AVAX

## Cost Breakdown

| Component | Monthly Cost |
|-----------|--------------|
| ECS Fargate Spot (4 tasks) | $49 |
| Aurora Serverless v2 | $30 |
| ElastiCache Redis | $15 |
| CloudWatch Logs | $10 |
| S3 + Glacier | $5 |
| Route53 Health Checks | $3 |
| NAT Gateway | $15 |
| **Total** | **$127/month** |

## Failover Testing

```bash
# Simulate region failure
aws ecs update-service \
  --cluster pyth-oracle-cluster-us-east-1 \
  --service pyth-oracle-service-us-east-1 \
  --desired-count 0 \
  --region us-east-1

# Verify failover to us-west-2 or eu-west-1
aws ecs describe-services \
  --cluster pyth-oracle-cluster-us-west-2 \
  --services pyth-oracle-service-us-west-2 \
  --region us-west-2
```

## Troubleshooting

### Connection Issues

```bash
# Check Redis connection
aws elasticache describe-replication-groups --region us-east-1

# Check Aurora connection
aws rds describe-db-clusters --region us-east-1

# Check ECS logs
aws logs tail /ecs/pyth-oracle-keeper --follow --region us-east-1
```

### Leader Election Issues

```bash
# Check current leader
aws elasticache describe-cache-clusters --region us-east-1

# Force leader election
aws ecs restart-task \
  --cluster pyth-oracle-cluster-us-east-1 \
  --task <task-id> \
  --region us-east-1
```

## Project Structure

```
pyth-prod/
├── terraform/           # Infrastructure as Code
│   ├── main.tf         # VPC, subnets, routing
│   ├── ecs.tf          # ECS Fargate configuration
│   ├── aurora.tf       # Aurora Global Database
│   ├── redis.tf        # ElastiCache Global Datastore
│   ├── monitoring.tf   # CloudWatch, alarms
│   ├── secrets.tf      # Secrets Manager
│   ├── variables.tf    # Configuration variables
│   └── outputs.tf      # Deployment outputs
├── src/
│   ├── keeper/
│   │   └── StateManager.js    # Distributed state management
│   └── db/
│       └── AuroraClient.js    # Database operations
├── production-keeper-sse.js   # Main keeper application
├── Dockerfile                  # Container image
├── docker-compose.yml         # Local development
├── monitoring/                # Prometheus, Grafana configs
└── package.json              # Dependencies
```

## License

MIT

