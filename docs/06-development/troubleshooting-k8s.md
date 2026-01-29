# 故障排查指南

> **适用场景**: Kubernetes 部署环境（Kind、Minikube、云 K8s）
>
> 如果您使用 Docker Compose 部署，请参考 [troubleshooting-docker.md](../06-operations/troubleshooting-docker.md)

本文档提供 ONE-DATA-STUDIO 平台常见问题的诊断和解决方案。

---

## 目录

- [基础设施问题](#基础设施问题)
- [服务启动问题](#服务启动问题)
- [网络连接问题](#网络连接问题)
- [性能问题](#性能问题)
- [数据问题](#数据问题)

---

## 基础设施问题

### K8s 集群问题

#### Pod 一直 Pending

**症状**：
```bash
kubectl get pods -A
# NAME              READY   STATUS    RESTARTS   AGE
# vllm-serving-xxx  0/1     Pending   0          5m
```

**可能原因**：

1. **资源不足**
```bash
kubectl describe nodes
# 查看资源使用情况

kubectl top nodes
# 实时资源监控
```

**解决方案**：
- 增加 K8s 节点资源
- 减少 Pod 资源请求（编辑 deployment，修改 resources.requests）

2. **没有可用的节点**
```bash
kubectl get nodes -o wide
# 检查节点状态

kubectl describe pod <pod-name> -n <namespace>
# 查看 Events 部分，寻找调度失败原因
```

3. **污点/容忍度配置问题**
```bash
kubectl describe nodes | grep Taints
# 检查节点污点配置
```

---

#### Pod 无法拉取镜像

**症状**：
```
Failed to pull image "xxx": rpc error: code = Unknown desc = Error response from daemon: pull access denied
```

**解决方案**：

1. **创建镜像拉取密钥**
```bash
kubectl create secret docker-registry regcred \
  --docker-server=harbor.example.com \
  --docker-username=<username> \
  --docker-password=<password> \
  -n <namespace>

# 在 Deployment 中引用
spec:
  template:
    spec:
      imagePullSecrets:
      - name: regcred
```

2. **使用国内镜像源**
```bash
# 编辑 /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}

# 重启 Docker
sudo systemctl restart docker
```

---

#### StorageClass 不可用

**症状**：
```
persistentvolumecontroller: could not find provisioner for class fast-ssd
```

**解决方案**：

1. **检查 StorageClass**
```bash
kubectl get storageclass
```

2. **安装存储驱动**
```bash
# Longhorn
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.5.1/deploy/longhorn.yaml

# Local Path Provisioner（适用于测试）
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml
```

---

## 服务启动问题

### vLLM 服务问题

#### vLLM Pod 一直 CrashLoopBackOff

**症状**：
```bash
kubectl logs -n one-data-model vllm-serving-xxx
# ERROR: CUDA out of memory
```

**解决方案**：

1. **GPU 内存不足**
```yaml
# 减少 max_model_len 或使用更小的模型
args:
  - --model
  - Qwen/Qwen-0.5B-Chat  # 使用小模型
  - --max-model-len
  - "1024"  # 减少上下文长度
```

2. **无 GPU 环境**
```yaml
# 移除 GPU 资源请求
resources:
  requests:
    memory: "4Gi"
    cpu: "1000m"
    # nvidia.com/gpu: "1"  # 删除此行
  limits:
    memory: "8Gi"
    cpu: "4000m"
    # nvidia.com/gpu: "1"  # 删除此行
```

3. **模型下载失败**
```bash
# 预先下载模型到本地
docker pull vllm/vllm-openai:latest

# 或使用模型缓存
kubectl apply -f k8s/applications/model-cache-pvc.yaml
```

---

#### vLLM 启动时间过长

**症状**：
```bash
kubectl get pods -n one-data-model -w
# vLLM Pod 一直 ContainerCreating
```

**原因**：模型下载需要时间

**解决方案**：
```bash
# 增加启动容忍时间
livenessProbe:
  initialDelaySeconds: 180  # 增加到 3 分钟

# 查看下载进度
kubectl logs -n one-data-model vllm-serving-xxx -f
```

---

### 数据库问题

#### MySQL 连接失败

**症状**：
```
Can't connect to MySQL server on 'mysql.one-data-infra.svc.cluster.local:3306'
```

**解决方案**：

1. **检查 MySQL 状态**
```bash
kubectl get pods -n one-data-infra | grep mysql
kubectl logs -n one-data-infra mysql-0
```

2. **测试连接**
```bash
kubectl run -it --rm mysql-client --image=mysql:8.0 --restart=Never -- \
  mysql -h mysql.one-data-infra.svc.cluster.local -u one_data -p
```

3. **检查密码**
```bash
kubectl get secret mysql-credentials -n one-data-infra -o jsonpath='{.data}' | jq
```

---

#### Redis 连接失败

**症状**：
```
NOAUTH Authentication required
```

**解决方案**：
```python
# 确保连接时提供密码
redis_client = redis.Redis(
    host='redis.one-data-infra.svc.cluster.local',
    port=6379,
    password='RedisPassword123!'  # 必须提供密码
)
```

---

## 网络连接问题

### 服务间无法访问

#### DNS 解析失败

**症状**：
```
getaddrinfo ENOTFOUND data-api.one-data-data.svc.cluster.local
```

**解决方案**：

1. **检查 Service 是否存在**
```bash
kubectl get svc -A | grep data-api
```

2. **检查 DNS Pod**
```bash
kubectl get pods -n kube-system | grep kube-dns

# 测试 DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup data-api.one-data-data.svc.cluster.local
```

3. **检查 CoreDNS 配置**
```bash
kubectl get configmap coredns -n kube-system -o yaml
```

---

#### 跨 Namespace 无法访问

**症状**：Agent 无法调用 Data API

**解决方案**：

1. **使用完整的服务名**
```python
# 正确
ALDATA_API_URL = "http://data-api.one-data-data.svc.cluster.local:8080"

# 错误
ALDATA_API_URL = "http://data-api:8080"  # 仅在同一 Namespace 内可用
```

2. **检查 NetworkPolicy**
```bash
kubectl get networkpolicy -A
# 确保没有阻止跨 Namespace 访问的策略
```

---

### Ingress 无法访问

#### 502 Bad Gateway

**症状**：
```
curl http://alldata.example.com/api/v1/health
# 502 Bad Gateway
```

**解决方案**：

1. **检查 Service 选择器**
```bash
kubectl get endpoints -n one-data-data
# 确保 Endpoints 有对应的 Pod IP
```

2. **检查 Ingress 配置**
```bash
kubectl get ingress -A
kubectl describe ingress alldata-ingress -n one-data-data
```

3. **检查 Ingress Controller**
```bash
kubectl get pods -n ingress-nginx
```

---

## 性能问题

### API 响应慢

#### 诊断步骤

1. **检查 Pod 资源使用**
```bash
kubectl top pods -A
```

2. **检查服务日志**
```bash
kubectl logs -n one-data-data deployment/data-api --tail=100
```

3. **检查网络延迟**
```bash
# 在 Pod 内运行
kubectl exec -it data-api-xxx -n one-data-data -- \
  curl -w "@-" -o /dev/null -s "http://mysql.one-data-infra.svc.cluster.local:3306"
```

#### 优化方案

1. **增加资源配额**
```yaml
resources:
  requests:
    memory: "1Gi"    # 增加内存
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

2. **启用 HPA 自动伸缩**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: data-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

### 模型推理慢

#### 诊断步骤

1. **检查 GPU 利用率**
```bash
kubectl exec -it vllm-serving-xxx -n one-data-model -- nvidia-smi
```

2. **检查请求队列**
```bash
# vLLM 内置了 /metrics 端点
curl http://vllm-serving:8000/metrics | grep vllm
```

#### 优化方案

1. **增加 tensor_parallel_size**（多 GPU）
```yaml
args:
  - --tensor-parallel-size
  - "2"  # 使用 2 个 GPU
```

2. **启用量化**
```yaml
args:
  - --quantization
  - awq  # 或 gptq
```

---

## 数据问题

### 数据集无法访问

#### MinIO 连接失败

**症状**：
```
MinIO API responded with 403 Forbidden
```

**解决方案**：

1. **检查凭据**
```bash
kubectl get secret minio-credentials -n one-data-infra -o yaml
```

2. **检查 Bucket 策略**
```bash
# 进入 MinIO Console
kubectl port-forward -n one-data-infra svc/minio 9001:9001
# 访问 http://localhost:9001
# 设置 Bucket 策略为 readonly 或 public
```

3. **更新应用配置**
```yaml
env:
- name: MINIO_ENDPOINT
  value: "minio.one-data-infra.svc.cluster.local:9000"  # 确保正确
- name: MINIO_USE_SSL
  value: "false"  # 内部集群通常不使用 SSL
```

---

## 日志收集

### 收集诊断信息

```bash
#!/bin/bash
# diagnose.sh - 收集所有诊断信息

echo "=== Pod 状态 ==="
kubectl get pods -A | grep one-data

echo ""
echo "=== Service 状态 ==="
kubectl get svc -A | grep one-data

echo ""
echo "=== 最近事件 ==="
kubectl get events -A --sort-by='.lastTimestamp' | tail -20

echo ""
echo "=== Data API 日志 ==="
kubectl logs -n one-data-data deployment/data-api --tail=50

echo ""
echo "=== vLLM 日志 ==="
kubectl logs -n one-data-model deployment/vllm-serving --tail=50

echo ""
echo "=== Agent API 日志 ==="
kubectl logs -n one-data-agent deployment/agent-api --tail=50
```

---

## 常用命令速查

| 场景 | 命令 |
|------|------|
| 查看 Pod 状态 | `kubectl get pods -A \| grep one-data` |
| 查看 Pod 详情 | `kubectl describe pod <name> -n <ns>` |
| 查看日志 | `kubectl logs -n <ns> deployment/<name> -f` |
| 端口转发 | `kubectl port-forward -n <ns> svc/<name> 8080:8080` |
| 执行命令 | `kubectl exec -it <pod> -n <ns> -- /bin/sh` |
| 删除 Pod | `kubectl delete pod <name> -n <ns>` |
| 重启 Deployment | `kubectl rollout restart deployment/<name> -n <ns>` |
| 查看资源使用 | `kubectl top pods -A` |
| 查看事件 | `kubectl get events -n <ns> --sort-by='.lastTimestamp'` |

---

## 获取帮助

### 收集信息

在报告问题时，请收集以下信息：

1. **K8s 版本**
```bash
kubectl version
```

2. **Pod 状态**
```bash
kubectl get pods -A -o wide > pod-status.txt
```

3. **相关日志**
```bash
kubectl logs -n <namespace> <pod-name> > logs.txt
```

4. **事件**
```bash
kubectl get events -n <namespace> > events.txt
```

5. **配置**
```bash
kubectl get -n <namespace> deployment/<name> -o yaml > deployment.yaml
```

---

## 更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2024-01-23 | v1.0 | 初始版本 |
