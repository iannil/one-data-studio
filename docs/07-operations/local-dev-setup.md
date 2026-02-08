# 本地开发环境设置指南

## 概述

为了避免 Docker 容器带来的缓存和代码同步问题，本指南说明如何直接在本地运行 Node 和 Python 服务，同时保持基础设施服务（MySQL, Redis 等）在 Docker 中运行。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Infrastructure Services (Docker)                  │
│  MySQL, Redis, MinIO, Milvus, Elasticsearch, Keycloak           │
└─────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Services (Local Dev)               │
│  web-frontend (Vite)    data-api (Flask)    agent-api (Flask)    │
│  admin-api (Flask)      model-api (FastAPI)  openai-proxy (FastAPI) │
│  ocr-service (FastAPI)  behavior-service (FastAPI)             │
└─────────────────────────────────────────────────────────────┘
```

## 环境要求

### 基础设施服务（Docker）
- Docker & Docker Compose
- 8GB+ RAM 可用

### 应用服务（本地）
- Node.js 18+ for web-frontend
- Python 3.10+ for Python services
- npm, pip 包管理器

## 快速启动

### 1. 启动基础设施服务

```bash
cd deploy/local

# 启动数据库和缓存服务
docker-compose up -d mysql redis minio

# 如需完整服务（包括 AI 组件）
docker-compose up -d
```

### 2. 设置环境变量

创建 `.env` 文件（或使用现有 `.env.example`）：

```bash
cp .env.example .env
```

### 3. 启动应用服务

#### 方式 A：使用本地开发脚本（推荐）

项目提供了专用的本地开发脚本，位于 `scripts/local-dev/` 目录：

```bash
cd scripts/local-dev

# 启动所有服务（基础设施 + 应用）
./start-all.sh

# 仅启动基础设施服务（Docker）
./start-all.sh --infra-only

# 仅启动应用服务（本地）
./start-all.sh --apps-only

# 查看所有服务状态
./status-all.sh

# 停止所有服务
./stop-all.sh
```

**单个服务管理：**

```bash
# 基础设施服务
./infrastructure.sh start|stop|status|logs

# Web 前端
./web.sh start|stop|restart|status|logs

# Data API
./data-api.sh start|stop|restart|status|logs

# Agent API
./agent-api.sh start|stop|restart|status|logs

# Admin API
./admin-api.sh start|stop|restart|status|logs

# Model API
./model-api.sh start|stop|restart|status|logs

# OpenAI Proxy
./openai-proxy.sh start|stop|restart|status|logs

# OCR Service
./ocr-service.sh start|stop|restart|status|logs

# Behavior Service
./behavior-service.sh start|stop|restart|status|logs
```

**清理并重启所有服务：**

```bash
# 完整清理并重启（停止所有服务、清理 Docker、重新启动）
./clean-and-restart.sh

# 仅清理并重启基础设施
./clean-and-restart.sh --infra

# 仅重启应用服务
./clean-and-restart.sh --apps
```

**跳过指定服务：**

```bash
# 启动所有服务，但跳过 web 和 model-api
./start-all.sh --skip web,model-api
```

更多细节请参考 [scripts/local-dev/README.md](../../../scripts/local-dev/README.md)。

#### 方式 B：手动启动

```bash
# 1. Web 前端 (Vite)
cd web && npm run dev

# 2. Data API (Flask)
cd services/data-api
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="mysql+pymysql://root:password@localhost:3306/onedata"
export REDIS_URL="redis://:password@localhost:6379/0"
export AUTH_MODE="false"
python src/main.py

# 3. Agent API (Flask)
cd services/agent-api
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="mysql+pymysql://root:password@localhost:3306/onedata"
export REDIS_URL="redis://:password@localhost:6379/0"
export MILVUS_HOST="localhost"
export MILVUS_PORT="19530"
export MINIO_ENDPOINT="minio:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
export MODEL_API_URL="http://localhost:8003"
export PORT=8000
export AUTH_MODE="false"
python src/main.py

# 4. Admin API (Flask)
cd services/admin-api
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="mysql+pymysql://root:password@localhost:3306/onedata"
export REDIS_URL="redis://:password@localhost:6379/0"
export PORT=8004
export AUTH_MODE="false"
python src/main.py

# 5. Model API (FastAPI)
cd services/model-api
source venv/bin/activate
pip install -r requirements.txt
export MODEL_DATABASE_URL="mysql+pymysql://root:password@localhost:3306/2034"
export REDIS_URL="redis://:password@localhost:6379/0"
export MINIO_ENDPOINT="minio:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
export HF_TOKEN="your_token_here"
export PORT=8002
python src/main.py

# 6. OpenAI Proxy (FastAPI)
cd services/openai-proxy
source venv/bin/activate
pip install -r requirements.txt
export REDIS_URL="redis://:password@localhost:6379/0"
export VLLM_CHAT_URL="http://localhost:8010"
export VLLM_EMBED_URL="http://localhost:8011"
export OLLAMA_URL="http://localhost:11434"
export PORT=8003
python src/main.py

# 7. OCR Service (FastAPI)
cd services/ocr-service
source venv/bin/activate
pip install -r requirements.txt
export REDIS_URL="redis://localhost:6379/0"
export PORT=8007
uvicorn app:app --host 0.0.0.0 --port 8007

# 8. Behavior Service (FastAPI)
cd services/behavior-service
source venv/bin/activate
pip install -r requirements.txt
export REDIS_URL="redis://localhost:6379/1"
export PORT=8008
uvicorn app:app --host 0.0.0.0 --port 8008
```

## 服务端口映射

| 服务 | 容器端口 | 本地开发端口 |
|------|-----------|-------------|
| web-frontend | 3000 | 3000 |
| data-api | 8001 | 8001 |
| agent-api | 8000 | 8000 |
| admin-api | 8004 | 8004 |
| model-api | 8002 | 8002 |
| openai-proxy | 8003 | 8003 |
| ocr-service | 8007 | 8007 |
| behavior-service | 8008 | 8008 |
| Keycloak | 8080 | 8080 |
| OpenMetadata | 8585 | 8585 |

## 开发工具

### VS Code 调试配置

#### Python (attach)
```json
{
  "name": "Python: Remote Attach",
  "type": "debugpy",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 8001
  },
  "pathMappings": [
    {
      "localRoot": "${workspaceFolder}/services/data-api",
      "remoteRoot": "/app"
    }
  ]
}
```

#### Node.js (launch)
```json
{
  "type": "node",
  "request": "launch",
  "name": "Debug Web Frontend",
  "cwd": "${workspaceFolder}/web",
  "runtimeExecutable": "node",
  "runtimeVersion": "18",
  "env": {
    "NODE_ENV": "development"
  }
}
```

## 常见问题

### Q: Docker 服务启动失败

A: 检查端口占用：
```bash
# macOS
lsof -i :3306
# Linux
sudo netstat -tulpn | grep :3306
```

### Q: Python 服务无法连接数据库

A: 确保 Docker 网络正常：
```bash
docker network inspect one-data-network
```

### Q: 前端无法连接 API

A: 检查 CORS 配置和 API_BASE_URL 是否正确。

## 生产部署

对于生产环境，建议使用 `docker-compose.prod.yml` 而非本地开发配置。
