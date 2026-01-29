# ONE-DATA-STUDIO Security Best Practices
# Sprint 23-24: Production Readiness

## Overview

This document outlines security best practices for deploying and operating ONE-DATA-STUDIO in production environments.

## Recent Security Enhancements (Sprint 24)

### Cache Security
- **Pickle RCE Prevention**: Cache module now uses JSON serialization with HMAC signature verification instead of pickle
- **Production Requirement**: `CACHE_SIGNING_KEY` environment variable is required in production
- **Tamper Detection**: Cached data is signed and verified to prevent cache poisoning attacks

### Code Execution Sandbox
- **AST-based Validation**: Complete AST analysis to detect dangerous patterns
- **Forbidden Module Blocking**: os, subprocess, socket, pickle, and other dangerous modules blocked
- **Forbidden Function Blocking**: eval, exec, open, __import__, and other dangerous functions blocked
- **Dunder Attribute Blocking**: __class__, __subclasses__, __globals__, etc. blocked to prevent sandbox escapes
- **Timeout Enforcement**: All code execution has configurable timeout limits

### SQL Injection Protection
- **Pattern Detection**: Dangerous SQL patterns (DROP, DELETE, UNION, --, etc.) are blocked
- **Parameterized Queries**: All database operations use parameterized queries
- **Production Validation**: Mock data is rejected in production environment

### SSRF Protection
- **Private IP Blocking**: 10.x.x.x, 172.16.x.x, 192.168.x.x blocked
- **Localhost Blocking**: localhost, 127.0.0.1 blocked
- **Cloud Metadata Blocking**: 169.254.169.254 (AWS/GCP/Azure metadata endpoints) blocked
- **Kubernetes Internal Blocking**: kubernetes.default.svc blocked
- **Protocol Validation**: Only http:// and https:// allowed

### Production Environment Enforcement
- **Mock Data Rejection**: mock_data=True is not allowed in production
- **SSL Verification**: SSL verification cannot be disabled in production
- **Credential Validation**: Helm templates validate that all required credentials are set

## Authentication & Authorization

### Token Security

1. **HttpOnly Cookies**: Access tokens are stored in HttpOnly cookies to prevent XSS attacks.
   - Frontend cannot read tokens directly
   - Tokens are automatically sent with requests
   - SameSite=Lax prevents CSRF for most cases

2. **CSRF Protection**: All state-changing operations require CSRF tokens.
   - Double Submit Cookie pattern
   - Token bound to session
   - 1-hour expiry

3. **Token Refresh**: Automatic token refresh before expiry.
   - 5-minute refresh threshold
   - Seamless user experience
   - Secure refresh token handling

### Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| admin | Full access to all resources |
| data_engineer | Dataset and metadata management |
| ai_developer | Workflow and model operations |
| data_analyst | Read-only access |
| user | Basic chat and view access |

## Network Security

### HTTPS Enforcement

All production traffic must use HTTPS:
- TLS 1.2+ required
- HSTS enabled with 1-year max-age
- Certificate managed by cert-manager

### Security Headers

All responses include:
- `Strict-Transport-Security`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy`
- `Referrer-Policy`

### CORS Policy

- Explicit origin whitelist (no wildcards in production)
- Credentials only with specific origins
- Preflight caching (10 minutes)

#### CORS Configuration Details

**Environment Variables:**
```bash
# 允许的源列表（逗号分隔）
CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com

# 允许携带凭据（cookies）
CORS_ALLOW_CREDENTIALS=true

# 允许的 HTTP 方法
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS

# 允许的请求头
CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-Requested-With,X-CSRF-Token

# 暴露的响应头
CORS_EXPOSED_HEADERS=X-Total-Count,X-Page-Count

# 预检请求缓存时间（秒）
CORS_MAX_AGE=600
```

**Flask 应用配置示例:**
```python
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# 生产环境 CORS 配置
CORS(app,
    origins=os.getenv('CORS_ALLOWED_ORIGINS', '').split(','),
    allow_credentials=True,
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization', 'X-CSRF-Token'],
    max_age=600
)
```

### Rate Limiting

#### Rate Limit 配置

**环境变量:**
```bash
# 启用速率限制
RATE_LIMIT_ENABLED=true

# 默认限制
RATE_LIMIT_DEFAULT=100/minute

# 突发请求允许量
RATE_LIMIT_BURST=200

# Redis 存储（生产环境推荐）
RATE_LIMIT_STORAGE_URL=redis://redis:6379/1
```

**装饰器使用示例:**
```python
from services.shared.rate_limit import rate_limit

