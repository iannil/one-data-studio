# 代码结构说明 (LLM 友好)

> **更新日期**: 2026-02-04
> **目的**: 为大模型提供清晰的项目结构说明，便于理解和改写代码

---

## 目录结构规范

```
one-data-studio/
├── services/                 # 后端服务
│   ├── admin-api/           # 管理后台 API (Flask)
│   ├── agent-api/           # 应用编排 API (Flask)
│   ├── data-api/            # 数据治理 API (Flask)
│   ├── model-api/           # MLOps 模型管理 API (Flask)
│   ├── ocr-service/         # OCR 文档识别服务 (FastAPI)
│   ├── behavior-service/    # 用户行为分析服务 (FastAPI)
│   ├── openai-proxy/        # OpenAI 兼容代理 (FastAPI)
│   └── shared/              # 共享模块（认证、安全、缓存、配置等）
├── web/                      # 前端应用 (React + TypeScript + Vite)
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── services/        # API 客户端
│   │   ├── store/           # Zustand 状态管理
│   │   └── main.tsx         # 应用入口
├── deploy/                   # 部署配置
│   ├── local/               # Docker Compose 配置
│   ├── kubernetes/          # K8s 配置
│   ├── helm/                # Helm Charts
│   ├── scripts/             # 部署脚本
│   └── dockerfiles/         # Dockerfile
├── tests/                    # 测试代码
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   ├── e2e/                 # 端到端测试 (Playwright)
│   └── mocks/               # Mock 服务
└── docs/                     # 项目文档
```

---

## 服务间通信模式

### 同步通信

所有服务间同步通信使用 REST API：

| 协议 | 说明 | 示例 |
|------|------|------|
| REST | 服务间标准 HTTP 调用 | `GET /api/v1/health` |
| JSON | 请求/响应数据格式 | `{"status": "ok"}` |

### 异步通信

使用 Redis 消息队列进行异步通信：

| 组件 | 说明 |
|------|------|
| Redis | 消息代理 |
| Celery | 任务队列（shared/celery_app.py） |

### 认证方式

- **协议**: Keycloak JWT
- **实现位置**: `services/shared/auth/`
- **中间件**: `jwt_middleware.py`

---

## 数据流

### Data → Model

```
[ETL Pipeline] → MinIO/HDFS → Dataset Registration → Model Training
```

- **协议**: MinIO S3 API
- **数据格式**: Parquet, CSV
- **实现**: `services/data-api/services/dataset_service.py`

### Model → Agent

```
[Model Service] → OpenAI-Compatible API → Agent Engine
```

- **协议**: OpenAI API 兼容
- **实现**: `services/openai-proxy/main.py`
- **支持模型**: vLLM, Ollama, OpenAI

### Data → Agent

```
[Metadata Store] → Text2SQL Engine → Agent Tool
```

- **协议**: REST API
- **实现**: `services/agent-api/engine/tools/text2sql.py`
- **数据注入**: Schema、元数据、样本数据

---

## 共享模块结构

```
services/shared/
├── auth/                    # 认证授权
│   ├── jwt_middleware.py    # JWT 中间件
│   └── permissions.py       # 权限控制
├── security/                # 安全模块
│   ├── cors.py              # CORS 配置
│   ├── csrf.py              # CSRF 保护
│   ├── encryption.py        # 加密解密
│   └── headers.py           # 安全头
├── storage/                 # 存储客户端
│   └── minio_client.py      # MinIO 客户端
├── cache.py                 # 缓存抽象
├── config.py                # 配置管理
├── circuit_breaker.py       # 熔断器
├── error_handler.py         # 错误处理
├── prometheus_metrics.py    # Prometheus 指标
└── integration_metrics.py   # 集成组件指标
```

---

## 前端架构

### 目录结构

```
web/src/
├── pages/                   # 页面组件（按功能模块分类）
│   ├── LoginPage.tsx        # 登录页
│   ├── HomePage.tsx         # 首页
│   ├── datasets/            # 数据管理
│   ├── agents/              # Agent 平台
│   ├── chat/                # 聊天
│   ├── workflows/           # 工作流
│   └── ...
├── components/              # 通用组件
│   ├── layout/              # 布局组件
│   ├── common/              # 通用组件
│   └── workflow/            # 工作流组件
├── services/                # API 客户端
│   ├── api/                 # API 调用封装
│   └── clients/             # 特定服务客户端
├── store/                   # Zustand 状态
├── hooks/                   # 自定义 Hooks
├── utils/                   # 工具函数
└── types/                   # TypeScript 类型定义
```

### 状态管理

| 方案 | 用途 |
|------|------|
| Zustand | 全局状态（用户、认证） |
| TanStack Query | 服务器状态（API 数据） |
| React State | 组件本地状态 |

---

## API 规范

### 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

### 错误码规范

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1000-1999 | 客户端错误 |
| 2000-2999 | 服务端错误 |
| 3000-3999 | 认证授权错误 |

---

## 命名规范

### Python

- 文件名: `snake_case.py`
- 类名: `PascalCase`
- 函数名: `snake_case`
- 常量: `UPPER_SNAKE_CASE`

### TypeScript

- 文件名: `PascalCase.tsx` (组件) / `camelCase.ts` (工具)
- 组件名: `PascalCase`
- 函数名: `camelCase`
- 接口/类型: `PascalCase`

---

## 环境变量约定

### 命名格式

`{SERVICE}_{CATEGORY}_{NAME}`

示例:
- `DATA_API_DATABASE_URL` - Data API 的数据库连接
- `AGENT_API_REDIS_URL` - Agent API 的 Redis 连接
- `LLM_BACKEND` - LLM 后端选择

### 共享变量

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | 默认数据库连接 |
| `REDIS_URL` | Redis 连接 |
| `MINIO_ENDPOINT` | MinIO 服务地址 |
| `KEYCLOAK_URL` | Keycloak 服务地址 |

---

## 配置文件位置

| 配置 | 位置 |
|------|------|
| Docker Compose | `deploy/local/docker-compose.yml` |
| K8s 基础设施 | `deploy/kubernetes/infrastructure/` |
| K8s 应用 | `deploy/kubernetes/applications/` |
| Helm Chart | `deploy/helm/charts/one-data/` |
| 环境变量模板 | `.env.example` |

---

## 相关文档

- [项目状态总览](PROJECT_STATUS.md)
- [技术债务清单](TECH_DEBT.md)
- [API 规范](02-integration/api-specifications.md)

---

> 更新时间：2026-02-04
