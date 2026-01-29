# PoC 实施手册

本文档提供 ONE-DATA-STUDIO 平台 PoC（概念验证）环境的搭建指南，帮助团队快速验证三个平台的集成方案。

---

## PoC 目标与范围

### 验证目标

| 集成点 | 验证内容 | 成功标准 |
|--------|----------|----------|
| Data → Model | 数据集注册与读取 | Model 能读取 Data 产出的数据集 |
| Model → Agent | 模型服务调用 | Agent 能调用 Model 的 OpenAI 兼容 API |
| Data → Agent | 元数据查询 | Agent 能获取 Data 的表结构信息 |
| 端到端 | RAG + SQL 查询 | 用户提问能正确返回结果 |

### 非目标

- 生产级性能验证
- 高可用性测试
- 大规模数据测试
- 完整的安全验证

---

## 第一阶段：基础设施准备

### 1.1 Kubernetes 集群准备

#### 选项 A：使用 Kind（本地快速测试）

```bash
# 安装 Kind
brew install kind  # macOS
# 或 curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64

# 创建集群
cat <<EOF | kind create cluster --name one-data-poc --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 30080
    hostPort: 8080
  - containerPort: 30443
    hostPort: 8443
- role: worker
- role: worker
EOF

# 验证
kubectl get nodes
kubectl get storageclass
```

#### 选项 B：使用 Minikube（本地开发）

```bash
# 安装 Minikube
brew install minikube

# 启动集群
minikube start \
  --driver=docker \
  --cpus=6 \
  --memory=12288 \
  --disk-size=50g \
  --nodes=2

# 启用 Ingress
minikube addons enable ingress

# 验证
kubectl get nodes
kubectl get pods -n ingress-nginx
```

#### 选项 C：使用云 K8s（推荐）

| 云厂商 | 快速创建命令 |
|--------|--------------|
| AWS | `eksctl create cluster --name one-data-poc --nodes 3 --node-type t3.large` |
| 阿里云 | 控制台创建 ACK 集群 |
| 腾讯云 | 控制台创建 TKE 集群 |

### 1.2 Helm 安装

```bash
# 安装 Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 验证
helm version
```

### 1.3 Istio 安装（可选）

```bash
# 下载 Istio
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

# 安装
istioctl install --set profile=demo -y

# 验证
istioctl verify-install
kubectl get pods -n istio-system
```

---

## 第二阶段：存储和中间件部署

### 2.1 MinIO 部署

```bash
# 添加 Helm 仓库
helm repo add minio https://charts.min.io/
helm repo update

# 创建命名空间
kubectl create namespace one-data-infra

# 部署 MinIO
helm install minio minio/minio \
  -n one-data-infra \
  --set rootUser=admin \
  --set rootPassword=admin123456 \
  --set replicas=1 \
  --set persistence.size=50Gi \
  --set resources.requests.memory=256Mi \
  --set service.type=ClusterIP

# 等待就绪
kubectl wait --for=condition=ready pod -l app=minio -n one-data-infra --timeout=300s

# 端口转发（本地测试）
kubectl port-forward -n one-data-infra svc/minio 9000:9000 9001:9001

# 访问控制台
# http://localhost:9001
# 用户名: admin
# 密码: admin123456
```

### 2.2 MySQL 部署

```bash
# 部署 MySQL
helm install mysql bitnami/mysql \
  -n one-data-infra \
  --set auth.rootPassword=mysql123 \
  --set primary.persistence.size=20Gi \
  --set architecture=replication

# 等待就绪
kubectl wait --for=condition=ready pod -l app=mysql -n one-data-infra --timeout=300s

# 获取连接信息
kubectl get secret mysql -n one-data-infra -o jsonpath='{.data.mysql-root-password}' | base64 -d
```

### 2.3 Redis 部署

```bash
# 部署 Redis
helm install redis bitnami/redis \
  -n one-data-infra \
  --set architecture=standalone \
  --set auth.enabled=true \
  --set auth.password=redis123 \
  --set master.persistence.size=10Gi

# 等待就绪
kubectl wait --for=condition=ready pod -l app=redis -n one-data-infra --timeout=300s
```

### 2.4 Milvus 部署（向量数据库）

