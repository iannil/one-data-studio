# 本地开发环境脚本

此目录包含用于本地开发环境的启动脚本，避免 Docker 容器缓存问题。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Services (Docker)                │
│  MySQL, Redis, MinIO, Milvus, Elasticsearch, Keycloak       │
└─────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                 Application Services (Local)                 │
│  Web Frontend, Data API, Agent API, Admin API,              │
│  Model API, OpenAI Proxy                                     │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 启动所有服务

```bash
cd scripts/local-dev
./start-all.sh
```

### 仅启动基础设施（Docker）

```bash
./infrastructure.sh start
```

### 仅启动应用服务（本地）

```bash
./start-all.sh --apps-only
```

### 查看所有服务状态

```bash
./status-all.sh
```

### 停止所有服务

```bash
./stop-all.sh
```

## 单个服务管理

### Web 前端

```bash
./web.sh start      # 启动
./web.sh stop       # 停止
./web.sh restart    # 重启
./web.sh status     # 状态
./web.sh logs       # 日志
```

### Data API

```bash
./data-api.sh start
./data-api.sh stop
./data-api.sh logs
```

### Agent API

```bash
./agent-api.sh start
./agent-api.sh stop
./agent-api.sh logs
```

### Admin API

```bash
./admin-api.sh start
./admin-api.sh stop
./admin-api.sh logs
```

### Model API

```bash
./model-api.sh start
./model-api.sh stop
./model-api.sh logs
```

### OpenAI Proxy

```bash
./openai-proxy.sh start
./openai-proxy.sh stop
./openai-proxy.sh logs
```

## 服务端口

| 服务 | 端口 |
|------|------|
| Web 前端 | 3000 |
| Data API | 8001 |
| Agent API | 8000 |
| Admin API | 8004 |
| Model API | 8002 |
| OpenAI Proxy | 8003 |
| MySQL | 3306 |
| Redis | 6379 |
| MinIO | 9000 |
| MinIO Console | 9001 |
| Milvus | 19530 |

## 环境变量

在项目根目录的 `.env` 文件中配置：

```bash
# 数据库
DATABASE_URL="mysql+pymysql://root:password@localhost:3306/onedata"
REDIS_URL="redis://:password@localhost:6379/0"

# MinIO
MINIO_ENDPOINT="localhost:9000"
MINIO_ACCESS_KEY="minioadmin"
MINIO_SECRET_KEY="minioadmin"

# Milvus
MILVUS_HOST="localhost"
MILVUS_PORT="19530"

# 认证（开发环境默认关闭）
AUTH_MODE="false"
```

## 日志文件

所有服务日志存储在项目根目录的 `.local-dev-logs/` 目录下：

```
.local-dev-logs/
├── web.log
├── data-api.log
├── agent-api.log
├── admin-api.log
├── model-api.log
└── openai-proxy.log
```

## PID 文件

所有服务 PID 存储在项目根目录的 `.local-dev-pids/` 目录下。

## 故障排查

### 端口被占用

如果服务启动失败提示端口被占用：

```bash
# macOS
lsof -i :<端口>

# 停止占用进程
kill -9 <PID>
```

### 依赖安装失败

如果 npm 依赖安装失败：

```bash
cd web
rm -rf node_modules package-lock.json
npm install
```

如果 Python 依赖安装失败：

```bash
cd services/<service>
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Docker 服务问题

如果基础设施服务启动失败：

```bash
cd deploy/local
docker-compose down -v
docker-compose up -d
```
