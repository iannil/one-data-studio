# 环境准备检查清单

本文档提供 ONE-DATA-STUDIO PoC 环境准备的完整检查清单。

---

## 硬件要求

### 最小配置（PoC 验证）

| 资源 | 最低要求 | 推荐配置 |
|------|----------|----------|
| CPU | 8 核 | 16 核 |
| 内存 | 32 GB | 64 GB |
| 存储 | 200 GB | 500 GB SSD |
| GPU | 无 | 1 x A100/V100 (可选) |

### 生产环境配置

| 资源 | 最低要求 | 推荐配置 |
|------|----------|----------|
| CPU | 64 核 | 128+ 核 |
| 内存 | 256 GB | 512+ GB |
| 存储 | 2 TB SSD | 5+ TB SSD |
| GPU | 2 x A100 40GB | 4+ x A100/H100 |

### 检查命令

```bash
# CPU
echo "CPU 核心数: $(nproc)"

# 内存
echo "内存大小: $(free -h | grep Mem | awk '{print $2}')"

# 存储
echo "磁盘空间: $(df -h / | tail -1 | awk '{print $4}') 可用"

# GPU (如果有)
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
```

---

## 软件依赖

### 本地开发机

| 软件 | 最低版本 | 推荐版本 | 检查命令 |
|------|----------|----------|----------|
| Docker | 20.10 | 24.x | `docker --version` |
| kubectl | 1.25 | 1.28+ | `kubectl version --client` |
| Helm | 3.0 | 3.13+ | `helm version` |
| Git | 2.30 | 2.40+ | `git --version` |
| Python | 3.9 | 3.10 | `python --version` |
| Go | 1.20 | 1.21 | `go version` |
| Java | 17 | 17 LTS | `java -version` |

### K8s 集群

| 组件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Kubernetes | 1.25 | 1.27+ |
| containerd | 1.6 | 1.7+ |
| CNI Plugin | - | Calico/Cilium |

---

## 网络要求

### 端口开放

| 服务 | 端口 | 说明 |
|------|------|------|
| Kubernetes API | 6443 | K8s API Server |
| HTTP | 80 | Ingress HTTP |
| HTTPS | 443 | Ingress HTTPS |
| MinIO Console | 9001 | MinIO 管理界面 |
| MinIO API | 9000 | MinIO S3 API |
| Keycloak | 8080 | 认证服务 |
| Grafana | 3000 | 监控界面 |

### 域名规划

| 用途 | 示例域名 |
|------|----------|
| 平台入口 | one-data.example.com |
| Data | data.example.com |
| Cube | cube.example.com |
| Agent | agent.example.com |
| MinIO | minio.example.com |

### 网络连通性检查

```bash
# 检查 DNS
nslookup one-data.example.com

# 检查外网访问（拉取镜像）
ping docker.io
ping quay.io
ping ghcr.io

# 检查 HuggingFace 连接（模型下载）
curl -I https://huggingface.co
```

---

## K8s 集群检查

### 集群健康检查

```bash
# 节点状态
kubectl get nodes

# 预期输出: 所有节点 Ready
# NAME    STATUS   ROLES           AGE   VERSION
# node1   Ready    control-plane   10m   v1.27.3
# node2   Ready    <none>          10m   v1.27.3

# 系统组件
kubectl get pods -n kube-system

# 预期输出: CoreDNS, etcd, kube-proxy 等正常运行
```

### StorageClass 检查

```bash
# 查看 StorageClass
kubectl get storageclass

# 预期输出: 至少有一个 default StorageClass
# NAME                 PROVISIONER           RECLAIMPOLICY   DEFAULT
# standard (default)   rancher.io/local-path   Delete          true
```

### 资源配额检查

```bash
# 查看节点资源
kubectl top nodes

# 查看资源请求
kubectl describe nodes | grep -A 5 "Allocated resources"
```

---

## 镜像仓库

### 公有镜像

| 镜像 | 仓库 | 标签 |
|------|------|------|
| MinIO | quay.io/minio/minio | RELEASE.2023+ |
| MySQL | docker.io/mysql | 8.0 |
| Redis | docker.io/redis | 7.0 |
| vLLM | docker.io/vllm/vllm-openai | latest |
| Keycloak | quay.io/keycloak/keycloak | 23.0+ |

### 私有镜像仓库（可选）

