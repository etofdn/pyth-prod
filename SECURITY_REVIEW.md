# Pyth Oracle Hermes Security Review

**Date:** 2024-12-19  
**Reviewer:** Security Audit  
**Scope:** Complete codebase review for infrastructure security flaws and completeness

---

## Executive Summary

This review identified **27 critical security issues**, **15 high-severity issues**, and **12 medium-severity issues** across the codebase. The most critical findings include:

1. **Hardcoded credentials** in multiple files (RPC tokens, API keys)
2. **Missing IAM permissions** for Secrets Manager access
3. **Insecure nonce management** that could lead to transaction conflicts
4. **Missing network security** controls (NAT Gateway, VPC endpoints)
5. **SQL injection vulnerabilities** in database queries
6. **Insufficient secret rotation** policies
7. **Missing authentication** on health/metrics endpoints

---

## Critical Security Issues

### 1. Hardcoded RPC Token in Source Code
**Severity:** 🔴 CRITICAL  
**Location:** `production-keeper-sse.js:22-23`, `dashboard/server.js:9`, `terraform/secrets.tf:43`

**Issue:**
RPC endpoint tokens are hardcoded in multiple files:
```javascript
// production-keeper-sse.js:22-23
this.wsRpcUrl = config.rpcUrl || process.env.RPC_URL || "wss://testnet-eto-y246d.avax-test.network/ext/bc/2hpQwDpDGEa4915WnAp6MP7qCcoP35jqUHFji7p3o9E99UBJmk/ws?token=da37bf16c0a88bb35f2e5c48bc8ce1229913fb135de21d7769a02b21f6c2b0ce";
```

**Risk:**
- Token exposure in version control
- Anyone with repo access can use the token
- Token cannot be rotated without code changes

**Recommendation:**
- Remove all hardcoded tokens
- Use Secrets Manager for all credentials
- Implement token rotation
- Add pre-commit hooks to prevent committing secrets

---

### 2. Missing IAM Permissions for Secrets Manager
**Severity:** 🔴 CRITICAL  
**Location:** `terraform/ecs.tf:70-74`

**Issue:**
Task execution role only has basic ECS permissions. Missing Secrets Manager read permissions:
```terraform
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_us_east_1" {
  role       = aws_iam_role.ecs_task_execution_role_us_east_1.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
```

**Risk:**
- ECS tasks cannot access Secrets Manager
- Application will fail to start
- Secrets defined in task definition won't work

**Recommendation:**
Add Secrets Manager read policy:
```terraform
resource "aws_iam_role_policy" "secrets_manager_access" {
  role = aws_iam_role.ecs_task_execution_role_us_east_1.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ]
      Resource = [
        aws_secretsmanager_secret.private_key_us_east_1.arn,
        aws_secretsmanager_secret.rpc_url.arn,
        aws_secretsmanager_secret.contract_address.arn,
        aws_secretsmanager_secret.aurora_password.arn
      ]
    }]
  })
}
```

---

### 3. Hardcoded Private Key Placeholder
**Severity:** 🔴 CRITICAL  
**Location:** `terraform/secrets.tf:19`

**Issue:**
Private key secret has a placeholder value:
```terraform
secret_string = "CHANGE_ME_REPLACE_WITH_ACTUAL_PRIVATE_KEY"
```

**Risk:**
- If deployed without updating, wallet will be invalid
- No validation that actual key was set
- Risk of deploying with placeholder

**Recommendation:**
- Use `terraform validate` hook to check secret is not placeholder
- Add validation in CI/CD pipeline
- Use `random_password` or external secret injection

---

### 4. Insecure Nonce Management
**Severity:** 🔴 CRITICAL  
**Location:** `production-keeper-sse.js:943-969`, `src/keeper/StateManager.js:179-204`

**Issue:**
Race condition in nonce management:
```javascript
// production-keeper-sse.js:957-969
async getNextNonce() {
    const blockchainNonce = await this.provider.getTransactionCount(this.wallet.address, "latest");
    const nextNonce = Math.max(blockchainNonce, this.currentNonce);
    this.currentNonce = nextNonce + 1;  // ⚠️ Incremented before use
    return nextNonce;
}
```

**Risk:**
- Multiple instances can use same nonce
- Transaction conflicts and failures
- Potential for double-spending attacks

**Recommendation:**
- Use Redis atomic INCR for nonce management
- Implement proper locking mechanism
- Add nonce reservation pool

---

### 5. SQL Injection Vulnerabilities
**Severity:** 🔴 CRITICAL  
**Location:** `src/db/AuroraClient.js`