```bash
# 添加 Milvus Helm 仓库
helm repo add milvus https://milvus-io.github.io/milvus-helm/
helm repo update

# 部署 Milvus（简化版）
helm install milvus milvus/milvus \
  -n one-data-infra \
  --set cluster.enabled=false \
  --set standalone.enabled=true \
  --set standalone.persistence.size=30Gi

# 等待就绪
kubectl wait --for=condition=ready pod -l app=milvus -n one-data-infra --timeout=600s
```

### 2.5 验证基础设施

```bash
# 检查所有 Pod 状态
kubectl get pods -n one-data-infra

# 预期输出
# NAME                       READY   STATUS    RESTARTS   AGE
# minio-0                    1/1     Running   0          5m
# mysql-0                    2/2     Running   0          3m
# mysql-1                    2/2     Running   0          3m
# redis-master-0             1/1     Running   0          2m
# milvus-standalone-0        1/1     Running   0          8m
```

---

## 第三阶段：L2 数据底座最小化部署

### 3.1 创建命名空间

```bash
kubectl create namespace one-data-data
kubectl label namespace one-data-data istio-injection=enabled
```

### 3.2 准备模拟数据

```bash
# 创建测试 Bucket
kubectl exec -n one-data-infra minio-0 -- mc alias set local http://localhost:9000 admin admin123456
kubectl exec -n one-data-infra minio-0 -- mc mb local/test-datasets

# 上传测试数据
cat << 'EOF' > /tmp/sales_data.csv
id,customer_id,amount,created_at
1,1001,299.99,2024-01-01T10:00:00Z
2,1002,599.99,2024-01-01T11:00:00Z
3,1003,199.99,2024-01-02T09:00:00Z
4,1001,399.99,2024-01-02T14:00:00Z
5,1004,799.99,2024-01-03T16:00:00Z
EOF

kubectl cp /tmp/sales_data.csv one-data-infra/minio-0:/tmp/sales_data.csv
kubectl exec -n one-data-infra minio-0 -- mc cp /tmp/sales_data.csv local/test-datasets/
```

### 3.3 部署模拟 Data API

```bash
# 创建 Deployment
cat << 'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-api
  namespace: one-data-data
spec:
  replicas: 1
  selector:
    matchLabels:
      app: data-api
  template:
    metadata:
      labels:
        app: data-api
    spec:
      containers:
      - name: api
        image: python:3.10-slim
        command:
        - python
        - -c
        - |
          from flask import Flask, jsonify, request
          from datetime import datetime
          import os

          app = Flask(__name__)

          datasets = {
              "ds-001": {
                  "dataset_id": "ds-001",
                  "name": "sales_data_v1.0",
                  "storage_path": "s3://test-datasets/sales_data.csv",
                  "format": "csv",
                  "status": "active",
                  "created_at": "2024-01-23T10:00:00Z"
              }
          }

          @app.route("/api/v1/health")
          def health():
              return jsonify({"code": 0, "message": "healthy"})

          @app.route("/api/v1/datasets", methods=["GET"])
          def list_datasets():
              return jsonify({"code": 0, "message": "success", "data": list(datasets.values())})

          @app.route("/api/v1/datasets/<dataset_id>", methods=["GET"])
          def get_dataset(dataset_id):
              ds = datasets.get(dataset_id)
              if ds:
                  return jsonify({"code": 0, "message": "success", "data": ds})
              return jsonify({"code": 40401, "message": "Dataset not found"}), 404

          @app.route("/api/v1/datasets", methods=["POST"])
          def create_dataset():
              data = request.json
              dataset_id = f"ds-{len(datasets) + 1:03d}"
              datasets[dataset_id] = {
                  "dataset_id": dataset_id,
                  "name": data.get("name"),
                  "storage_path": data.get("storage_path"),
                  "format": data.get("format"),
                  "status": "active",
                  "created_at": datetime.utcnow().isoformat() + "Z"
              }
              return jsonify({"code": 0, "message": "success", "data": {"dataset_id": dataset_id}})

          if __name__ == "__main__":
              app.run(host="0.0.0.0", port=8080)
        env:
        - name: FLASK_ENV
          value: "development"
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 5
EOF

# 创建 Service
cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: data-api
  namespace: one-data-data
spec:
  selector:
    app: data-api
  ports:
  - port: 8080
    targetPort: 8080
EOF

# 等待就绪
kubectl wait --for=condition=ready pod -l app=data-api -n one-data-data --timeout=120s
```

