# 故障排查指南

本文档提供 ONE-DATA-STUDIO 平台常见问题的诊断和解决方案。

## 目录

1. [服务启动问题](#服务启动问题)
2. [性能问题](#性能问题)
3. [数据一致性问题](#数据一致性问题)
4. [集成问题](#集成问题)
5. [存储问题](#存储问题)
6. [网络问题](#网络问题)

---

## 服务启动问题

### Alldata API 启动失败

#### 症状
- Pod 状态为 `CrashLoopBackOff`
- 日志显示数据库连接错误

#### 诊断步骤

```bash
# 查看 Pod 状态
kubectl get pods -n one-data-alldata

# 查看 Pod 日志
kubectl logs -n one-data-alldata deployment/alldata-api --tail=100

# 查看 Pod 事件
kubectl describe pod -n one-data-alldata <pod-name>
```

#### 常见原因与解决

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Can't connect to MySQL server` | MySQL 未就绪 | 检查 MySQL Pod 状态，等待就绪 |
| `Access denied for user` | 数据库凭证错误 | 检查 Secret 配置 |
| `Table doesn't exist` | 数据库未初始化 | 运行数据库迁移脚本 |
| `Port 8080 already in use` | 端口冲突 | 检查 Service 配置 |

#### 数据库初始化

```bash
# 执行数据库迁移
kubectl exec -n one-data-alldata deployment/alldata-api -- \
  python -m alembic upgrade head

# 或使用初始化 Job
kubectl apply -f deploy/kubernetes/applications/alldata-api/db-init-job.yaml
```

### Bisheng API 启动失败

#### 症状
- LLM 调用超时
- 向量检索失败

#### 诊断步骤

```bash
# 检查依赖服务
kubectl get pods -n one-data-infra | grep -E "milvus|redis"

# 测试 Milvus 连接
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- \
  nc -zv milvus-proxy.one-data-infra.svc.cluster.local 19530

# 检查环境变量
kubectl exec -n one-data-bisheng deployment/bisheng-api -- env | grep -E "MILVUS|REDIS"
```

#### 常见原因与解决

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Milvus connection timeout` | Milvus Proxy 未就绪 | 检查 Milvus StatefulSet |
| `Collection not found` | 向量集合未创建 | 运行集合初始化脚本 |
| `Redis connection refused` | Redis 未启动 | 检查 Redis Pod |

### vLLM Serving 启动失败

#### 症状
- GPU 内存不足错误
- 模型加载失败

#### 诊断步骤

```bash
# 检查 GPU 可用性
kubectl describe node | grep -A 5 "nvidia.com/gpu"

# 查看 vLLM 日志
kubectl logs -n one-data-cube statefulset/vllm-serving --tail=100

# 检查 GPU 内存使用
kubectl exec -n one-data-cube statefulset/vllm-serving -- nvidia-smi
```

#### 常见原因与解决

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Out of GPU memory` | 模型太大或 GPU 不足 | 减小模型或增加 GPU 资源 |
| `Model not found` | 模型路径错误 | 检查 PVC 挂载和模型下载 |
| `CUDA not available` | GPU 驱动问题 | 检查节点 CUDA 安装 |

---

## 性能问题

### API 响应缓慢

#### 诊断步骤

```bash
# 查看资源使用情况
kubectl top pods -n one-data-alldata

# 查看数据库连接池
kubectl exec -n one-data-alldata deployment/alldata-api -- \
  curl http://localhost:8080/metrics | grep db_connections

# 查看 Prometheus 指标
kubectl port-forward -n one-data-system svc/prometheus 9090:9090
# 访问 http://localhost:9090 查询: http_request_duration_seconds
```

#### 性能优化检查清单

- [ ] 数据库连接池大小是否足够 (推荐: 20-50)
- [ ] Redis 缓存是否启用
- [ ] 查询是否使用了索引
- [ ] 是否有 N+1 查询问题
- [ ] 日志级别是否过高

#### 数据库慢查询分析

```sql
-- 启用慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;

-- 查看慢查询
SELECT * FROM mysql.slow_log ORDER BY query_time DESC LIMIT 20;

-- 分析查询执行计划
EXPLAIN SELECT * FROM large_table WHERE condition = 'value';
```

### Milvus 查询缓慢

#### 诊断步骤

```bash
# 查看 Milvus 性能指标
kubectl exec -n one-data-infra statefulset/milvus-querynode -- \
  curl http://localhost:9091/metrics

# 检查索引状态
from pymilvus import utility
collections = utility.list_collections()
for c in collections:
    coll = Collection(c)
    print(f"{c}: {coll.num_entities} entities, index: {coll.index()}")
```

#### 优化措施

1. **索引优化**
   ```python
   # 创建 HNSW 索引以提高查询速度
   index_params = {
       "index_type": "HNSW",
       "metric_type": "L2",
       "params": {"M": 16, "efConstruction": 256}
   }
   collection.create_index("embedding", index_params)
   ```

2. **查询参数调优**
   ```python
   # 增加 nprobe 提高召回率
   search_params = {"metric_type": "L2", "params": {"nprobe": 16}}
   ```

3. **负载均衡**
   ```yaml
   # 增加 QueryNode 副本
   replicas: 3
   ```

---

## 数据一致性问题

### 元数据同步失败

#### 症状
- OpenMetadata 与本地数据库不一致
- 血缘信息缺失

#### 诊断步骤

```bash
# 检查同步服务状态
kubectl logs -n one-data-alldata deployment/alldata-api -c metadata-sync

# 查看同步延迟
kubectl exec -n one-data-alldata deployment/alldata-api -- \
  curl http://localhost:8080/api/v1/metadata/sync-status
```

#### 解决方案

```bash
# 手动触发同步
kubectl exec -n one-data-alldata deployment/alldata-api -- \
  curl -X POST http://localhost:8080/api/v1/metadata/sync

# 检查 OpenMetadata 连接
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- \
  nc -zv openmetadata.one-data-infra.svc.cluster.local 8585
```

### 血缘事件丢失

#### 症状
- 血缘图不完整
- 事件队列积压

#### 诊断步骤

```bash
# 检查事件队列大小
kubectl exec -n one-data-alldata deployment/alldata-api -- \
  curl http://localhost:8080/metrics | grep openlineage_queue

# 检查持久化速率
kubectl exec -n one-data-alldata deployment/alldata-api -- \
  curl http://localhost:8080/metrics | grep openlineage_persisted
```

#### 解决方案

```python
# 增加批量处理大小
# services/openlineage_event_service.py
service = OpenLineageEventService(
    batch_size=200,  # 从 100 增加到 200
    flush_interval=3  # 从 5 减少到 3
)
```

---

## 集成问题

### Kettle 作业执行失败

#### 症状
- 作业状态一直为 `RUNNING`
- 作业执行超时

#### 诊断步骤

```bash
# 查看 Kettle Worker 日志
kubectl logs -n one-data-alldata deployment/kettle-worker

# 检查作业队列
kubectl exec -n one-data-alldata deployment/alldata-api -- \
  curl http://localhost:8080/api/v1/kettle/jobs

# 检查 MinIO 连接
kubectl exec -n one-data-alldata deployment/kettle-worker -- \
  curl http://minio.one-data-infra.svc.cluster.local:9000/minio/health/live
```

#### 解决方案

1. **增加 Worker 副本**
   ```bash
   kubectl scale deployment/kettle-worker -n one-data-alldata --replicas=3
   ```

2. **调整资源限制**
   ```yaml
   resources:
     requests:
       memory: "2Gi"
       cpu: "1000m"
     limits:
       memory: "4Gi"
       cpu: "2000m"
   ```

### Text-to-SQL 生成错误

#### 症状
- 生成的 SQL 语法错误
- 查询结果不正确

#### 诊断步骤

```bash
# 查看错误日志
kubectl logs -n one-data-bisheng deployment/bisheng-api | grep -i "text2sql"

# 检查元数据上下文
kubectl exec -n one-data-bisheng deployment/bisheng-api -- \
  curl http://localhost:8081/api/v1/metadata/schema/test_db
```

#### 解决方案

1. **丰富 Prompt 上下文**
   ```python
   # 添加更多表结构信息
   schema_info = get_full_schema(database, table)
   prompt = f"""
   表结构:
   {schema_info}

   常见查询示例:
   ...

   用户问题: {question}
   """
   ```

2. **启用 SQL 验证**
   ```python
   def validate_sql(sql):
       try:
           parse_sql(sql)  # 使用 SQL 解析器
           return True
       except Exception as e:
           logger.error(f"Invalid SQL: {e}")
           return False
   ```

---

## 存储问题

### MinIO 存储空间不足

#### 症状
- 文件上传失败
- PVC 已满

#### 诊断步骤

```bash
# 查看 PVC 使用情况
kubectl get pvc -n one-data-infra

# 查看存储使用
kubectl exec -n one-data-infra statefulset/minio -- \
  df -h /data

# 查看 MinIO 配额
kubectl exec -n one-data-infra statefulset/minio -- \
  mc admin info local
```

#### 解决方案

1. **扩展 PVC**
   ```bash
   # 如果 StorageClass 支持扩展
   kubectl patch pvc minio-data -n one-data-infra -p '{"spec":{"resources":{"requests":{"storage":"500Gi"}}}}'
   ```

2. **清理旧数据**
   ```bash
   # 删除 30 天前的备份
   kubectl exec -n one-data-infra statefulset/minio -- \
     mc rm --recursive --older-than 30d local/backups/
   ```

### Milvus 数据损坏

#### 症状
- 查询返回空结果
- Segment 加载失败

#### 诊断步骤

```bash
# 查看 Milvus 日志
kubectl logs -n one-data-infra statefulset/milvus-datacoord

# 检查集合状态
kubectl exec -n one-data-infra statefulset/milvus-querynode -- \
  curl http://localhost:9091/metrics | grep segment
```

#### 解决方案

```bash
# 重建集合索引
kubectl exec -n one-data-infra deployment/alldata-api -- python <<'EOF'
from pymilvus import connections, Collection
connections.connect("default", host="milvus-proxy", port="19530")
collection = Collection("your_collection")
collection.drop_index()
collection.create_index("embedding", index_params)
collection.load()
EOF

# 或恢复备份
kubectl apply -f deploy/kubernetes/infrastructure/databases/milvus-restore.yaml
```

---

## 网络问题

### 服务间通信失败

#### 症状
- `Connection refused` 错误
- `DNS resolution failed` 错误

#### 诊断步骤

```bash
# 测试 DNS 解析
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- \
  nslookup alldata-api.one-data-alldata.svc.cluster.local

# 测试端口连通性
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- \
  nc -zv alldata-api.one-data-alldata.svc.cluster.local 8080

# 检查网络策略
kubectl get networkpolicies --all-namespaces
```

#### 解决方案

1. **检查网络策略**
   ```bash
   # 查看是否允许通信
   kubectl get networkpolicy -n one-data-alldata -o yaml
   ```

2. **添加允许规则**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-egress
   spec:
     podSelector: {}
     policyTypes:
     - Egress
     egress:
     - to:
       - namespaceSelector:
           matchLabels:
             name: one-data-infra
   ```

### Ingress 配置错误

#### 症状
- 502 Bad Gateway
- 404 Not Found

#### 诊断步骤

```bash
# 查看 Ingress 日志
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller

# 查看 Ingress 资源
kubectl get ingress -A

# 测试 Ingress
curl -H "Host: alldata.example.com" http://<ingress-ip>/api/v1/health
```

#### 解决方案

1. **检查 Service 端口**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   spec:
     rules:
     - host: alldata.example.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: alldata-api
               port:
                 number: 8080  # 确保端口正确
   ```

2. **检查 TLS 证书**
   ```bash
   kubectl get certificate -A
   kubectl describe certificate alldata-cert -n one-data-alldata
   ```

---

## 应急命令速查

```bash
# 快速重启所有服务
kubectl rollout restart deployment -n one-data-alldata
kubectl rollout restart deployment -n one-data-bisheng
kubectl rollout restart statefulset -n one-data-infra

# 查看所有 Pod 状态
kubectl get pods -A | grep -E "one-data|NAME"

# 查看 PVC 使用
kubectl get pvc -A -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,CAPACITY:.spec.resources.requests.storage

# 端口转发到本地调试
kubectl port-forward -n one-data-alldata svc/alldata-api 8080:8080
kubectl port-forward -n one-data-system svc/grafana 3000:3000

# 进入容器调试
kubectl exec -it -n one-data-alldata deployment/alldata-api -- /bin/sh

# 查看资源使用
kubectl top nodes
kubectl top pods -A

# 查看事件
kubectl get events -A --sort-by='.lastTimestamp'
```

---

## 联系支持

如果问题无法通过上述方法解决，请收集以下信息后联系技术支持：

```bash
# 收集诊断信息
kubectl cluster-info dump > cluster-dump.txt
kubectl logs -n one-data-alldata deployment/alldata-api --tail=500 > alldata-api.log
kubectl logs -n one-data-bisheng deployment/bisheng-api --tail=500 > bisheng-api.log
kubectl get pods -A -o yaml > pods.yaml
kubectl get svc -A -o yaml > services.yaml
```