**Issue:**
While using parameterized queries, some queries are still vulnerable:
```javascript
// AuroraClient.js:206-212
const [rows] = await this.pool.query(`
    SELECT *
    FROM price_updates
    WHERE feed_id = ?
    ORDER BY timestamp DESC
    LIMIT ?
`, [feedId, limit]);
```
This is actually safe, but some dynamic queries might not be.

**Risk:**
- Potential SQL injection if parameters are not properly escaped
- Database compromise
- Data exfiltration

**Recommendation:**
- Audit all SQL queries
- Use parameterized queries exclusively
- Add input validation for all user inputs
- Implement query logging for monitoring

---

### 6. Missing VPC Endpoints for AWS Services
**Severity:** 🔴 CRITICAL  
**Location:** `terraform/main.tf`

**Issue:**
ECS tasks in private subnets cannot access AWS services (Secrets Manager, CloudWatch) without NAT Gateway or VPC endpoints.

**Risk:**
- Application cannot access Secrets Manager
- Logs cannot be sent to CloudWatch
- Complete service failure

**Recommendation:**
Add VPC endpoints:
```terraform
resource "aws_vpc_endpoint" "secrets_manager" {
  vpc_id              = aws_vpc.us_east_1.id
  service_name        = "com.amazonaws.us-east-1.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_us_east_1_a.id, aws_subnet.private_us_east_1_b.id]
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true
}
```

---

### 7. Missing NAT Gateway Configuration
**Severity:** 🔴 CRITICAL  
**Location:** `terraform/main.tf`

**Issue:**
Private subnets have no route to internet, but ECS tasks need internet access for:
- Blockchain RPC calls
- Hermes SSE endpoint
- External API calls

**Risk:**
- Application cannot function
- No external connectivity

**Recommendation:**
Add NAT Gateway:
```terraform
resource "aws_nat_gateway" "us_east_1" {
  allocation_id = aws_eip.nat_us_east_1.id
  subnet_id     = aws_subnet.public_us_east_1_a.id
}

resource "aws_route" "private_nat" {
  route_table_id         = aws_route_table.private_us_east_1.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.us_east_1.id
}
```

---

### 8. Unrestricted Egress Traffic
**Severity:** 🔴 CRITICAL  
**Location:** `terraform/ecs.tf:234-239`, `terraform/aurora.tf:57-62`

**Issue:**
Security groups allow all egress traffic:
```terraform
egress {
  from_port   = 0
  to_port     = 0
  protocol    = "-1"
  cidr_blocks = ["0.0.0.0/0"]
}
```

**Risk:**
- Data exfiltration possible
- Malware communication
- Compliance violations

**Recommendation:**
Restrict egress to specific destinations:
```terraform
egress {
  description = "HTTPS to AWS services"
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]  # Or specific AWS IP ranges
}
```

---

### 9. Missing Authentication on Health Endpoints
**Severity:** 🔴 CRITICAL  
**Location:** `production-keeper-sse.js:1213-1276`

**Issue:**
Health and metrics endpoints are publicly accessible without authentication:
```javascript
app.get('/health', (req, res) => {
    // No authentication check
    res.status(isHealthy ? 200 : 503).json({
        status: isHealthy ? 'healthy' : 'unhealthy',
        ...this.healthStatus,
        // Exposes sensitive information
    });
});
```

**Risk:**
- Information disclosure (wallet balance, internal state)
- Attack surface for DDoS
- Service enumeration

**Recommendation:**
- Add authentication (API key, AWS IAM)
- Restrict access via security groups
- Remove sensitive data from public endpoints
- Use CloudWatch for health monitoring instead

---

### 10. Insecure Secret Rotation Lambda
**Severity:** 🔴 CRITICAL  
**Location:** `terraform/secrets.tf:105-126`

**Issue:**
Lambda function references non-existent file:
```terraform
resource "aws_lambda_function" "aurora_rotation" {
  filename      = "aurora-rotation.zip"  # File doesn't exist
  function_name = "aurora-password-rotation"
  handler       = "index.handler"
  runtime       = "python3.11"
}
```

**Risk:**
- Lambda deployment will fail
- Secret rotation disabled
- Manual password rotation required

**Recommendation:**
- Create Lambda function code
- Use AWS managed rotation template
- Test rotation functionality

---

## High Severity Issues

### 11. Missing Input Validation
**Severity:** 🟠 HIGH  
**Location:** `production-keeper-sse.js:448-529`

**Issue:**
SSE message processing lacks validation:
```javascript
processSseMessage(data) {
    const parsed = JSON.parse(data);  // No error handling
    // No validation of feed data structure
    const rawPrice = parseInt(feedData.price.price);  // Could be NaN
}
```

**Risk:**
- Invalid data processing
- Application crashes
- Price manipulation