# 使用默认限制
@app.route('/api/v1/users')
@rate_limit()
def get_users():
    pass

# 自定义限制
@app.route('/api/v1/chat')
@rate_limit(limit='10/minute', burst=20)
def chat():
    pass

# 基于用户的限制
@app.route('/api/v1/expensive-operation')
@rate_limit(limit='5/hour', key_func=lambda: g.user_id)
def expensive_operation():
    pass
```

**响应头:**
- `X-RateLimit-Limit`: 限制总量
- `X-RateLimit-Remaining`: 剩余请求数
- `X-RateLimit-Reset`: 重置时间（Unix 时间戳）

**超限响应:**
```json
{
  "code": 42900,
  "message": "Too many requests",
  "error": "rate_limit_exceeded",
  "retry_after": 60
}
```

## Secret Management

### Environment Variables

**Never** commit secrets to version control.

Required secrets:
- `JWT_SECRET_KEY`: Minimum 32 characters, randomly generated
- `CSRF_SECRET_KEY`: Minimum 32 characters
- `MYSQL_PASSWORD`: Strong password (24+ characters)
- `REDIS_PASSWORD`: Strong password
- `MINIO_SECRET_KEY`: Minimum 40 characters
- `OPENAI_API_KEY`: API key from OpenAI

### Secret Rotation

Regular rotation schedule:
- JWT keys: Monthly
- Database passwords: Quarterly
- API keys: As needed

Use the rotation script:
```bash
./scripts/rotate-secrets.sh jwt --dry-run
./scripts/rotate-secrets.sh database
```

### Kubernetes Secrets

Use External Secrets Operator:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: jwt-secrets
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  # ...
```

## Input Validation

### API Input Validation

All user input is validated:
- SQL injection prevention (parameterized queries)
- XSS prevention (output encoding)
- Command injection prevention (no shell commands with user input)
- File upload validation (type, size, content)

### Content Size Limits

- Request body: 100MB max
- File uploads: 50MB per file
- SQL query results: 10,000 rows max

## Audit Logging

### Logged Events

- Authentication (login, logout, failures)
- Data access (CRUD operations)
- Configuration changes
- Permission changes
- System errors

### Log Retention

- Security logs: 90 days minimum
- Audit logs: 1 year minimum
- Access logs: 30 days

### Log Format

```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "action": "login",
  "user_id": "user-123",
  "ip_address": "192.168.1.1",
  "status": "success",
  "metadata": {}
}
```

## Infrastructure Security

### Kubernetes Security

1. **Network Policies**: Restrict pod-to-pod communication
2. **Pod Security**: Non-root containers, read-only filesystem
3. **RBAC**: Minimal permissions for service accounts
4. **Secrets**: Never mount unnecessary secrets

### Database Security

1. **Connection Encryption**: TLS for all database connections
2. **User Permissions**: Minimal required permissions
3. **Backup Encryption**: Encrypted backups in MinIO
4. **Network Isolation**: Database not exposed externally

### MinIO Security

1. **Bucket Policies**: Restrict access to authorized services
2. **Encryption**: Server-side encryption enabled
3. **Access Logging**: All access logged

## Vulnerability Management

### Dependency Scanning

- **Dependabot**: Weekly dependency updates
- **pip-audit**: Python vulnerability scanning
- **npm audit**: JavaScript vulnerability scanning

### Container Scanning

- **Trivy**: Container image scanning in CI
- Base image updates: Weekly
- Critical vulnerabilities: Fix within 24 hours

### Security Testing

- **Bandit**: Python SAST
- **ESLint Security**: JavaScript SAST
- **Gitleaks**: Secret scanning
- **Checkov**: IaC scanning

## Incident Response

### Security Incident Classification

| Severity | Response Time | Examples |
|----------|---------------|----------|
| Critical | 1 hour | Data breach, authentication bypass |
| High | 4 hours | Privilege escalation, exposed secrets |
| Medium | 24 hours | Minor vulnerability, configuration issue |
| Low | 72 hours | Documentation issue, best practice deviation |

### Response Procedure

1. **Detect**: Automated alerts or manual discovery
2. **Contain**: Isolate affected systems
3. **Investigate**: Determine scope and impact
4. **Remediate**: Fix the vulnerability
5. **Recover**: Restore services
6. **Review**: Post-incident analysis

### Contact

Security issues should be reported to: security@example.com

## Compliance

### Data Protection

