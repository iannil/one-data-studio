# Disaster Recovery Guide
# Sprint 23: Production Readiness

## Overview

This document describes the disaster recovery (DR) procedures for ONE-DATA-STUDIO.

## Recovery Time Objectives

| Component | RTO | RPO |
|-----------|-----|-----|
| Application Services | 15 minutes | 1 hour |
| Database (MySQL) | 30 minutes | 1 hour |
| Object Storage (MinIO) | 1 hour | 24 hours |
| Full System | 2 hours | 24 hours |

## Backup Strategy

### Automated Backups

| Component | Frequency | Retention | Location |
|-----------|-----------|-----------|----------|
| MySQL | Daily 2:00 AM | 30 days | MinIO |
| MinIO | Continuous | 90 days | Cross-region |
| Secrets | On change | 7 versions | Secrets Manager |
| Configuration | On change | 30 days | Git |

### Manual Backups

Before major changes:
```bash
# Create manual MySQL backup
kubectl create job --from=cronjob/mysql-backup manual-backup-$(date +%Y%m%d) -n one-data-infra

# Verify backup
./scripts/disaster-recovery.sh verify mysql_backup_YYYYMMDD_HHMMSS.sql.gz
```

## Recovery Procedures

### Scenario 1: Application Pod Failure

**Symptoms**: Service unavailable, pod in CrashLoopBackOff

**Recovery**:
```bash
# Check pod status
kubectl get pods -n one-data-system

# View logs
kubectl logs -n one-data-system deployment/bisheng-api --previous

# Restart deployment
kubectl rollout restart deployment/bisheng-api -n one-data-system

# Watch rollout
kubectl rollout status deployment/bisheng-api -n one-data-system
```

**Estimated Recovery Time**: 5 minutes

### Scenario 2: Database Corruption

**Symptoms**: SQL errors, data inconsistency

**Recovery**:
```bash
# List available backups
./scripts/disaster-recovery.sh list

# Verify backup integrity
./scripts/disaster-recovery.sh verify mysql_backup_YYYYMMDD_HHMMSS.sql.gz

# Restore from backup
./scripts/disaster-recovery.sh restore-mysql mysql_backup_YYYYMMDD_HHMMSS.sql.gz
```

**Estimated Recovery Time**: 30 minutes

### Scenario 3: Namespace Deletion

**Symptoms**: All pods and services missing

**Recovery**:
```bash
# Recreate namespace
kubectl create namespace one-data-system

# Sync ArgoCD applications
argocd app sync bisheng-api --force
argocd app sync alldata-api --force
argocd app sync web-frontend --force

# Restore secrets
kubectl apply -f k8s/infrastructure/secrets/

# Restore database
./scripts/disaster-recovery.sh restore-mysql
```

**Estimated Recovery Time**: 1 hour

### Scenario 4: Cluster Failure

**Symptoms**: kubectl cannot connect, all services down

**Recovery**:
1. Provision new cluster
2. Install ArgoCD
3. Connect to Git repository
4. Sync applications
5. Restore database from MinIO backup

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Create project
kubectl apply -f argocd/projects/one-data-studio.yaml

# Create applications
kubectl apply -f argocd/applications/

# Restore database
./scripts/disaster-recovery.sh restore-all
```

**Estimated Recovery Time**: 2 hours

### Scenario 5: Secret Compromise

**Symptoms**: Unauthorized access detected, secrets potentially exposed

**Recovery**:
```bash
# Immediate: Rotate all secrets
./scripts/rotate-secrets.sh all --force

# Invalidate existing tokens
kubectl delete pods -n one-data-system --all

# Review audit logs
kubectl logs -n one-data-system -l app=bisheng-api | grep -i "login\|auth"

# Update external services
# - Regenerate OpenAI API key
# - Regenerate Keycloak client secret
```

**Estimated Recovery Time**: 30 minutes

## Verification Checklist

After recovery, verify:

- [ ] All pods running and healthy
- [ ] Database connectivity
- [ ] Redis connectivity
- [ ] MinIO connectivity
- [ ] Authentication working
- [ ] API endpoints responding
- [ ] Frontend accessible
- [ ] Audit logging active

## Testing

### Monthly DR Test

1. Create test backup
2. Restore to staging environment
3. Verify data integrity
4. Document results

### Quarterly Full DR Test

1. Simulate cluster failure
2. Execute full recovery
3. Measure actual RTO/RPO
4. Update procedures if needed

## Contacts

| Role | Name | Contact |
|------|------|---------|
| Primary On-Call | - | oncall@example.com |
| Database Admin | - | dba@example.com |
| Platform Team | - | platform@example.com |

## Runbook Links

- [Kubernetes Troubleshooting](https://kubernetes.io/docs/tasks/debug/)
- [ArgoCD Operations](https://argo-cd.readthedocs.io/en/stable/operator-manual/)
- [MySQL Recovery](https://dev.mysql.com/doc/refman/8.0/en/backup-and-recovery.html)