### 3.4 验证 Data API

```bash
# 端口转发
kubectl port-forward -n one-data-data svc/data-api 8080:8080 &

# 测试健康检查
curl http://localhost:8080/api/v1/health

# 测试获取数据集列表
curl http://localhost:8080/api/v1/datasets

# 测试注册新数据集
curl -X POST http://localhost:8080/api/v1/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_data_v1.0",
    "storage_path": "s3://test-datasets/customer_data.csv",
    "format": "csv"
  }'
```

---

## 第四阶段：L3 模型引擎最小化部署

### 4.1 创建命名空间

```bash
kubectl create namespace one-data-model
kubectl label namespace one-data-model istio-injection=enabled
```

### 4.2 部署 vLLM（使用小模型）

```bash
# 使用 Qwen-0.5B 作为测试模型
cat << 'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-serving
  namespace: one-data-model
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-serving
  template:
    metadata:
      labels:
        app: vllm-serving
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        command:
        - python
        - -m
        - vllm.entrypoints.openai.api_server
        - --model
        - Qwen/Qwen-0.5B-Chat
        args: []
        env:
        - name: HF_TOKEN
          value: ""  # 如需要 HuggingFace Token，在此设置
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
EOF

# 创建 Service
cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: vllm-serving
  namespace: one-data-model
spec:
  selector:
    app: vllm-serving
  ports:
  - port: 8000
    targetPort: 8000
EOF

# 等待 Pod 启动（模型下载需要时间）
kubectl get pods -n one-data-model -w
```

### 4.3 验证 vLLM 服务

```bash
# 端口转发
kubectl port-forward -n one-data-model svc/vllm-serving 8000:8000 &

# 列出模型
curl http://localhost:8000/v1/models

# 测试聊天补全
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen-0.5B-Chat",
    "messages": [{"role": "user", "content": "你好，请介绍一下自己。"}],
    "max_tokens": 100
  }'
```

### 4.4 配置 Istio Gateway（可选）

```bash
# 如果启用了 Istio
cat << 'EOF' | kubectl apply -f -
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: vllm-vs
  namespace: one-data-model
spec:
  hosts:
  - "*"
  gateways:
  - istio-system/ingressgateway
  http:
  - match:
    - uri:
        prefix: /v1/
    route:
    - destination:
        host: vllm-serving
        port:
          number: 8000
EOF
```

---

## 第五阶段：L4 应用层最小化部署

### 5.1 创建命名空间

```bash
kubectl create namespace one-data-agent
kubectl label namespace one-data-agent istio-injection=enabled
```

### 5.2 部署简化版 Agent API

```bash
cat << 'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-api
  namespace: one-data-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: agent-api
  template:
    metadata:
      labels:
        app: agent-api
    spec:
      containers:
      - name: api
        image: python:3.10-slim
        command:
        - python
        - -c
        - |
          from flask import Flask, jsonify, request
          import requests
          import os

          app = Flask(__name__)

          # 配置模型端点
          MODEL_ENDPOINT = os.getenv("MODEL_ENDPOINT", "http://vllm-serving.one-data-model.svc.cluster.local:8000")

          @app.route("/api/v1/health")
          def health():
              return jsonify({"code": 0, "message": "healthy", "model_endpoint": MODEL_ENDPOINT})

          @app.route("/api/v1/chat", methods=["POST"])
          def chat():
              data = request.json
              message = data.get("message")

              # 调用 Model 模型服务
              response = requests.post(
                  f"{MODEL_ENDPOINT}/v1/chat/completions",
                  json={
                      "model": "Qwen/Qwen-0.5B-Chat",
                      "messages": [{"role": "user", "content": message}],
                      "max_tokens": 500
                  },
                  timeout=30
              )

              if response.status_code == 200:
                  result = response.json()
                  reply = result["choices"][0]["message"]["content"]
                  return jsonify({
                      "code": 0,
                      "message": "success",
                      "data": {"reply": reply}
                  })
              else:
                  return jsonify({"code": 50001, "message": "Model service error"}), 500

          @app.route("/api/v1/datasets", methods=["GET"])
          def list_datasets():
              # 调用 Data API
              response = requests.get(
                  "http://data-api.one-data-data.svc.cluster.local:8080/api/v1/datasets",
                  timeout=10
              )
              return jsonify(response.json())

          if __name__ == "__main__":
              app.run(host="0.0.0.0", port=8080)
        env:
        - name: MODEL_ENDPOINT
          value: "http://vllm-serving.one-data-model.svc.cluster.local:8000"
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 5
EOF

# 创建 Service
cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: agent-api
  namespace: one-data-agent
spec:
  selector:
    app: agent-api
  ports:
  - port: 8080
    targetPort: 8080
EOF
```