- Personal data encrypted at rest
- Access logging for all PII
- Data retention policies enforced
- User consent management

### Audit Requirements

- Monthly security reviews
- Quarterly penetration testing
- Annual compliance audit

## Quick Reference

### Security Checklist

Before deployment:
- [ ] All secrets in External Secrets / Vault
- [ ] HTTPS enabled and enforced
- [ ] Security headers configured
- [ ] CSRF protection enabled
- [ ] CORS whitelist configured
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Backup encryption enabled
- [ ] Network policies applied
- [ ] Container images scanned
- [ ] CACHE_SIGNING_KEY set for production
- [ ] ENVIRONMENT=production set
- [ ] Mock data disabled
- [ ] SSL verification enabled

### Required Environment Variables (Production)

```bash
# ==================== Authentication ====================
JWT_SECRET_KEY=<min 32 chars, random>
CSRF_SECRET_KEY=<min 32 chars, random>
JWT_KEY_ROTATION_PERIOD=86400       # 密钥轮换周期（秒）

# ==================== Cache Security ====================
CACHE_SIGNING_KEY=<min 32 chars, random>

# ==================== Environment ====================
ENVIRONMENT=production

# ==================== SSL/TLS ====================
VERIFY_SSL=true                     # 生产环境必须为 true
SECURITY_FORCE_HTTPS=true           # 强制 HTTPS 重定向

# ==================== HSTS Headers ====================
SECURITY_HSTS_ENABLED=true
SECURITY_HSTS_MAX_AGE=31536000      # 1 年
SECURITY_HSTS_INCLUDE_SUBDOMAINS=true
SECURITY_HSTS_PRELOAD=true

# ==================== CORS ====================
CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
CORS_ALLOW_CREDENTIALS=true

# ==================== Rate Limiting ====================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_BURST=200

# ==================== Database ====================
MYSQL_PASSWORD=<strong password>
REDIS_PASSWORD=<strong password>

# ==================== Storage ====================
MINIO_ACCESS_KEY=<access key>
MINIO_SECRET_KEY=<min 40 chars>
MINIO_SECURE=true                   # 使用 HTTPS

# ==================== External APIs ====================
OPENAI_API_KEY=<api key>

# ==================== Keycloak ====================
KEYCLOAK_URL=https://auth.example.com
KEYCLOAK_REALM=one-data
KEYCLOAK_CLIENT_ID=one-data-studio
KEYCLOAK_CLIENT_SECRET=<secret>
```

### Kubernetes Secret Placeholder Annotations

生产环境部署前，必须替换所有带有以下注解的占位符 Secret：

```yaml
annotations:
  one-data.io/placeholder: "true"
```

验证命令：
```bash
# 检查占位符 Secret
kubectl get secrets -A -o json | jq '.items[] | select(.metadata.annotations["one-data.io/placeholder"] == "true") | .metadata.name'

# 如果有输出，说明有未替换的占位符 Secret
```

### Useful Commands

```bash
# Check security headers
curl -I https://api.example.com | grep -E "Strict-Transport|X-Frame|X-Content-Type"

# Verify CSRF
curl -X POST /api/v1/test -H "X-CSRF-Token: invalid" # Should return 403

# Check cookie attributes
curl -v https://api.example.com/auth/login 2>&1 | grep -i "set-cookie"

# Run security scan
bandit -r services/ -f json
npm audit --audit-level=high

# Verify TLS
openssl s_client -connect api.example.com:443 -servername api.example.com
```

## API Version Migration Guide

### Overview

ONE-DATA-STUDIO API supports multiple versions to ensure backward compatibility during upgrades.

### Version Lifecycle

| Status | Description | Support Duration |
|--------|-------------|------------------|
| Current | 推荐使用的稳定版本 | 持续支持 |
| Beta | 测试版本，可能有变化 | 不保证向后兼容 |
| Deprecated | 已弃用，计划下线 | 90 天弃用期 |
| Sunset | 即将下线 | 30 天警告期 |
| Retired | 已下线 | 不再支持 |

### Version Detection

API 版本可以通过以下方式指定（优先级从高到低）：

1. **URL 路径**: `/api/v1/users`
2. **请求头**: `X-API-Version: v2`
3. **查询参数**: `?api_version=v1`
4. **默认版本**: `v1`

### Migration Steps

#### From v1 to v2

1. **检查弃用警告**
   ```bash
   # 检查响应头中的弃用警告
   curl -I https://api.example.com/api/v1/endpoint | grep -i deprecat
   ```