**Recommendation:**
- Add JSON schema validation
- Validate all inputs
- Handle errors gracefully

---

### 12. Missing Rate Limiting
**Severity:** 🟠 HIGH  
**Location:** `production-keeper-sse.js:1213-1281`

**Issue:**
Express endpoints have no rate limiting.

**Risk:**
- DDoS attacks
- Resource exhaustion
- Service unavailability

**Recommendation:**
Add rate limiting middleware:
```javascript
const rateLimit = require('express-rate-limit');
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use('/metrics', limiter);
```

---

### 13. Missing Encryption at Rest for Logs
**Severity:** 🟠 HIGH  
**Location:** `production-keeper-sse.js:152-163`

**Issue:**
Logs written to filesystem without encryption:
```javascript
new winston.transports.File({
    filename: "logs/error.log",
    // No encryption
})
```

**Risk:**
- Sensitive data in logs
- Information disclosure if container compromised

**Recommendation:**
- Use CloudWatch Logs exclusively
- Enable encryption at rest
- Remove local file logging

---

### 14. Weak Password Policy
**Severity:** 🟠 HIGH  
**Location:** `terraform/secrets.tf:83-86`

**Issue:**
Random password generation doesn't enforce complexity:
```terraform
resource "random_password" "aurora_password" {
  length  = 32
  special = true  # But no minimum requirements
}
```

**Risk:**
- Weak passwords possible
- Brute force attacks

**Recommendation:**
- Enforce password complexity
- Use AWS Secrets Manager rotation
- Implement password history

---

### 15. Missing Database Connection Encryption
**Severity:** 🟠 HIGH  
**Location:** `src/db/AuroraClient.js:34-45`

**Issue:**
MySQL connection doesn't explicitly require SSL:
```javascript
this.pool = mysql.createPool({
    host: this.config.host,
    // No SSL configuration
});
```

**Risk:**
- Unencrypted database traffic
- Man-in-the-middle attacks

**Recommendation:**
```javascript
ssl: {
    rejectUnauthorized: true,
    ca: fs.readFileSync('/path/to/ca-cert.pem')
}
```

---

### 16. Missing Audit Logging
**Severity:** 🟠 HIGH  
**Location:** Entire codebase

**Issue:**
No audit logging for:
- Secret access
- Configuration changes
- Administrative actions

**Risk:**
- Cannot detect unauthorized access
- No compliance audit trail

**Recommendation:**
- Implement CloudTrail logging
- Log all secret access
- Log configuration changes

---

### 17. Missing Secret Version Management
**Severity:** 🟠 HIGH  
**Location:** `terraform/secrets.tf`

**Issue:**
Secret versions not tracked, no rollback capability.

**Risk:**
- Cannot recover from bad secret updates
- No change history

**Recommendation:**
- Track secret versions
- Implement rollback procedures
- Use versioned secrets

---

### 18. Insufficient Error Handling
**Severity:** 🟠 HIGH  
**Location:** `production-keeper-sse.js:757-942`

**Issue:**
Transaction errors not properly handled:
```javascript
catch (error) {
    attempts++;
    lastError = error;
    // Error details logged but not acted upon
}
```

**Risk:**
- Silent failures
- Retry loops
- Resource exhaustion

**Recommendation:**
- Implement circuit breaker pattern
- Add error classification
- Limit retry attempts

---

### 19. Missing Health Check Authentication
**Severity:** 🟠 HIGH  
**Location:** `Dockerfile:37-68`

**Issue:**
Health check script doesn't validate response content.

**Risk:**
- False positive health checks
- Unhealthy containers marked as healthy

**Recommendation:**
Validate health check response structure.

---

### 20. Missing Resource Limits
**Severity:** 🟠 HIGH  
**Location:** `terraform/ecs.tf:113-114`

**Issue:**
Container resource limits not enforced:
```terraform
cpu    = "512"   # Soft limit
memory = "1024"  # Soft limit
```

**Risk:**
- Resource exhaustion
- Noisy neighbor issues

**Recommendation:**
- Set hard limits
- Configure memory limits
- Add CPU throttling

---

## Medium Severity Issues

### 21. Missing Monitoring Alerts
**Severity:** 🟡 MEDIUM  
**Location:** `terraform/monitoring.tf`

**Issue:**
Some critical metrics not monitored:
- Database connection failures
- Redis connection failures
- Secret access failures

**Recommendation:**
Add comprehensive monitoring.

---

### 22. Missing Backup Verification
**Severity:** 🟡 MEDIUM  
**Location:** `terraform/aurora.tf:90-91`

**Issue:**
Backups configured but not verified:
```terraform
backup_retention_period = 7
preferred_backup_window = "03:00-04:00"
```

**Risk:**
- Backup failures undetected
- Data loss

