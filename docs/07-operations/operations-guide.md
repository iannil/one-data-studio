# ONE-DATA-STUDIO 运维手册

## 目录

1. [系统概述](#系统概述)
2. [部署架构](#部署架构)
3. [日常运维](#日常运维)
4. [监控告警](#监控告警)
5. [备份恢复](#备份恢复)
6. [故障排查](#故障排查)
7. [扩缩容](#扩缩容)
8. [安全加固](#安全加固)

---

## 系统概述

### 服务组成

| 服务 | 端口 | 说明 |
|------|------|------|
| Web Frontend | 3000 | React 前端应用 |
| Data API | 8080 | 数据治理 API |
| Agent API | 8081 | LLM 应用编排 API |
| OpenAI Proxy | 8000 | LLM 服务代理 |

### 依赖服务

| 服务 | 端口 | 说明 |
|------|------|------|
| MySQL | 3306 | 主数据库 |
| Redis | 6379 | 缓存和会话 |
| MinIO | 9000/9001 | 对象存储 |
| Milvus | 19530 | 向量数据库 |
| Keycloak | 8080 | 身份认证 |

---

## 部署架构

### Kubernetes 部署

```
┌─────────────────────────────────────────────────────────────┐
│                     Ingress Controller                       │
├─────────────────────────────────────────────────────────────┤
│                     Istio Service Mesh                       │
├─────────────────┬───────────────────┬───────────────────────┤
│   Web Frontend  │   Data API     │   Agent API         │
│   (Deployment)  │   (Deployment)    │   (Deployment)        │
│   replicas: 2   │   replicas: 2     │   replicas: 2         │
├─────────────────┴───────────────────┴───────────────────────┤
│                     Shared Services                          │
│   MySQL │ Redis │ MinIO │ Milvus │ Keycloak                 │
└─────────────────────────────────────────────────────────────┘
```

### 资源配置建议

#### 生产环境最低配置

| 组件 | CPU | 内存 | 存储 |
|------|-----|------|------|
| Data API | 500m-2000m | 512Mi-2Gi | - |
| Agent API | 1000m-4000m | 1Gi-4Gi | - |
| Web Frontend | 200m-1000m | 256Mi-1Gi | - |
| MySQL | 2000m | 4Gi | 100Gi SSD |
| Redis | 500m | 1Gi | 10Gi |
| Milvus | 4000m | 8Gi | 200Gi SSD |
| MinIO | 1000m | 2Gi | 500Gi |

---

## 日常运维

### 健康检查

```bash
# 检查所有服务健康状态
curl http://data-api:8080/api/v1/health | jq
curl http://agent-api:8081/api/v1/health | jq

# Kubernetes 环境
kubectl get pods -n one-data-system
kubectl get pods -n one-data-system -o wide | grep -v Running
```

### 日志查看

```bash
# Docker Compose 环境
docker-compose logs -f data-api
docker-compose logs -f agent-api

# Kubernetes 环境
kubectl logs -f deployment/data-api -n one-data-system
kubectl logs -f deployment/agent-api -n one-data-system

# 使用 Loki 查询日志
# Grafana -> Explore -> Loki
# 查询示例：{service="agent-api"} |= "error"
```

### 服务重启

```bash
# Docker Compose 环境
docker-compose restart data-api
docker-compose restart agent-api

# Kubernetes 环境
kubectl rollout restart deployment/data-api -n one-data-system
kubectl rollout restart deployment/agent-api -n one-data-system

# 等待重启完成
kubectl rollout status deployment/data-api -n one-data-system
```

### 配置更新

```bash
# 更新 ConfigMap
kubectl apply -f k8s/apps/data-api/configmap.yaml

# 触发 Pod 重启以应用新配置
kubectl rollout restart deployment/data-api -n one-data-system
```

---

## 监控告警

### Prometheus 指标

#### 核心 HTTP 指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| http_request_duration_seconds | 请求延迟 | P95 > 500ms |
| http_requests_total | 请求总数 | - |
| http_requests_in_progress | 当前进行中的请求 | - |
| http_response_size_bytes | 响应大小分布 | - |

#### 数据库指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| db_connections_total | 数据库连接总数 | - |
| db_connections_in_use | 当前连接使用数 | > 80% |
| db_connection_duration_seconds | 连接延迟 | P95 > 100ms |

#### AI 服务指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| ai_requests_total | AI 请求总数（按服务/模型/状态） | - |
| ai_request_duration_seconds | AI 请求延迟 | P95 > 10s |
| ai_request_tokens_total | Token 使用统计 | - |

#### 业务指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| business_operations_total | 业务操作计数 | - |
| business_operation_duration_seconds | 业务操作延迟 | - |
| cache_hits_total / cache_misses_total | 缓存命中率 | < 50% |
| task_queue_size | 任务队列长度 | - |

### Grafana 仪表板

预配置的仪表板：

1. **API 性能仪表板** (`deploy/monitoring/grafana/dashboards/api-performance.json`)
   - 请求延迟分布
   - 错误率趋势
   - 吞吐量

2. **系统资源仪表板** (`deploy/monitoring/grafana/dashboards/system-resources.json`)
   - CPU/内存使用
   - 网络 I/O
   - 磁盘使用

3. **业务指标仪表板** (`deploy/monitoring/grafana/dashboards/business-metrics.json`)
   - 活跃用户数
   - 工作流执行数
   - RAG 查询数

4. **AI 服务仪表板** (`deploy/monitoring/grafana/dashboards/ai-services.json`)
   - vLLM Chat/Embedding 延迟
   - Token 使用统计
   - AI 服务可用性

### 告警规则

#### 服务健康告警

```yaml
# 服务不可用告警
- alert: ServiceDown
  expr: up{job=~"data-api|agent-api"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "服务 {{ $labels.job }} 不可用"

# 高延迟告警
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "服务 {{ $labels.job }} P95 延迟超过 500ms"

# 高错误率告警
- alert: HighErrorRate
  expr: rate(http_request_errors_total[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "服务 {{ $labels.job }} 错误率超过 5%"
```

#### RAG 服务告警

```yaml
# RAG 检索延迟高
- alert: RAGRetrievalLatencyHigh
  expr: histogram_quantile(0.95, rate(rag_retrieval_duration_seconds_bucket[5m])) > 3
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "RAG 检索延迟超过 3 秒"

# 向量搜索分数低
- alert: VectorSearchLowScore
  expr: avg(vector_search_score{collection!="test"}) < 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "向量搜索分数低于 0.5"
```

#### 数据流水线告警

```yaml
# ETL 任务失败率高
- alert: ETLJobFailureRateHigh
  expr: sum(rate(etl_jobs_total{status="failed"}[10m])) / sum(rate(etl_jobs_total[10m])) > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "ETL 任务失败率超过 10%"

# 数据质量分数低
- alert: DataQualityScoreLow
  expr: data_quality_score < 0.7
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "数据质量分数低于 0.7"
```

#### ML 训练告警

```yaml
# 训练任务失败
- alert: TrainingJobFailed
  expr: kube_job_status_failed{job_name=~".*training.*"} == 1
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "训练任务 {{ $labels.job_name }} 失败"

# GPU 利用率低
- alert: LowGPUUtilization
  expr: nvidia_gpu_utilization < 30
  for: 15m
  labels:
    severity: info
  annotations:
    summary: "GPU 利用率低于 30%"
```

---

## 备份恢复

### MySQL 备份

```bash
# 手动备份
mysqldump -h mysql -u root -p one_data_studio > backup_$(date +%Y%m%d).sql

# 定时备份（添加到 crontab）
0 2 * * * /scripts/mysql-backup.sh

# 恢复备份
mysql -h mysql -u root -p one_data_studio < backup_20240101.sql
```

### MinIO 备份

```bash
# 使用 mc 工具备份
mc alias set myminio http://minio:9000 minio minio123
mc mirror myminio/datasets /backup/minio/datasets

# 恢复
mc mirror /backup/minio/datasets myminio/datasets
```

### Milvus 备份

```bash
# 使用 Milvus 备份工具
milvus-backup create -n backup_$(date +%Y%m%d)

# 列出备份
milvus-backup list

# 恢复备份
milvus-backup restore -n backup_20240101
```

### 完整备份脚本

```bash
#!/bin/bash
# /scripts/full-backup.sh

BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

echo "Starting full backup..."

# MySQL
echo "Backing up MySQL..."
mysqldump -h mysql -u root -p$MYSQL_ROOT_PASSWORD one_data_studio > $BACKUP_DIR/mysql.sql

# MinIO
echo "Backing up MinIO..."
mc mirror myminio/datasets $BACKUP_DIR/minio/

# Milvus
echo "Backing up Milvus..."
milvus-backup create -n backup_$(date +%Y%m%d) -d $BACKUP_DIR/milvus/

# 压缩
tar -czvf /backup/backup_$(date +%Y%m%d).tar.gz $BACKUP_DIR

echo "Backup completed: /backup/backup_$(date +%Y%m%d).tar.gz"
```

---

## 故障排查

### 常见问题

#### 1. API 响应慢

检查步骤：
```bash
# 1. 检查 Pod 资源使用
kubectl top pods -n one-data-system

# 2. 检查数据库连接
kubectl exec -it deployment/agent-api -n one-data-system -- python -c "
from models import SessionLocal
db = SessionLocal()
db.execute('SELECT 1')
print('Database OK')
"

# 3. 检查 Redis 连接
kubectl exec -it deployment/agent-api -n one-data-system -- redis-cli -h redis ping

# 4. 检查慢查询日志
kubectl logs deployment/agent-api -n one-data-system | grep -i slow
```

#### 2. 向量检索失败

检查步骤：
```bash
# 1. 检查 Milvus 状态
kubectl get pods -l app=milvus -n one-data-system

# 2. 检查集合状态
kubectl exec -it deployment/agent-api -n one-data-system -- python -c "
from services import VectorStore
vs = VectorStore()
print(vs.list_collections())
"

# 3. 检查 Milvus 日志
kubectl logs deployment/milvus -n one-data-system | tail -100
```

#### 3. 认证失败

检查步骤：
```bash
# 1. 检查 Keycloak 状态
kubectl get pods -l app=keycloak -n one-data-system

# 2. 验证 JWT 配置
kubectl get secret jwt-secret -n one-data-system -o yaml

# 3. 测试认证
curl -v -H "Authorization: Bearer $TOKEN" http://agent-api:8081/api/v1/auth/me
```

### 紧急恢复流程

1. **服务完全不可用**
   ```bash
   # 检查 Pod 状态
   kubectl get pods -n one-data-system

   # 重启有问题的 Pod
   kubectl delete pod <pod-name> -n one-data-system

   # 如果多个 Pod 有问题，重启 Deployment
   kubectl rollout restart deployment --all -n one-data-system
   ```

2. **数据库连接失败**
   ```bash
   # 检查 MySQL Pod
   kubectl get pods -l app=mysql -n one-data-system

   # 检查 PVC
   kubectl get pvc -n one-data-system

   # 查看 MySQL 日志
   kubectl logs -l app=mysql -n one-data-system
   ```

---

## 扩缩容

### 手动扩容

```bash
# 扩展 API 副本数
kubectl scale deployment/data-api --replicas=3 -n one-data-system
kubectl scale deployment/agent-api --replicas=3 -n one-data-system
```

### 自动扩容 (HPA)

已配置的 HPA 策略：

```yaml
# k8s/hpa/agent-api-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

查看 HPA 状态：
```bash
kubectl get hpa -n one-data-system
```

---

## 安全加固

### 密钥管理

1. **使用 Kubernetes Secrets**
   ```bash
   # 创建密钥
   kubectl create secret generic db-credentials \
     --from-literal=username=root \
     --from-literal=password=<password> \
     -n one-data-system
   ```

2. **JWT 密钥轮换**
   ```bash
   # 生成新密钥
   NEW_KEY=$(openssl rand -base64 32)

   # 更新 Secret
   kubectl patch secret jwt-secret -n one-data-system \
     -p='{"data":{"JWT_SECRET_KEY":"'$(echo -n $NEW_KEY | base64)'"}}'

   # 重启服务应用新密钥
   kubectl rollout restart deployment/data-api -n one-data-system
   kubectl rollout restart deployment/agent-api -n one-data-system
   ```

### 网络策略

```yaml
# 限制 Pod 间通信
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
  namespace: one-data-system
spec:
  podSelector:
    matchLabels:
      app: agent-api
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: web
    - podSelector:
        matchLabels:
          app: data-api
```

### 审计日志

审计日志位置：
- Kubernetes: `/var/log/kubernetes/audit/`
- 应用审计: `services/shared/audit.py` 实现

查看审计日志：
```bash
# 查询审计日志（通过 Loki）
{job="agent-api"} |= "AUDIT"
```

---

## 附录

### 常用命令速查

```bash
# 查看所有资源
kubectl get all -n one-data-system

# 查看 Pod 详情
kubectl describe pod <pod-name> -n one-data-system

# 进入 Pod 调试
kubectl exec -it <pod-name> -n one-data-system -- /bin/bash

# 端口转发
kubectl port-forward svc/agent-api 8081:8081 -n one-data-system

# 查看事件
kubectl get events -n one-data-system --sort-by='.lastTimestamp'

# 查看资源使用
kubectl top nodes
kubectl top pods -n one-data-system
```

### 联系方式

- 技术支持：support@one-data-studio.com
- 紧急热线：+86-xxx-xxxx-xxxx
- 文档地址：https://docs.one-data-studio.com
