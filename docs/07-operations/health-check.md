# Docker 容器健康检查配置

本文档记录 ONE-DATA-STUDIO 项目中所有 Docker 容器的健康检查配置。

## 概述

健康检查 (Health Check) 是 Docker 容器的重要组成部分，用于确保容器内的服务正常运行。当健康检查失败时，Docker 会将容器标记为 `unhealthy`，可以根据配置自动重启容器。

## 健康检查参数说明

| 参数 | 说明 | 建议值 |
|------|------|--------|
| `test` | 健康检查命令 | HTTP 端点检查 |
| `interval` | 检查间隔时间 | 10s-30s |
| `timeout` | 单次检查超时时间 | 5s-10s |
| `retries` | 失败重试次数 | 3-5 |
| `start_period` | 启动宽限期 | 30s-300s |

## 服务健康检查配置

### 基础设施服务

#### MySQL
```yaml
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
  interval: 10s
  timeout: 5s
  retries: 5
```

#### Redis
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

#### MinIO
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
  interval: 30s
  timeout: 20s
  retries: 3
```

#### etcd
```yaml
healthcheck:
  test: ["CMD", "etcdctl", "endpoint", "health"]
  interval: 10s
  timeout: 5s
  retries: 5
```

#### Elasticsearch
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q 'green\\|yellow'"]
  interval: 30s
  timeout: 10s
  retries: 5
```

#### Milvus
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:9091/healthz || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 120s
```

### 元数据服务

#### OpenMetadata
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8585/api/v1/system/version | grep -q 'version'"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

### ETL 服务

#### Kettle (Webspoon)
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8080/spoon/spoon || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 120s
```

#### Apache Hop
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8182/hop/status || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

### 认证服务

#### Keycloak
```yaml
healthcheck:
  test: ["CMD-SHELL", "cat /proc/net/tcp | grep ':1F90 ' || true"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 30s
```

### AI 服务

#### vLLM Chat
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8000/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 300s
```

#### vLLM Embed
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8000/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 180s
```

#### Ollama
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:11434/api/tags || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 30s
```

### 应用服务

#### Agent API
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8000/api/v1/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

#### Data API
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8001/api/v1/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

#### OpenAI Proxy
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8000/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 30s
```

#### Admin API
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8004/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

#### Model API
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8002/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

#### OCR Service
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8007/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

#### Behavior Service
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8008/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 30s
```

### Web 前端

#### Web Frontend
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:80 -f || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

### 工作流调度

#### Zookeeper
```yaml
healthcheck:
  test: ["CMD-SHELL", "echo ruok | nc localhost 2181 || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
```

#### DolphinScheduler PostgreSQL
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U dolphinscheduler"]
  interval: 10s
  timeout: 5s
  retries: 5
```

#### DolphinScheduler
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:12345/dolphinscheduler/auth/login || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 120s
```

### BI 分析

#### Superset Cache
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

#### Superset
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:8088/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 180s
```

### 数据集成

#### SeaTunnel Zookeeper
```yaml
healthcheck:
  test: ["CMD-SHELL", "echo ruok | nc localhost 2181 || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
```

#### SeaTunnel
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -s http://localhost:5801 -f || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 120s
```

## 健康检查脚本

项目提供了两个健康检查脚本：

### Bash 脚本

```bash
./deploy/local/check-health.sh
```

### Python 脚本

```bash
./deploy/local/check_health.py
```

两个脚本都会检查：
1. Docker 容器状态
2. 健康检查状态
3. HTTP 端点可用性

## 使用 Docker Compose 查看健康状态

```bash
# 查看所有容器和健康状态
docker-compose ps

# 查看特定容器的健康详情
docker inspect --format='{{json .State.Health}}' one-data-mysql | jq

# 查看健康检查日志
docker inspect --format='{{json .State.Health.Log}}' one-data-mysql | jq

# 实时监控健康状态
watch -n 5 'docker-compose ps'
```

## 服务依赖与健康检查

使用 `depends_on` 的 `condition: service_healthy` 可以确保服务只在依赖服务健康后启动：

```yaml
service-a:
  depends_on:
    mysql:
      condition: service_healthy
    redis:
      condition: service_healthy
```

## 常见问题

### 健康检查失败的常见原因

1. **服务未完全启动**：增加 `start_period` 参数
2. **健康检查命令不正确**：验证命令在容器内可执行
3. **依赖服务未就绪**：使用 `condition: service_healthy`
4. **网络问题**：确保容器间网络可访问

### 调试健康检查

```bash
# 在容器内执行健康检查命令
docker exec one-data-mysql mysqladmin ping -h localhost

# 查看健康检查日志
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' one-data-mysql
```

## 更新日志

| 日期 | 变更内容 |
|------|----------|
| 2025-02-08 | 初始化文档，为所有服务配置健康检查 |
