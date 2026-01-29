# ONE-DATA-STUDIO 部署配置

本目录包含所有部署相关的配置文件和脚本。

## 目录结构

```
deploy/
├── local/                    # 本地开发环境
│   ├── docker-compose.yml    # 主服务
│   ├── docker-compose.monitoring.yml  # 监控栈
│   └── config/               # 本地配置文件
│
├── kubernetes/               # Kubernetes 资源
│   ├── base/                 # 基础配置（命名空间、存储类）
│   ├── applications/         # 应用部署
│   │   ├── data-api/
│   │   ├── agent-api/
│   │   ├── openai-proxy/
│   │   ├── web-frontend/
│   │   └── vllm-serving/
│   ├── infrastructure/       # 基础设施
│   │   ├── databases/        # MySQL, Redis, Milvus, MinIO
│   │   ├── monitoring/       # Prometheus, Grafana, AlertManager, Loki, Jaeger
│   │   ├── networking/       # Istio, NetworkPolicy
│   │   ├── security/         # cert-manager, secrets, Keycloak
│   │   └── proxies/          # ProxySQL, Nginx
│   ├── jobs/                 # Jobs 和 CronJobs
│   └── overlays/             # Kustomize 环境覆盖
│       ├── dev/
│       ├── staging/
│       └── production/
│
├── argocd/                   # ArgoCD GitOps 配置
│   ├── applications/         # ArgoCD Application 定义
│   └── projects/             # ArgoCD Project 定义
│
├── dockerfiles/              # 所有 Dockerfile
│   ├── data-api/
│   ├── agent-api/
│   └── openai-proxy/
│
├── helm/                     # Helm Charts
│   └── charts/
│       └── one-data/         # 主 Chart
│
├── scripts/                  # 部署脚本
│   ├── deploy.sh
│   ├── deploy-all.sh
│   ├── rollback.sh
│   └── blue-green-deploy.sh
│
└── openapi/                  # API 规范文档
    ├── data-api.yaml
    └── agent-api.yaml
```

## 快速开始

### 本地开发

```bash
# 启动所有服务
cd deploy/local
docker-compose up -d

# 包含监控栈
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### Kubernetes 部署

```bash
# 使用 Kustomize 部署到 dev 环境
kubectl apply -k deploy/kubernetes/overlays/dev

# 部署到 staging
kubectl apply -k deploy/kubernetes/overlays/staging

# 部署到 production
kubectl apply -k deploy/kubernetes/overlays/production
```

### ArgoCD GitOps

```bash
# 应用 ArgoCD 配置
kubectl apply -f deploy/argocd/projects/
kubectl apply -f deploy/argocd/applications/
```

### Helm 部署

```bash
# 安装
helm install one-data deploy/helm/charts/one-data \
  --namespace one-data-system \
  --create-namespace \
  -f deploy/helm/charts/one-data/values.yaml

# 升级
helm upgrade one-data deploy/helm/charts/one-data \
  --namespace one-data-system

# 卸载
helm uninstall one-data --namespace one-data-system
```

## 环境变量

参考 `.env.example` 文件配置环境变量。
