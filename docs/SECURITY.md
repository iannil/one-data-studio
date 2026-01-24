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
# Authentication
JWT_SECRET_KEY=<min 32 chars, random>
CSRF_SECRET_KEY=<min 32 chars, random>

# Cache Security
CACHE_SIGNING_KEY=<min 32 chars, random>

# Environment
ENVIRONMENT=production

# Database
MYSQL_PASSWORD=<strong password>
REDIS_PASSWORD=<strong password>

# Storage
MINIO_ACCESS_KEY=<access key>
MINIO_SECRET_KEY=<min 40 chars>

# External APIs
OPENAI_API_KEY=<api key>
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
