# ONE-DATA-STUDIO 环境变量参考

本文档详细说明 ONE-DATA-STUDIO 平台使用的所有环境变量，包括后端服务和前端应用。

---

## 目录

- [后端环境变量](#后端环境变量)
- [前端环境变量](#前端环境变量)
- [配置示例](#配置示例)
- [安全注意事项](#安全注意事项)

---

## 后端环境变量

后端环境变量配置在项目根目录的 `.env` 文件中。

### 环境配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ENVIRONMENT` | string | `development` | 运行环境：development/staging/production |
| `FLASK_ENV` | string | `development` | Flask 环境 |
| `DEBUG` | boolean | `true` | 调试模式（生产环境必须设为 false） |
| `LOG_LEVEL` | string | `INFO` | 日志级别：DEBUG/INFO/WARNING/ERROR |

### MySQL 数据库配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `MYSQL_HOST` | string | `mysql.one-data-infra.svc.cluster.local` | MySQL 主机地址 |
| `MYSQL_PORT` | integer | `3306` | MySQL 端口 |
| `MYSQL_USER` | string | `one_data` | 数据库用户名 |
| `MYSQL_PASSWORD` | string | - | 数据库密码（必填） |
| `MYSQL_DATABASE` | string | `one_data_studio` | 数据库名称 |
| `MYSQL_HA_ENABLED` | boolean | `false` | 是否启用高可用 |
| `MYSQL_PRIMARY_HOST` | string | - | 主库地址（HA 模式） |
| `MYSQL_REPLICA_HOST` | string | - | 从库地址（HA 模式） |

### 连接池配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DB_POOL_SIZE` | integer | `10` | 连接池大小 |
| `DB_MAX_OVERFLOW` | integer | `20` | 最大溢出连接数 |
| `DB_POOL_TIMEOUT` | integer | `30` | 连接超时（秒） |
| `DB_POOL_RECYCLE` | integer | `3600` | 连接回收时间（秒） |

### Redis 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `REDIS_ENABLED` | boolean | `true` | 是否启用 Redis |
| `REDIS_HOST` | string | `redis.one-data-infra.svc.cluster.local` | Redis 主机地址 |
| `REDIS_PORT` | integer | `6379` | Redis 端口 |
| `REDIS_DB` | integer | `0` | Redis 数据库编号 |
| `REDIS_PASSWORD` | string | - | Redis 密码 |
| `REDIS_MAX_CONNECTIONS` | integer | `50` | 最大连接数 |
| `REDIS_SENTINEL_ENABLED` | boolean | `false` | 是否启用 Sentinel |
| `REDIS_SENTINEL_MASTER` | string | `mymaster` | Sentinel 主节点名称 |
| `REDIS_SENTINEL_HOSTS` | string | - | Sentinel 地址列表 |
| `REDIS_SENTINEL_PASSWORD` | string | - | Sentinel 密码 |

### 缓存 TTL 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `CACHE_METADATA_TTL` | integer | `300` | 元数据缓存 TTL（秒） |
| `CACHE_MODEL_LIST_TTL` | integer | `600` | 模型列表缓存 TTL（秒） |
| `CACHE_WORKFLOW_TTL` | integer | `180` | 工作流缓存 TTL（秒） |
| `CACHE_SEARCH_RESULT_TTL` | integer | `60` | 搜索结果缓存 TTL（秒） |

### MinIO 对象存储配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `MINIO_ENDPOINT` | string | `minio.one-data-infra.svc.cluster.local:9000` | MinIO 端点 |
| `MINIO_ACCESS_KEY` | string | - | 访问密钥（必填） |
| `MINIO_SECRET_KEY` | string | - | 密钥（必填） |
| `MINIO_DEFAULT_BUCKET` | string | `one-data-studio` | 默认存储桶 |
| `MINIO_USE_SSL` | boolean | `false` | 是否使用 SSL |

### Milvus 向量数据库配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `MILVUS_HOST` | string | `milvus.one-data-infra.svc.cluster.local` | Milvus 主机地址 |
| `MILVUS_PORT` | integer | `19530` | Milvus 端口 |
| `EMBEDDING_DIM` | integer | `1536` | 向量维度 |
| `MILVUS_INDEX_TYPE` | string | `IVF_FLAT` | 索引类型 |
| `MILVUS_METRIC_TYPE` | string | `L2` | 距离度量类型 |
| `MILVUS_NLIST` | integer | `128` | IVF 索引聚类数 |

### OpenAI / LLM 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | string | - | OpenAI API 密钥（必填） |
| `OPENAI_API_KEYS` | string | - | 多个 API 密钥（逗号分隔） |
| `OPENAI_BASE_URL` | string | `https://api.openai.com/v1` | API 基础 URL |
| `OPENAI_MODEL` | string | `gpt-4o-mini` | 默认模型 |
| `OPENAI_TEMPERATURE` | float | `0.7` | 温度参数 |
| `OPENAI_MAX_TOKENS` | integer | `2000` | 最大 Token 数 |
| `OPENAI_TIMEOUT` | integer | `30` | 请求超时（秒） |
| `OPENAI_KEY_ROTATION_STRATEGY` | string | `round_robin` | 密钥轮换策略 |

### vLLM 自托管 LLM 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `VLLM_CHAT_URL` | string | `http://vllm-chat:8000` | vLLM 聊天服务 URL |
| `VLLM_CHAT_MODEL` | string | `Qwen/Qwen2.5-1.5B-Instruct` | 聊天模型 |
| `VLLM_EMBED_URL` | string | `http://vllm-embed:8000` | vLLM 嵌入服务 URL |
| `VLLM_EMBED_MODEL` | string | `BAAI/bge-base-zh-v1.5` | 嵌入模型 |
| `VLLM_GPU_MEMORY_UTILIZATION` | float | `0.8` | GPU 内存利用率 (0.0-1.0) |
| `HF_TOKEN` | string | - | HuggingFace Token |
| `AI_FEATURES_ENABLED` | boolean | `true` | 是否启用 AI 功能 |

### Keycloak 认证配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `KEYCLOAK_URL` | string | `http://keycloak.one-data-system.svc.cluster.local:80` | Keycloak URL |
| `KEYCLOAK_REALM` | string | `one-data-studio` | Realm 名称 |
| `KEYCLOAK_CLIENT_ID` | string | `web-frontend` | 客户端 ID |
| `KEYCLOAK_CLIENT_SECRET` | string | - | 客户端密钥 |

### JWT 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `JWT_SECRET_KEY` | string | - | JWT 密钥（必填，随机字符串） |
| `JWT_ALGORITHM` | string | `HS256` | 签名算法 |
| `JWT_ACCESS_TOKEN_EXPIRE` | integer | `3600` | 访问令牌过期时间（秒） |
| `JWT_REFRESH_TOKEN_EXPIRE` | integer | `604800` | 刷新令牌过期时间（秒） |
| `JWT_KEY_ROTATION_PERIOD` | integer | `86400` | 密钥轮换周期（秒） |
| `JWT_KEY_GRACE_PERIOD` | integer | `7200` | 密钥宽限期（秒） |

### 安全配置

#### CSRF 保护

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `CSRF_SECRET_KEY` | string | - | CSRF 密钥（必填） |
| `CSRF_TOKEN_EXPIRY` | integer | `3600` | Token 过期时间（秒） |
| `CSRF_HEADER_NAME` | string | `X-CSRF-Token` | Header 名称 |
| `CSRF_COOKIE_NAME` | string | `csrf_token` | Cookie 名称 |

#### CORS 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `CORS_ALLOWED_ORIGINS` | string | - | 允许的源（逗号分隔） |
| `CORS_ALLOW_ALL` | boolean | `false` | 允许所有源（仅开发环境） |

#### 安全头配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `SECURITY_HSTS_ENABLED` | boolean | `true` | 启用 HSTS |
| `SECURITY_HSTS_MAX_AGE` | integer | `31536000` | HSTS 最大时间 |
| `SECURITY_CSP_ENABLED` | boolean | `true` | 启用 CSP |
| `SECURITY_FRAME_OPTIONS` | string | `DENY` | X-Frame-Options |
| `SECURITY_REFERRER_POLICY` | string | `strict-origin-when-cross-origin` | Referrer-Policy |

#### HTTPS 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `SECURITY_FORCE_HTTPS` | boolean | `true` | 强制 HTTPS |
| `SECURITY_TRUST_PROXY` | boolean | `true` | 信任代理 |

#### Cookie 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `AUTH_COOKIE_ACCESS` | string | `access_token` | 访问令牌 Cookie 名 |
| `AUTH_COOKIE_REFRESH` | string | `refresh_token` | 刷新令牌 Cookie 名 |
| `AUTH_COOKIE_DOMAIN` | string | - | Cookie 域名 |
| `AUTH_COOKIE_SAMESITE` | string | `Lax` | SameSite 属性 |

### 服务 URL 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATA_API_URL` | string | `http://data-api:8080` | Data API 内部 URL |
| `AGENT_API_URL` | string | `http://agent-api:8081` | Agent API 内部 URL |
| `MODEL_API_URL` | string | `http://vllm-serving:8000` | Model API 内部 URL |
| `OPENAI_PROXY_URL` | string | `http://openai-proxy:8000` | OpenAI Proxy 内部 URL |

### Celery 任务队列配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `CELERY_BROKER_URL` | string | `redis://localhost:6379/1` | Broker URL |
| `CELERY_RESULT_BACKEND` | string | `redis://localhost:6379/2` | 结果后端 URL |
| `CELERY_TASK_TIME_LIMIT` | integer | `3600` | 任务超时（秒） |
| `CELERY_TASK_SOFT_TIME_LIMIT` | integer | `3000` | 软超时（秒） |
| `CELERY_WORKER_MAX_TASKS` | integer | `100` | Worker 最大任务数 |
| `CELERY_RESULT_EXPIRES` | integer | `86400` | 结果过期时间（秒） |

### 日志配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `LOG_FORMAT` | string | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | 日志格式 |
| `LOG_FILE` | string | - | 日志文件路径 |

### 功能开关

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `FEATURE_MULTIMODAL_ENABLED` | boolean | `true` | 多模态功能 |
| `FEATURE_AGENT_TOOLS_ENABLED` | boolean | `true` | Agent 工具 |
| `FEATURE_I18N_ENABLED` | boolean | `true` | 国际化 |

### OpenMetadata 集成配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `OPENMETADATA_HOST` | string | `openmetadata.one-data-infra.svc.cluster.local` | 主机地址 |
| `OPENMETADATA_PORT` | integer | `8585` | 端口 |
| `OPENMETADATA_ENABLED` | boolean | `true` | 是否启用 |
| `OPENMETADATA_API_VERSION` | string | `v1` | API 版本 |
| `OPENMETADATA_TIMEOUT` | integer | `30` | 超时（秒） |
| `OPENMETADATA_JWT_TOKEN` | string | - | JWT Token |

### Kettle/PDI ETL 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `KETTLE_CARTE_URL` | string | `http://kettle:8181` | Carte 服务 URL |
| `KETTLE_CARTE_USER` | string | `cluster` | Carte 用户名 |
| `KETTLE_CARTE_PASSWORD` | string | - | Carte 密码（必填） |
| `KETTLE_ENABLED` | boolean | `true` | 是否启用 Kettle |

---

## 前端环境变量

前端环境变量配置在 `web/.env.example` 文件中，使用 `VITE_` 前缀。

### API 端点配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `VITE_API_DATA_URL` | string | `http://localhost:8080` | Data API 地址 |
| `VITE_API_AGENT_URL` | string | `http://localhost:8081` | Agent API 地址 |
| `VITE_API_MODEL_URL` | string | `http://localhost:8000` | Model API 地址 |

### 认证配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `VITE_AUTH_MODE` | string | `keycloak` | 认证模式：keycloak/mock |
| `VITE_KEYCLOAK_URL` | string | `http://keycloak.one-data.local` | Keycloak URL |
| `VITE_KEYCLOAK_REALM` | string | `one-data-studio` | Realm 名称 |
| `VITE_KEYCLOAK_CLIENT_ID` | string | `web-frontend` | 客户端 ID |

### 应用配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `VITE_APP_TITLE` | string | `ONE-DATA-STUDIO` | 应用标题 |
| `VITE_APP_DESCRIPTION` | string | `企业级 AI 融合平台` | 应用描述 |
| `VITE_APP_VERSION` | string | `0.1.0` | 应用版本 |

### 功能开关

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `VITE_ENABLE_METRICS` | boolean | `true` | 启用指标收集 |
| `VITE_ENABLE_WEBSOCKET` | boolean | `true` | 启用 WebSocket |
| `VITE_ENABLE_MOCK_LOGIN` | boolean | `false` | 启用模拟登录（仅开发） |

### 开发模式配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `VITE_DEV_MODE` | boolean | `false` | 开发模式（生产环境必须设为 false） |

---

## 配置示例

### 开发环境 (.env.development)

```bash
# 环境
ENVIRONMENT=development
FLASK_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=one_data
MYSQL_PASSWORD=dev_password_123
MYSQL_DATABASE=one_data_studio

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# OpenAI
OPENAI_API_KEY=sk-test-...
OPENAI_BASE_URL=https://api.openai.com/v1

# 前端
VITE_API_DATA_URL=http://localhost:8080
VITE_API_AGENT_URL=http://localhost:8081
VITE_AUTH_MODE=mock
VITE_DEV_MODE=true
```

### 生产环境 (.env.production)

```bash
# 环境
ENVIRONMENT=production
FLASK_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# 数据库
MYSQL_HOST=mysql.production.svc.cluster.local
MYSQL_PORT=3306
MYSQL_USER=one_data_prod
MYSQL_PASSWORD=<strong_password>
MYSQL_DATABASE=one_data_studio

# Redis
REDIS_HOST=redis.production.svc.cluster.local
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<strong_password>

# MinIO
MINIO_ENDPOINT=minio.production.svc.cluster.local:9000
MINIO_ACCESS_KEY=<access_key>
MINIO_SECRET_KEY=<secret_key>
MINIO_USE_SSL=true

# OpenAI
OPENAI_API_KEY=<production_key>
OPENAI_API_KEYS=<key1>,<key2>,<key3>
OPENAI_KEY_ROTATION_STRATEGY=round_robin

# 安全
SECURITY_FORCE_HTTPS=true
CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
JWT_SECRET_KEY=<random_32_char_string>
CSRF_SECRET_KEY=<random_32_char_string>
```

---

## 安全注意事项

### 必须修改的默认值

以下变量在生产环境中**必须**修改为安全值：

| 变量名 | 默认值 | 建议 |
|--------|--------|------|
| `MYSQL_PASSWORD` | - | 使用强密码（16+字符，大小写+数字+符号） |
| `REDIS_PASSWORD` | - | 使用强密码 |
| `MINIO_ACCESS_KEY` | `minioadmin` | 使用随机访问密钥 |
| `MINIO_SECRET_KEY` | `minioadmin` | 使用强密钥 |
| `JWT_SECRET_KEY` | - | 使用 openssl rand -base64 32 生成 |
| `CSRF_SECRET_KEY` | - | 使用 openssl rand -base64 32 生成 |
| `KETTLE_CARTE_PASSWORD` | `cluster` | 使用强密码 |
| `KEYCLOAK_CLIENT_SECRET` | - | 使用强密钥 |

### 生成安全密钥

```bash
# 生成随机密钥
openssl rand -base64 32

# 生成 UUID
uuidgen

# 生成强密码
openssl rand -base64 24 | tr -d "=+/" | cut -c1-25
```

### 环境隔离

```bash
# 开发环境
cp .env.example .env.development

# 测试环境
cp .env.example .env.staging

# 生产环境
cp .env.example .env.production
```

### 密钥轮换

```bash
# 使用密钥轮换脚本
./scripts/rotate-secrets.sh

# 或手动轮换 JWT 密钥
NEW_KEY=$(openssl rand -base64 32)
kubectl patch secret jwt-secret -n one-data-data \
  -p='{"data":{"JWT_SECRET_KEY":"'$(echo -n $NEW_KEY | base64)'"}}'

# 重启服务应用新密钥
kubectl rollout restart deployment/data-api -n one-data-data
```

---

**更新时间**: 2026-02-03
