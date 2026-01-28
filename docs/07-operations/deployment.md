# 部署手册

ONE-DATA-STUDIO 部署指南

## 目录

- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [验证部署](#验证部署)
- [故障处理](#故障处理)

---

## 环境要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4 核 | 8 核+ |
| 内存 | 16 GB | 32 GB+ |
| 存储 | 100 GB SSD | 500 GB SSD |
| 网络 | 100 Mbps | 1 Gbps |

### 软件要求

| 软件 | 版本要求 |
|------|----------|
| Docker | 20.10+ |
| Docker Compose | 2.0+ |
| Git | 2.30+ |
| Python | 3.9+ (开发环境) |
| Node.js | 18+ (前端构建) |

### 外部依赖

| 服务 | 用途 |
|------|------|
| MySQL 8.0+ | 数据持久化 |
| Redis 7.0+ | 缓存与任务队列 |
| MinIO | 对象存储 |
| Milvus 2.3+ | 向量数据库 |

---

## 快速开始

### 1. 克隆代码库

```bash
git clone https://github.com/your-org/one-data-studio.git
cd one-data-studio
```

### 2. 配置环境变量

```bash
cp deploy/.env.example deploy/.env.dev
# 编辑 deploy/.env.dev 配置必要的环境变量
```

### 3. 启动服务

```bash
./deploy/scripts/deploy.sh dev
```

### 4. 验证部署

访问以下地址验证服务：

- Web UI: http://localhost:3000
- Alldata API: http://localhost:8080/api/v1/health
- Bisheng API: http://localhost:8081/api/v1/health
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

---

## 详细部署步骤

### 方式一: Docker Compose 部署

#### 1. 准备配置文件

创建环境配置文件 `deploy/.env.dev`:

```bash
# ==================== 数据库配置 ====================
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=one_data
MYSQL_PASSWORD=YourSecurePassword123!
MYSQL_DATABASE=one_data_bisheng

# ==================== Redis 配置 ====================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# ==================== MinIO 配置 ====================
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_DEFAULT_BUCKET=one-data

# ==================== Milvus 配置 ====================
MILVUS_HOST=milvus
MILVUS_PORT=19530

# ==================== OpenAI 配置 ====================
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# ==================== Keycloak 配置（可选）====================
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=one-data
KEYCLOAK_CLIENT_ID=one-data-studio

# ==================== 服务端口 ====================
ALDATA_API_PORT=8080
BISHENG_API_PORT=8081
CUBE_API_PORT=8000
WEB_PORT=3000

# ==================== 认证配置 ====================
AUTH_MODE=false  # 设为 true 启用 Keycloak 认证

# ==================== 日志配置 ====================
LOG_LEVEL=INFO
```

#### 2. 启动基础服务

```bash
cd deploy
docker-compose -f docker-compose-infrastructure.yml up -d
```

#### 3. 启动应用服务

```bash
docker-compose up -d
```

#### 4. 初始化数据库

```bash
# Alldata API 数据库
docker-compose exec alldata-api python -c "
from models import Base
from database import engine
Base.metadata.create_all(engine)
"

# Bisheng API 数据库
docker-compose exec bisheng-api python -c "
from models import Base
from database import engine
Base.metadata.create_all(engine)
"
```

### 方式二: Kubernetes 部署

#### 1. 构建镜像

```bash
# 构建并推送镜像
docker build -t your-registry/one-data-web:latest web/
docker build -t your-registry/one-data-alldata-api:latest services/alldata-api/
docker build -t your-registry/one-data-bisheng-api:latest services/bisheng-api/

docker push your-registry/one-data-web:latest
docker push your-registry/one-data-alldata-api:latest
docker push your-registry/one-data-bisheng-api:latest
```

#### 2. 部署到 Kubernetes

```bash
# 创建命名空间
kubectl create namespace one-data

# 部署应用
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl apply -f deploy/kubernetes/configmap.yaml
kubectl apply -f deploy/kubernetes/secrets.yaml
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl apply -f deploy/kubernetes/service.yaml
kubectl apply -f deploy/kubernetes/ingress.yaml
```

#### 3. 验证部署状态

```bash
kubectl get pods -n one-data
kubectl get services -n one-data
```

---

## 配置说明

### 密钥配置

支持配置多个 API 密钥以实现轮换：

```bash
# 方式一：逗号分隔
OPENAI_API_KEYS=key1,key2,key3

# 方式二：环境变量文件
OPENAI_API_KEY=key1  # 主密钥（向后兼容）
OPENAI_API_KEYS=key1,key2,key3  # 多密钥
OPENAI_KEY_ROTATION_STRATEGY=round_robin  # 轮换策略
```

### 缓存配置

```bash
# Redis 配置
REDIS_ENABLED=true
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# 缓存 TTL（秒）
CACHE_METADATA_TTL=300
CACHE_MODEL_LIST_TTL=600
CACHE_WORKFLOW_TTL=180
```

### 日志配置

```bash
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_FILE=/var/log/one-data/app.log
```

---

## 验证部署

### 健康检查

```bash
# Alldata API
curl http://localhost:8080/api/v1/health

# Bisheng API
curl http://localhost:8081/api/v1/health

# 返回示例
{
  "code": 0,
  "message": "healthy",
  "service": "bisheng-api",
  "version": "2.0.0"
}
```

### 功能验证

#### 1. 测试数据集 API

```bash
# 创建数据集
curl -X POST http://localhost:8080/api/v1/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试数据集",
    "storage_path": "s3://test/",
    "format": "csv"
  }'
```

#### 2. 测试工作流 API

```bash
# 创建工作流
curl -X POST http://localhost:8081/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试工作流",
    "type": "rag",
    "description": "用于测试的工作流"
  }'
```

#### 3. 测试聊天接口

```bash
# 发送聊天消息
curl -X POST http://localhost:8081/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好",
    "model": "gpt-4o-mini"
  }'
```

---

## 故障处理

### 常见问题

#### 1. 服务无法启动

**症状**: docker-compose up 后服务立即退出

**排查步骤**:
```bash
# 查看日志
docker-compose logs alldata-api
docker-compose logs bisheng-api

# 检查配置
docker-compose config

# 检查端口占用
netstat -tuln | grep -E '8080|8081|3000'
```

**解决方案**:
- 检查环境变量配置
- 确保依赖服务（MySQL、Redis）已启动
- 检查端口冲突

#### 2. 数据库连接失败

**症状**: API 返回数据库连接错误

**排查步骤**:
```bash
# 检查 MySQL 状态
docker-compose exec mysql mysql -u root -p

# 检查网络连接
docker-compose exec alldata-api ping mysql -c 3
```

**解决方案**:
- 确认 MySQL 密码正确
- 检查网络配置
- 验证数据库已初始化

#### 3. 前端无法访问后端

**症状**: Web 界面显示网络错误

**排查步骤**:
```bash
# 检查代理配置
cat web/vite.config.ts | grep proxy

# 检查 CORS 配置
curl -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8080/api/v1/health -v
```

**解决方案**:
- 检查 Vite 代理配置
- 确认 API 服务正常运行
- 验证 CORS 设置

### 回滚操作

#### 使用回滚脚本

```bash
# 回滚到上一个版本
./deploy/scripts/rollback.sh previous

# 回滚到指定版本
./deploy/scripts/rollback.sh abc123def

# 回滚到指定备份
./deploy/scripts/rollback.sh backup-20240101-120000
```

#### 使用蓝绿回滚

```bash
# 回滚到指定环境
./deploy/scripts/blue-green-deploy.sh rollback blue
```

---

## 监控与维护

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f alldata-api
docker-compose logs -f bisheng-api

# 查看最近 100 行日志
docker-compose logs --tail=100 alldata-api
```

### 性能监控

访问 Grafana 仪表盘:
- URL: http://localhost:3001
- 默认用户名: admin
- 默认密码: admin（首次登录后需修改）

### 数据备份

```bash
# 备份 MySQL
docker-compose exec mysql mysqldump -u root -p"${MYSQL_PASSWORD}" \
  --all-databases > backup_$(date +%Y%m%d).sql

# 备份 MinIO
docker-compose exec minio mc mirror /data /backup/minio/
```

---

## 生产环境建议

### 安全配置

1. 修改所有默认密码
2. 启用 HTTPS/TLS
3. 配置防火墙规则
4. 启用认证授权
5. 定期更新镜像

### 高可用配置

1. 使用外部托管数据库
2. 配置负载均衡器
3. 部署多实例应用
4. 启用健康检查
5. 配置自动扩缩容

### 性能优化

1. 调整数据库连接池大小
2. 配置 Redis 缓存策略
3. 启用 CDN 加速静态资源
4. 优化数据库查询
5. 配置适当的日志级别