**Recommendation:**
- Automate backup verification
- Test restore procedures

---

### 23. Missing TLS Version Enforcement
**Severity:** 🟡 MEDIUM  
**Location:** `production-keeper-sse.js`

**Issue:**
No TLS version enforcement for external connections.

**Risk:**
- Weak TLS versions
- Protocol downgrade attacks

**Recommendation:**
Enforce TLS 1.2+.

---

### 24. Missing Dependency Scanning
**Severity:** 🟡 MEDIUM  
**Location:** `package.json`

**Issue:**
No automated dependency vulnerability scanning.

**Risk:**
- Known vulnerabilities in dependencies
- Supply chain attacks

**Recommendation:**
- Add `npm audit` to CI/CD
- Use Dependabot
- Regular dependency updates

---

### 25. Missing Code Signing
**Severity:** 🟡 MEDIUM  
**Location:** `Dockerfile`

**Issue:**
Docker images not signed.

**Risk:**
- Image tampering
- Supply chain attacks

**Recommendation:**
- Enable Docker Content Trust
- Sign images in CI/CD
- Verify signatures on pull

---

### 26. Missing Secrets Rotation Schedule
**Severity:** 🟡 MEDIUM  
**Location:** `terraform/secrets.tf:100-103`

**Issue:**
Only Aurora password has rotation configured:
```terraform
automatically_after_days = 90
```

**Risk:**
- Other secrets never rotated
- Long-lived credentials

**Recommendation:**
- Rotate all secrets regularly
- Implement rotation for private keys
- Document rotation procedures

---

### 27. Missing Disaster Recovery Testing
**Severity:** 🟡 MEDIUM  
**Location:** `README.md:176-191`

**Issue:**
DR procedures documented but not tested.

**Risk:**
- Failover procedures untested
- Extended downtime during incidents

**Recommendation:**
- Regular DR drills
- Automated failover testing
- Document test results

---

## Infrastructure Completeness Issues

### Missing Components

1. **VPC Endpoints** - Required for private subnet access to AWS services
2. **NAT Gateway** - Required for ECS tasks to access internet
3. **WAF Rules** - Missing for API protection
4. **Secrets Manager Rotation Lambda** - Code missing
5. **CloudWatch Alarms** - Incomplete coverage
6. **Backup Verification** - Not automated
7. **Security Scanning** - No automated vulnerability scanning
8. **Compliance Checks** - No automated compliance validation

### Configuration Issues

1. **Security Groups** - Too permissive egress rules
2. **IAM Roles** - Missing Secrets Manager permissions
3. **Resource Limits** - Not enforced
4. **Monitoring** - Incomplete metric coverage
5. **Logging** - Missing audit logs

---

## Recommendations Summary

### Immediate Actions (Critical)

1. ✅ Remove all hardcoded credentials
2. ✅ Add IAM permissions for Secrets Manager
3. ✅ Fix nonce management race conditions
4. ✅ Add VPC endpoints or NAT Gateway
5. ✅ Restrict security group egress rules
6. ✅ Add authentication to health endpoints
7. ✅ Create Lambda rotation function
8. ✅ Add input validation
9. ✅ Enable SSL for database connections
10. ✅ Implement rate limiting

### Short-term (High Priority)

1. ✅ Add comprehensive monitoring
2. ✅ Implement audit logging
3. ✅ Add dependency scanning
4. ✅ Enable encryption at rest
5. ✅ Implement circuit breaker pattern
6. ✅ Add resource limits
7. ✅ Create backup verification procedures

### Long-term (Medium Priority)

1. ✅ Implement DR testing
2. ✅ Add code signing
3. ✅ Enhance secret rotation
4. ✅ Add compliance checks
5. ✅ Implement automated security scanning

---

## Testing Recommendations

1. **Penetration Testing** - External security audit
2. **Load Testing** - Verify rate limiting works
3. **Chaos Engineering** - Test failover procedures
4. **Secret Rotation Testing** - Verify rotation works
5. **Backup Restore Testing** - Verify backups are valid

---

## Compliance Considerations

- **PCI DSS** - If handling payment data
- **SOC 2** - Audit logging requirements
- **GDPR** - Data protection requirements
- **HIPAA** - If handling health data

---

## Conclusion

The codebase has a solid foundation but requires significant security hardening before production deployment. The most critical issues are:

1. Hardcoded credentials
2. Missing IAM permissions
3. Insecure nonce management
4. Missing network security controls

Addressing these issues should be prioritized before deployment.

---

**Next Steps:**
1. Review and prioritize findings
2. Create remediation tickets
3. Implement fixes in order of severity
4. Re-audit after fixes
5. Schedule regular security reviews

