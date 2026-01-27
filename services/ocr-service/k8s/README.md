# OCR服务Kubernetes部署指南

本文档介绍如何在Kubernetes集群上部署OCR服务。

## 前置条件

- Kubernetes集群 1.20+
- kubectl配置正确
- Helm 3.x（可选）
- Ingress Controller（如nginx-ingress）
- cert-manager（用于TLS证书）

## 快速开始

### 1. 创建命名空间和配置

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
```

### 2. 部署服务

```bash
# RBAC
kubectl apply -f k8s/rbac.yaml

# 部署
kubectl apply -f k8s/deployment.yaml

# 服务
kubectl apply -f k8s/service.yaml

# 网络策略
kubectl apply -f k8s/networkpolicy.yaml

# Pod中断预算
kubectl apply -f k8s/pdb.yaml
```

### 3. 配置Ingress

```bash
kubectl apply -f k8s/ingress.yaml
```

### 4. 验证部署

```bash
# 检查Pod状态
kubectl get pods -n ocr-service

# 检查服务
kubectl get svc -n ocr-service

# 检查日志
kubectl logs -f deployment/ocr-service -n ocr-service

# 端口转发测试
kubectl port-forward svc/ocr-service 8007:8007 -n ocr-service
```

## 配置说明

### ConfigMap配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| OCR_ENGINE | paddleocr | OCR引擎选择 |
| MAX_FILE_SIZE | 52428800 | 最大文件大小(字节) |
| LOG_LEVEL | INFO | 日志级别 |
| WORKER_COUNT | 4 | 工作进程数 |
| MAX_CONCURRENT_TASKS | 10 | 最大并发任务数 |
| CACHE_TTL | 3600 | 缓存过期时间(秒) |

### Secret配置

在部署前，请修改 `k8s/secret.yaml` 中的敏感信息：

- `MYSQL_PASSWORD`: MySQL密码
- `DATABASE_URL`: 数据库连接字符串
- `REDIS_PASSWORD`: Redis密码
- `REDIS_URL`: Redis连接字符串
- `OPENAI_API_KEY`: OpenAI API密钥（可选）
- `SECRET_KEY`: 应用密钥

## 扩缩容配置

### 手动扩缩容

```bash
# 扩容到5个副本
kubectl scale deployment/ocr-service --replicas=5 -n ocr-service

# 缩容到2个副本
kubectl scale deployment/ocr-service --replicas=2 -n ocr-service
```

### 自动扩缩容

HPA已配置，默认规则：
- 最小副本数: 3
- 最大副本数: 10
- CPU目标利用率: 70%
- 内存目标利用率: 80%

修改HPA配置：

```bash
kubectl edit hpa ocr-service-hpa -n ocr-service
```

## 滚动更新

### 更新镜像

```bash
# 修改镜像
kubectl set image deployment/ocr-service \
  ocr-service=onedata-ocr-service:v2.0 \
  -n ocr-service

# 查看更新状态
kubectl rollout status deployment/ocr-service -n ocr-service
```

### 回滚

```bash
# 查看历史版本
kubectl rollout history deployment/ocr-service -n ocr-service

# 回滚到上一版本
kubectl rollout undo deployment/ocr-service -n ocr-service

# 回滚到指定版本
kubectl rollout undo deployment/ocr-service --to-revision=2 -n ocr-service
```

## 监控配置

### Prometheus服务发现

```bash
kubectl apply -f k8s/prometheus.yaml
```

### ServiceMonitor配置（需要Prometheus Operator）

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ocr-service
  namespace: ocr-service
spec:
  selector:
    matchLabels:
      app: ocr-service
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

## 故障排查

### Pod无法启动

```bash
# 查看Pod详情
kubectl describe pod <pod-name> -n ocr-service

# 查看日志
kubectl logs <pod-name> -n ocr-service

# 查看之前容器的日志
kubectl logs <pod-name> --previous -n ocr-service
```

### 服务无法访问

```bash
# 检查Service
kubectl get svc ocr-service -n ocr-service

# 检查Endpoints
kubectl get endpoints ocr-service -n ocr-service

# 测试服务连接
kubectl run test --image=busybox --rm -it --restart=Never -n ocr-service -- \
  wget -O- http://ocr-service:8007/health
```

### Ingress无法访问

```bash
# 检查Ingress
kubectl get ingress -n ocr-service

# 检查Ingress Controller日志
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

## 生产环境检查清单

- [ ] 修改Secret中的默认密码
- [ ] 配置TLS证书
- [ ] 设置资源限制（Requests/Limits）
- [ ] 配置HPA自动扩缩容
- [ ] 配置PodDisruptionBudget
- [ ] 配置NetworkPolicy
- [ ] 配置日志收集（EFK/ELK）
- [ ] 配置监控告警（Prometheus/Grafana）
- [ ] 配置备份策略
- [ ] 进行负载测试
- [ ] 制定回滚计划

## Helm部署（可选）

使用Helm可以更方便地管理部署：

```bash
# 创建values
cat > values.yaml <<EOF
replicaCount: 3

image:
  repository: onedata-ocr-service
  tag: "latest"
  pullPolicy: IfNotPresent

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: ocr.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: ocr-service-tls
      hosts:
        - ocr.example.com

# 挂载PVC
persistence:
  enabled: true
  existingClaim: ocr-models-pvc
EOF

# 部署
helm install ocr-service ./charts/ocr-service -f values.yaml -n ocr-service

# 升级
helm upgrade ocr-service ./charts/ocr-service -f values.yaml -n ocr-service

# 卸载
helm uninstall ocr-service -n ocr-service
```
