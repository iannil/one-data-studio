# ONE-DATA-STUDIO 快速开始指南

本指南帮助你在 30 分钟内搭建 ONE-DATA-STUDIO PoC 环境。

---

## 前置要求

### 必需

- Docker 20.10+
- Docker Compose 2.0+
- kubectl 1.25+
- Helm 3.x

### 可选

- GPU（用于模型推理，无 GPU 可使用 CPU 模式）
- Kind/Minikube（本地 K8s 环境）

---

## 方式一：Docker Compose（推荐开发环境）

### 1. 启动所有服务

```bash
# 启动基础设施 + 应用服务
docker-compose -f deploy/local/docker-compose.yml up -d

# 查看服务状态
docker-compose -f deploy/local/docker-compose.yml ps
```

### 2. 等待服务就绪

```bash
# 等待所有服务健康
docker-compose -f deploy/local/docker-compose.yml ps

# 查看初始化日志
docker-compose -f deploy/local/docker-compose.yml logs alldata-init
docker-compose -f deploy/local/docker-compose.yml logs bisheng-init
```

### 3. 访问前端

```bash
# 启动前端开发服务（可选）
docker-compose -f deploy/local/docker-compose.yml --profile dev up -d web

# 或在本地启动前端（推荐）
cd web
npm install
npm run dev
```

打开浏览器访问 http://localhost:5173

### 4. 服务端点

| 服务 | 地址 | 说明 |
|------|------|------|
| Alldata API | http://localhost:8080 | 数据治理 API |
| Bisheng API | http://localhost:8081 | 应用编排 API |
| vLLM Serving | http://localhost:8000 | 模型服务 |
| MinIO Console | http://localhost:9001 | 对象存储控制台 |
| Prometheus | http://localhost:9090 | 监控（需启用） |
| Grafana | http://localhost:3000 | 可视化（需启用） |

### 5. 启用监控

```bash
# 启用 Prometheus 和 Grafana
docker-compose -f deploy/local/docker-compose.yml --profile monitoring up -d
```

---

## 方式二：Kubernetes（推荐生产环境）

### 1. 创建 Kind 集群

```bash
# 使用 Makefile
make kind-cluster

# 或手动创建
kind create cluster --name one-data --config=k8s/kind-config.yaml
```

### 2. 部署基础设施

```bash
# 使用 Makefile
make install-infra

# 或手动执行
kubectl apply -f k8s/base/namespaces.yaml
kubectl apply -f k8s/base/storage-classes.yaml
kubectl apply -f k8s/infrastructure/minio.yaml
kubectl apply -f k8s/infrastructure/mysql.yaml
kubectl apply -f k8s/infrastructure/redis.yaml
```

### 3. 初始化数据库

```bash
# 运行初始化 Job
kubectl apply -f k8s/jobs/

# 等待初始化完成
kubectl wait --for=condition=complete job/alldata-db-init -n one-data-alldata --timeout=300s
kubectl wait --for=condition=complete job/bisheng-db-init -n one-data-bisheng --timeout=300s
```

### 4. 部署应用服务

```bash
# 使用 Makefile
make install-apps

# 或手动执行
kubectl apply -f k8s/applications/alldata-api.yaml
kubectl apply -f k8s/applications/vllm-serving.yaml
kubectl apply -f k8s/applications/bisheng-api.yaml
```

### 5. 部署前端

```bash
# 使用 Makefile
make phase2

# 或手动执行
make web-build
make web-install
```

### 6. 端口转发

```bash
# 启动端口转发（后台）
make forward

# 或前台运行
make forward-interactive
```

---

## 验证部署

### 健康检查

```bash
# Alldata API
curl http://localhost:8080/api/v1/health

# Bisheng API
curl http://localhost:8081/api/v1/health

# vLLM 模型服务
curl http://localhost:8000/v1/models
```

### 测试数据集创建

```bash
# 创建数据集
curl -X POST http://localhost:8080/api/v1/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-dataset",
    "storage_path": "s3://test/",
    "format": "csv"
  }'
```

### 运行端到端测试

```bash
# Docker Compose 环境
bash scripts/test-e2e.sh

# K8s 环境（需先启动端口转发）
make test-all
```

---

## 功能验证清单

- [ ] 前端登录页面可访问
- [ ] 数据集列表可正常加载
- [ ] 创建数据集成功
- [ ] 工作流列表可正常加载
- [ ] 创建工作流成功
- [ ] 元数据查询返回数据
- [ ] 健康检查端点返回正确状态
- [ ] 重启后数据持久化有效

---

## 清理环境

### Docker Compose

```bash
# 停止所有服务
docker-compose -f deploy/local/docker-compose.yml down

# 删除数据卷
docker-compose -f deploy/local/docker-compose.yml down -v
```

### Kubernetes

```bash
# 使用 Makefile
make clean-all

# 或手动删除
kubectl delete -f k8s/applications/
kubectl delete -f k8s/infrastructure/
kubectl delete -f k8s/base/
kind delete cluster --name one-data
```

---

## 故障排查

### Pod 一直 Pending

```bash
# 查看 Pod 详情
kubectl describe pod <pod-name> -n <namespace>

# 常见原因：资源不足
kubectl top nodes
```

### vLLM 启动失败

```bash
# 查看 Pod 日志
kubectl logs -n one-data-cube deployment/vllm-serving -f

# 常见原因：模型下载失败（网络问题）
# 解决：使用国内镜像源或预先下载模型
```

### 数据库初始化失败

```bash
# 查看 Job 日志
kubectl logs -n one-data-alldata job/alldata-db-init
kubectl logs -n one-data-bisheng job/bisheng-db-init

# 重新运行初始化
kubectl delete job -n one-data-alldata alldata-db-init
kubectl delete job -n one-data-bisheng bisheng-db-init
kubectl apply -f k8s/jobs/
```

### 前端无法访问后端 API

```bash
# 检查环境变量配置
cat web/.env.development

# 检查 nginx 配置（生产环境）
kubectl get configmap -n one-data-web
```

---

## 下一步

- 阅读完整文档：[docs/README.md](docs/README.md)
- 查看 API 规范：[docs/02-integration/api-specifications.md](docs/02-integration/api-specifications.md)
- 了解 PoC 实施手册：[docs/05-development/poc-playbook.md](docs/05-development/poc-playbook.md)
- 查看 Sprint 计划：[docs/05-development/sprint-plan.md](docs/05-development/sprint-plan.md)

---

## 附录：Makefile 命令参考

```bash
# 环境准备
make kind-cluster     # 创建 Kind 集群
make docker-up        # 启动 Docker Compose
make docker-down      # 停止 Docker Compose

# K8s 部署
make install          # 安装所有服务
make install-infra    # 安装基础设施
make install-apps     # 安装应用服务

# 前端部署
make web-build        # 构建前端镜像
make web-install      # 部署前端
make web-dev          # 启动本地开发服务器

# 状态查看
make status           # 查看 Pod 状态
make logs             # 查看所有日志
make logs-alldata     # 查看 Alldata 日志
make logs-bisheng     # 查看 Bisheng 日志
make logs-cube        # 查看 Cube 日志

# 测试
make test             # 快速测试
make test-all         # 完整测试

# 端口转发
make forward          # 后台端口转发
make forward-interactive  # 前台端口转发
make unforward        # 停止端口转发

# 清理
make clean            # 删除 K8s 资源
make clean-all        # 删除所有资源包括集群
```