### 5.3 验证 Agent API

```bash
# 端口转发
kubectl port-forward -n one-data-agent svc/agent-api 8081:8080 &

# 测试健康检查
curl http://localhost:8081/api/v1/health

# 测试聊天（调用 Model 模型服务）
curl -X POST http://localhost:8081/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'

# 测试数据集列表（调用 Data API）
curl http://localhost:8081/api/v1/datasets
```

---

## 第六阶段：端到端集成验证

### 6.1 创建验证脚本

```bash
cat << 'EOF' > /tmp/poc-test.sh
#!/bin/bash

echo "=== ONE-DATA-STUDIO PoC 集成验证 ==="
echo

# 测试 1: Data API
echo "[1/4] 测试 Data API..."
ALDATA_URL="http://localhost:8080"
response=$(curl -s $ALDATA_URL/api/v1/health)
if echo $response | grep -q "healthy"; then
    echo "✓ Data API 正常"
else
    echo "✗ Data API 异常"
fi
echo

# 测试 2: Model 模型服务
echo "[2/4] 测试 Model 模型服务..."
MODEL_URL="http://localhost:8002"
response=$(curl -s $MODEL_URL/api/v1/models)
if echo $response | grep -q "Qwen"; then
    echo "✓ Model 模型服务正常"
    echo "  可用模型:"
    curl -s $MODEL_URL/api/v1/models | grep -o '"id":"[^"]*"' | head -3
else
    echo "✗ Model 模型服务异常"
fi
echo

# 测试 3: Agent 应用层
echo "[3/4] 测试 Agent 应用层..."
agent_URL="http://localhost:8081"
response=$(curl -s $agent_URL/api/v1/health)
if echo $response | grep -q "healthy"; then
    echo "✓ Agent API 正常"
else
    echo "✗ Agent API 异常"
fi
echo

# 测试 4: 端到端调用
echo "[4/4] 测试端到端调用..."
response=$(curl -s -X POST $agent_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "2+2等于几？"}')
if echo $response | grep -q "4"; then
    echo "✓ 端到端调用成功"
    echo "  模型回复:"
    echo $response | grep -o '"reply":"[^"]*"' | cut -d'"' -f4
else
    echo "✗ 端到端调用失败"
    echo "  响应: $response"
fi
echo

echo "=== 验证完成 ==="
EOF

chmod +x /tmp/poc-test.sh
```

### 6.2 执行验证

```bash
# 确保所有端口转发在运行
jobs

# 执行验证脚本
/tmp/poc-test.sh
```

---

## 故障排查

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| Pod 一直 Pending | 资源不足 | 检查节点资源，调整资源请求 |
| 镜像拉取失败 | 网络问题 | 配置镜像代理或使用国内源 |
| 服务无法访问 | Service 配置错误 | 检查 Service selector 和端口 |
| 模型下载很慢 | HuggingFace 网络 | 预下载模型或使用镜像站 |

### 查看日志

```bash
# 查看所有 Pod 状态
kubectl get pods -A

# 查看特定 Pod 日志
kubectl logs -n one-data-model deployment/vllm-serving -f

# 查看事件
kubectl get events -A --sort-by='.lastTimestamp'
```

---

## 清理环境

```bash
# 删除所有资源
kubectl delete namespace one-data-agent
kubectl delete namespace one-data-model
kubectl delete namespace one-data-data
kubectl delete namespace one-data-infra
kubectl delete namespace one-data-system

# 删除 Kind 集群（如果使用 Kind）
kind delete cluster --name one-data-poc

# 或删除 Minikube 集群（如果使用 Minikube）
minikube delete
```

---

## 更新记录

| 日期 | 版本 | 更新内容 | 更新人 |
|------|------|----------|--------|
| 2024-01-23 | v1.0 | 初始版本，PoC 实施指南 | Claude |
