# ArgoCD Configuration for ONE-DATA-STUDIO
# Sprint 23: Production Readiness - GitOps

This directory contains ArgoCD configurations for GitOps-based deployment.

## Structure

```
argocd/
├── applications/           # ArgoCD Application definitions
│   ├── alldata-api.yaml   # Alldata API application
│   ├── bisheng-api.yaml   # Bisheng API application
│   ├── web-frontend.yaml  # Web frontend application
│   └── monitoring.yaml    # Monitoring stack application
├── projects/              # ArgoCD Project definitions
│   └── one-data-studio.yaml
└── README.md
```

## Prerequisites

1. ArgoCD installed in the cluster:
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

2. ArgoCD CLI installed locally:
```bash
brew install argocd  # macOS
# or download from https://github.com/argoproj/argo-cd/releases
```

## Setup

### 1. Create the Project

```bash
kubectl apply -f argocd/projects/one-data-studio.yaml
```

### 2. Create Applications

```bash
kubectl apply -f argocd/applications/
```

### 3. Access ArgoCD UI

```bash
# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Port forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
```

## Operations

### Sync an Application

```bash
argocd app sync bisheng-api
```

### View Application Status

```bash
argocd app get bisheng-api
```

### Rollback

```bash
argocd app rollback bisheng-api <revision>
```

### View Sync History

```bash
argocd app history bisheng-api
```

## Sync Strategies

| Application | Auto-Sync | Self-Heal | Prune |
|-------------|-----------|-----------|-------|
| bisheng-api | ✅ | ✅ | ✅ |
| alldata-api | ✅ | ✅ | ✅ |
| web-frontend | ✅ | ✅ | ✅ |
| monitoring | ❌ | ✅ | ❌ |

## Notifications

Notifications are configured to send alerts to Slack on:
- Sync succeeded
- Sync failed
- Health degraded

Configure the Slack webhook in ArgoCD notifications secret.

## Security

- Applications are scoped to the `one-data-studio` project
- RBAC policies restrict who can sync/modify applications
- Sensitive values are stored in External Secrets
