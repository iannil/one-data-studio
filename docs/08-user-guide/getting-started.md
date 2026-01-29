# 快速入门指南
# ONE-DATA-STUDIO v1.0.0

## 简介

ONE-DATA-STUDIO 是一个统一的"数据 + AI + LLM"融合平台，集成了数据治理、模型训练和大模型应用开发能力。

## 前置要求

- Kubernetes 1.25+
- Helm 3.10+
- 8GB+ RAM
- 20GB+ 存储空间

## 快速部署

### 1. 使用 Helm 部署

```bash
# 添加 Helm 仓库
helm repo add one-data-studio https://charts.one-data-studio.io
helm repo update

# 安装
helm install one-data-studio one-data-studio/one-data-studio \
  --namespace one-data-system \
  --create-namespace \
  --set global.domain=one-data.example.com
```

### 2. 使用 Docker Compose（开发环境）

```bash
# 克隆仓库
git clone https://github.com/your-org/one-data-studio.git
cd one-data-studio

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 首次访问

1. 打开浏览器访问：`https://one-data.example.com`
2. 使用默认管理员账户登录：
   - 用户名：`admin`
   - 密码：首次部署时生成（查看安装日志）

3. 修改默认密码

## 核心功能

### 1. 数据管理（Data）

创建数据集：
```bash
curl -X POST https://api.one-data.example.com/api/v1/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sales_data",
    "description": "销售数据集",
    "format": "csv"
  }'
```

### 2. 工作流（Agent）

创建简单工作流：
1. 导航到 **工作流** > **创建工作流**
2. 拖拽节点：`输入` → `LLM` → `输出`
3. 配置 LLM 节点参数
4. 点击 **保存** 并 **运行**

### 3. 智能对话

```bash
curl -X POST https://api.one-data.example.com/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
  }'
```

### 4. Text-to-SQL

```bash
curl -X POST https://api.one-data.example.com/api/v1/text2sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "sales_db",
    "question": "过去一个月的销售总额是多少？"
  }'
```

## 常见操作

### 查看服务状态

```bash
# Kubernetes
kubectl get pods -n one-data-system

# 健康检查
curl https://api.one-data.example.com/api/v1/health
```

### 查看日志

```bash
# Kubernetes
kubectl logs -f deployment/agent-api -n one-data-system

# Docker Compose
docker-compose logs -f agent-api
```

### 重启服务

```bash
# Kubernetes
kubectl rollout restart deployment/agent-api -n one-data-system

# Docker Compose
docker-compose restart agent-api
```

## 下一步

- [工作流使用指南](./workflow-guide.md)
- [Agent 开发指南](./agent-guide.md)
- [Text-to-SQL 指南](./text2sql-guide.md)
- [API 参考文档](../02-integration/api-reference.md)

## 获取帮助

- 文档：https://docs.one-data-studio.io
- 问题反馈：https://github.com/your-org/one-data-studio/issues
- 社区讨论：https://community.one-data-studio.io