| 工具 | 用途 |
|------|------|
| Harbor | 企业级镜像仓库 |
| GitLab Registry | GitLab 内置仓库 |
| AWS ECR | AWS 镜像仓库 |
| 阿里云 ACR | 阿里云镜像仓库 |

### 镜像拉取测试

```bash
# 测试 MinIO 镜像
docker pull quay.io/minio/minio:latest

# 测试 MySQL 镜像
docker pull docker.io/mysql:8.0

# 测试 vLLM 镜像
docker pull vllm/vllm-openai:latest
```

---

## 本地开发环境

### IDE 配置

| 工具 | 用途 |
|------|------|
| VS Code / GoLand | 后端开发 |
| PyCharm | Python/ML 开发 |
| IntelliJ IDEA | Java 开发 |
| DataGrip | 数据库管理 |

### VS Code 插件推荐

```
- Python
- Go
- Java
- Kubernetes
- Helm IntelliSense
- YAML
- Mermaid Preview
- REST Client
```

### 开发工具安装

```bash
# Python 虚拟环境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Go 依赖
go mod download

# Node 依赖 (如需要)
npm install
```

---

## 服务账号与密钥

### 需要准备的服务

| 服务 | 需要的信息 |
|------|------------|
| HuggingFace | API Token (模型下载) |
| 云厂商 | Access Key / Secret Key |
| Git 仓库 | Personal Access Token |
| 镜像仓库 | 登录凭据 |

### 密钥管理

```bash
# 创建 Kubernetes Secret
kubectl create secret docker-registry harbor-credentials \
  --docker-server=harbor.example.com \
  --docker-username=admin \
  --docker-password=your-password \
  -n one-data-infra

# 创建通用 Secret
kubectl create secret generic app-secrets \
  --from-literal=hf-token=your-hf-token \
  --from-literal=aws-access-key=your-key \
  -n one-data-infra
```

---

## 环境变量配置

### 全局配置

```bash
# 平台域名
export ONE_DATA_DOMAIN="one-data.example.com"

# 存储配置
export MINIO_ENDPOINT="minio.one-data-infra.svc.cluster.local:9000"
export MINIO_ACCESS_KEY="admin"
export MINIO_SECRET_KEY="admin123456"

# 数据库配置
export MYSQL_HOST="mysql.one-data-infra.svc.cluster.local"
export MYSQL_PORT=3306
export MYSQL_DATABASE="one_data"
export MYSQL_USER="one_data"
export MYSQL_PASSWORD="mysql123"

# Redis 配置
export REDIS_HOST="redis.one-data-infra.svc.cluster.local"
export REDIS_PORT=6379
export REDIS_PASSWORD="redis123"

# 模型服务配置
export MODEL_ENDPOINT="http://vllm-serving.one-data-model.svc.cluster.local:8000"

# Keycloak 配置
export KEYCLOAK_URL="http://keycloak.one-data-system.svc.cluster.local:8080"
export KEYCLOAK_REALM="one-data"
```

---

## 部署前检查清单

### 基础设施

- [ ] K8s 集群正常运行
- [ ] kubectl 可正常连接集群
- [ ] Helm 已安装
- [ ] StorageClass 已配置
- [ ] 镜像仓库可访问

### 网络

- [ ] 域名已解析
- [ ] 防火墙规则已配置
- [ ] Ingress Controller 已安装
- [ ] SSL 证书已准备（可选）

### 资源

- [ ] CPU 资源充足
- [ ] 内存资源充足
- [ ] 存储空间充足
- [ ] GPU 可用（如需要）

### 配置

- [ ] 环境变量已配置
- [ ] 密钥已创建
- [ ] 命名空间已创建

---

## 常见问题排查

### kubectl 连接失败

```bash
# 检查配置
kubectl config current-context
kubectl config view

# 重置配置
rm -rf ~/.kube/config
# 重新配置
```

### 镜像拉取失败

```bash
# 检查镜像仓库连通性
docker pull <image>

# 配置镜像代理（国内）
# 编辑 /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

### Pod 启动失败

```bash
# 查看 Pod 状态
kubectl describe pod <pod-name>

# 查看日志
kubectl logs <pod-name> --previous

# 查看事件
kubectl get events --sort-by=.metadata.creationTimestamp
```

---

## 更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2024-01-23 | v1.0 | 初始版本 |
