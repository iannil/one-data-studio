# K8s External Secrets Configuration
# Sprint 21: Security Hardening - Secrets Management

This directory contains Kubernetes External Secrets configurations for managing
sensitive credentials securely in production environments.

## Overview

External Secrets Operator (ESO) allows synchronizing secrets from external
secret management systems (like AWS Secrets Manager, HashiCorp Vault, etc.)
into Kubernetes Secrets.

## Prerequisites

1. Install External Secrets Operator:
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace
```

2. Configure your secret store (see `secret-store.yaml`)

## Files

- `secret-store.yaml` - SecretStore configuration for connecting to secret backend
- `external-secrets.yaml` - ExternalSecret definitions for application secrets
- `cluster-secret-store.yaml` - ClusterSecretStore for cluster-wide access

## Usage

1. Create the secret store:
```bash
kubectl apply -f secret-store.yaml
```

2. Create the external secrets:
```bash
kubectl apply -f external-secrets.yaml
```

3. Verify secrets are synced:
```bash
kubectl get externalsecrets -n one-data-system
kubectl get secrets -n one-data-system
```

## Secret Rotation

Secrets are automatically synced every 1 hour (configurable in refreshInterval).
To force a refresh:
```bash
kubectl annotate externalsecret mysql-secrets \
  force-sync=$(date +%s) --overwrite -n one-data-system
```
