# ONE-DATA-STUDIO Kubernetes Deployment

This directory contains Kubernetes manifests for deploying ONE-DATA-STUDIO to a Kubernetes cluster.

## Directory Structure

```
k8s/
├── base/                    # Base configuration (shared across environments)
│   ├── namespace.yaml       # Namespace definition
│   ├── configmap.yaml       # Non-sensitive configuration
│   ├── secrets.yaml         # Secrets template (DO NOT commit real secrets!)
│   ├── rbac.yaml            # Service account and RBAC
│   ├── agent-api.yaml     # LLMOps API deployment
│   ├── data-api.yaml     # DataOps API deployment
│   ├── openai-proxy.yaml    # OpenAI-compatible proxy
│   ├── model-api.yaml        # MLOps API deployment
│   ├── web-frontend.yaml    # Web frontend deployment
│   ├── ingress.yaml         # Ingress configuration
│   ├── hpa.yaml             # Horizontal Pod Autoscaler
│   ├── pdb.yaml             # Pod Disruption Budget
│   ├── network-policy.yaml  # Network policies
│   └── kustomization.yaml   # Kustomize configuration
└── overlays/
    ├── production/          # Production-specific overrides
    │   └── kustomization.yaml
    └── staging/             # Staging-specific overrides
        └── kustomization.yaml
```

## Prerequisites

1. **Kubernetes Cluster** (v1.25+)
2. **kubectl** configured with cluster access
3. **Kustomize** (included in kubectl v1.14+)
4. **Ingress Controller** (nginx-ingress recommended)
5. **External Dependencies**:
   - MySQL 8.0+ (or compatible managed service)
   - Redis 7+ (or compatible managed service)
   - MinIO or S3-compatible storage
   - Milvus vector database
   - Keycloak for authentication

## Deployment

### 1. Create Secrets

**IMPORTANT**: Never commit real secrets to version control!

Create secrets using kubectl:

```bash
kubectl create namespace one-data-studio

kubectl create secret generic one-data-secrets \
  --from-literal=MYSQL_PASSWORD='<secure-password>' \
  --from-literal=MYSQL_ROOT_PASSWORD='<secure-root-password>' \
  --from-literal=REDIS_PASSWORD='<secure-redis-password>' \
  --from-literal=MINIO_ROOT_USER='<minio-user>' \
  --from-literal=MINIO_ROOT_PASSWORD='<secure-minio-password>' \
  --from-literal=MINIO_ACCESS_KEY='<minio-access-key>' \
  --from-literal=MINIO_SECRET_KEY='<minio-secret-key>' \
  --from-literal=JWT_SECRET_KEY='<secure-jwt-secret>' \
  --from-literal=KEYCLOAK_CLIENT_SECRET='<keycloak-secret>' \
  --from-literal=OPENAI_API_KEY='<openai-key-optional>' \
  -n one-data-studio
```

Or use external secrets management (recommended):
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager

### 2. Configure Environment

Update `k8s/base/configmap.yaml` with your environment-specific values:
- Database hostnames
- Service URLs
- Keycloak configuration

### 3. Deploy

**Staging**:
```bash
kubectl apply -k k8s/overlays/staging/
```

**Production**:
```bash
kubectl apply -k k8s/overlays/production/
```

### 4. Verify Deployment

```bash
# Check pod status
kubectl get pods -n one-data-studio

# Check services
kubectl get svc -n one-data-studio

# Check ingress
kubectl get ingress -n one-data-studio

# View logs
kubectl logs -f deployment/agent-api -n one-data-studio
```

## Configuration

### Image Tags

Update image tags in overlay kustomization files:

```yaml
images:
  - name: one-data-studio/agent-api
    newTag: v1.0.0
```

### Resource Limits

Modify resource limits in overlay patches or directly in base manifests based on your cluster capacity.

### Scaling

The HPA configurations in `hpa.yaml` automatically scale pods based on CPU utilization. Adjust thresholds as needed:

```yaml
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          averageUtilization: 70
```

### TLS/HTTPS

Enable TLS in production by uncommenting the TLS section in `ingress.yaml` and configuring cert-manager:

```yaml
spec:
  tls:
    - hosts:
        - one-data.example.com
      secretName: one-data-tls
```

## Troubleshooting

### Pods not starting

1. Check pod events: `kubectl describe pod <pod-name> -n one-data-studio`
2. Check logs: `kubectl logs <pod-name> -n one-data-studio`
3. Verify secrets exist: `kubectl get secrets -n one-data-studio`

### Database connection issues

1. Verify database is accessible from cluster
2. Check configmap values are correct
3. Verify secret passwords are set

### Ingress not working

1. Verify ingress controller is installed
2. Check ingress status: `kubectl describe ingress -n one-data-studio`
3. Verify DNS is configured correctly

## Security Notes

1. **Secrets**: Use external secrets management in production
2. **Network Policies**: Review and adjust based on your security requirements
3. **RBAC**: The default service account has minimal permissions
4. **Pod Security**: All pods run as non-root with restricted capabilities
5. **TLS**: Always enable TLS in production environments