2. **更新 API 调用**
   ```python
   # v1 (deprecated)
   response = requests.get('/api/v1/old-endpoint')

   # v2 (recommended)
   response = requests.get('/api/v2/new-endpoint')
   ```

3. **处理响应格式变化**
   - 查看 `/api/versions/v2` 获取破坏性变更列表
   - 更新数据解析逻辑

4. **测试迁移**
   ```bash
   # 使用版本头测试新版本
   curl -H "X-API-Version: v2" https://api.example.com/api/endpoint
   ```

### Deprecation Notices

弃用的 API 将返回以下响应头：

```
X-API-Deprecated: true
X-API-Sunset: 2025-06-01T00:00:00Z
X-API-Alternative: /api/v2/new-endpoint
Deprecation: true
Warning: 299 - "API version v1 is deprecated. Will be retired in 90 days."
```

### Version Information Endpoint

```bash
# 列出所有支持的版本
curl https://api.example.com/api/versions

# 获取特定版本信息
curl https://api.example.com/api/versions/v1
```

## Multi-Tenant Configuration Guide

### Overview

ONE-DATA-STUDIO 支持多租户部署，每个租户有独立的数据隔离和资源配额。

### Tenant Identification

租户可以通过以下方式识别（优先级从高到低）：

1. **JWT Claims**: `tenant_id` claim
2. **请求头**: `X-Tenant-ID`
3. **子域名**: `tenant1.api.example.com`

### Configuration

**环境变量:**
```bash
# 启用多租户
MULTI_TENANT_ENABLED=true

# 租户识别方式
TENANT_IDENTIFICATION_METHOD=jwt  # jwt, header, subdomain

# 默认租户（可选）
DEFAULT_TENANT_ID=default

# 租户数据隔离
TENANT_DATA_ISOLATION=strict  # strict, shared
```

### Resource Quotas

每个租户可以配置资源配额：

```python
from services.shared.multitenancy import TenantQuota

# 获取租户配额
quota = get_tenant_quota('tenant-123')

# 检查配额
if not quota.check_quota('workflows', current_count):
    raise QuotaExceededError('workflows', current_count, quota.get_quota('workflows'))

# 获取使用摘要
summary = quota.get_usage_summary()
# {
#   'workflows': {'quota': 100, 'used': 50, 'remaining': 50, 'percentage': 50.0},
#   'documents': {'quota': 1000, 'used': 200, 'remaining': 800, 'percentage': 20.0}
# }
```

**默认配额:**

| 资源 | 默认限制 | 描述 |
|------|----------|------|
| max_workflows | 100 | 最大工作流数量 |
| max_documents | 1000 | 最大文档数量 |
| max_conversations | 500 | 最大对话数量 |
| max_storage_gb | 10 | 最大存储空间 (GB) |
| max_api_calls_per_day | 10000 | 每日 API 调用限制 |

### Database Schema

多租户数据通过 `tenant_id` 列隔离：

```python
from services.shared.multitenancy import TenantMixin

class Workflow(TenantMixin, Base):
    __tablename__ = 'workflows'

    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    # tenant_id 由 TenantMixin 自动添加
```

### Query Filtering

使用 `TenantQuery` 自动过滤租户数据：

```python
from services.shared.multitenancy import TenantQuery, tenant_context

# 方式 1: 使用上下文管理器
with tenant_context('tenant-123'):
    workflows = Workflow.query.all()  # 自动过滤 tenant_id

# 方式 2: 显式过滤
workflows = TenantQuery.filter_by_tenant(
    Workflow.query,
    Workflow,
    tenant_id='tenant-123'
).all()
```

### Tenant-Specific Collections

向量数据库集合按租户隔离：

```python
from services.shared.multitenancy import get_tenant_collection_name

# 获取租户特定的集合名称
collection_name = get_tenant_collection_name('documents', tenant_id='tenant-123')
# 返回: 'documents_tenant123'
```

### Best Practices

1. **始终使用租户上下文**
   ```python
   with tenant_context(tenant_id):
       # 所有数据库操作自动使用租户过滤
       perform_operations()
   ```

2. **配额检查装饰器**
   ```python
   @check_quota('workflows')
   def create_workflow():
       # 自动检查配额
       pass
   ```

3. **审计租户操作**
   - 所有跨租户操作都应记录审计日志
   - 管理员操作需要特殊权限

4. **数据迁移**
   - 租户数据迁移需要离线执行
   - 使用 `tenant_id` 字段批量更新

