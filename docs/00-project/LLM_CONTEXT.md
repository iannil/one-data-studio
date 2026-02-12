# ONE-DATA-STUDIO 项目上下文 (LLM 友好)

> **版本**: 1.3.2
> **更新日期**: 2026-02-12
> **目标读者**: LLM 大模型

---

## 一、项目概述

### 1.1 项目定位

ONE-DATA-STUDIO 是一个**企业级 DataOps + MLOps + LLMOps 融合平台**，将三个 AI 基础设施整合为统一的智能数据平台。

### 1.2 核心价值

- **数据治理 (DataOps)**: 数据集成、ETL、数据质量、元数据管理
- **模型训练 (MLOps)**: Notebook 开发、分布式训练、模型服务
- **应用编排 (LLMOps)**: RAG 流水线、Agent 编排、Prompt 管理

### 1.3 代码规模

| 类型 | 文件数 | 代码行数 |
|------|--------|----------|
| Python 后端 | 274 | 142,887 |
| TypeScript 前端 | 216 | 120,334 |
| 测试代码 | 143+ | 32,500+ |
| **总计** | **630+** | **~295,000+** |

---

## 二、架构设计

### 2.1 四层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    L4 应用编排层 (Agent)                      │
│    RAG 流水线 │ Agent 编排 │ Prompt 管理 │ 工作流引擎         │
├─────────────────────────────────────────────────────────────┤
│                    L3 算法引擎层 (Model)                      │
│    Notebook 开发 │ 分布式训练 │ 模型服务 │ 向量存储            │
├─────────────────────────────────────────────────────────────┤
│                    L2 数据底座层 (Data)                       │
│    数据集成 │ ETL │ 治理 │ 特征存储 │ 向量存储                │
├─────────────────────────────────────────────────────────────┤
│                    L1 基础设施层                              │
│    Kubernetes 容器编排 │ CPU/GPU 资源池 │ 监控告警            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 服务拓扑

```
                    ┌──────────────┐
                    │   web (UI)   │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   data-api    │  │   agent-api   │  │   model-api   │
│   (Flask)     │  │   (Flask)     │  │   (Flask)     │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────┬───────┴──────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────┐     ┌───────────────┐
│  openai-proxy │     │   admin-api   │
│  (FastAPI)    │     │   (Flask)     │
└───────────────┘     └───────────────┘
```

---

## 三、代码结构

### 3.1 根目录结构

```
one-data-studio/
├── services/                 # 后端服务
│   ├── data-api/            # 数据治理 API (Flask)
│   ├── agent-api/           # 应用编排 API (Flask)
│   ├── model-api/           # MLOps 模型管理 API (Flask)
│   ├── admin-api/           # 管理后台 API (Flask)
│   ├── openai-proxy/        # OpenAI 兼容代理 (FastAPI)
│   ├── ocr-service/         # OCR 文档识别服务 (FastAPI)
│   ├── behavior-service/    # 用户行为分析服务 (FastAPI)
│   └── shared/              # 共享模块（认证、存储、缓存）
├── web/                      # 前端应用 (React + TypeScript + Vite)
├── deploy/                   # 部署配置
│   ├── local/               # Docker Compose 配置
│   ├── k8s/                 # Kubernetes Helm Charts
│   └── dockerfiles/         # Dockerfile
├── tests/                    # 测试用例
│   ├── unit/                # 单元测试（按角色分类）
│   ├── integration/         # 集成测试
│   └── e2e/                 # 端到端测试 (Playwright)
├── docs/                     # 项目文档
├── memory/                   # 记忆系统
├── release/                  # 发布产物
└── scripts/                  # 运维脚本
```

### 3.2 前端结构 (web/)

```
web/
├── src/
│   ├── pages/               # 页面组件
│   │   ├── data/           # 数据管理页面
│   │   ├── agent/          # Agent 页面
│   │   ├── model/          # 模型页面
│   │   ├── admin/          # 管理后台
│   │   └── portal/         # 门户页面
│   ├── components/          # 通用组件
│   ├── hooks/               # 自定义 Hooks
│   ├── services/            # API 服务
│   ├── stores/              # Zustand 状态管理
│   └── utils/               # 工具函数
├── package.json
└── vite.config.ts
```

### 3.3 后端结构 (services/)

每个服务遵循相同的结构：

```
services/{service-name}/
├── app.py                   # Flask/FastAPI 应用入口
├── config.py                # 配置管理
├── routes/                  # API 路由
├── models/                  # 数据模型
├── services/                # 业务逻辑
├── utils/                   # 工具函数
├── tests/                   # 服务测试
└── requirements.txt         # Python 依赖
```

---

## 四、服务清单

### 4.1 后端服务状态

| 服务 | 状态 | 框架 | 文件数 | 代码行数 | 说明 |
|------|------|------|--------|----------|------|
| data-api | ✅ 生产就绪 | Flask | 90 | 69,054 | 数据治理核心服务 |
| agent-api | ✅ 生产就绪 | Flask | 56 | 23,462 | Agent 编排服务 |
| model-api | ✅ 生产就绪 | Flask | 24 | 10,304 | MLOps 模型管理 |
| admin-api | ✅ 生产就绪 | Flask | 25 | 10,316 | 管理后台 API |
| openai-proxy | ✅ 生产就绪 | FastAPI | 1 | 890 | OpenAI 兼容代理 |
| ocr-service | ✅ 已完成 | FastAPI | 33 | 11,503 | OCR 文档识别 |
| behavior-service | ✅ 已完成 | FastAPI | 11 | 3,058 | 用户行为分析 |
| shared | ✅ 生产就绪 | - | 62 | ~90,000 | 共享模块 |

### 4.2 核心依赖

**后端**:
- Flask / FastAPI - Web 框架
- SQLAlchemy - ORM
- Redis - 缓存
- PostgreSQL / MySQL - 数据库
- Milvus - 向量数据库

**前端**:
- React 18.3.1 - UI 框架
- TypeScript 5.x - 类型安全
- Ant Design 5.14.0 - UI 组件库
- Zustand 4.5.0 - 状态管理
- TanStack Query 5.24.0 - 数据获取

---

## 五、API 端点

### 5.1 Data API (端口 5001)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/datasets` | GET/POST | 数据集管理 |
| `/api/v1/datasources` | GET/POST | 数据源管理 |
| `/api/v1/metadata` | GET | 元数据查询 |
| `/api/v1/etl/jobs` | GET/POST | ETL 任务管理 |
| `/api/v1/quality/rules` | GET/POST | 数据质量规则 |
| `/api/v1/health` | GET | 健康检查 |

### 5.2 Agent API (端口 5002)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/workflows` | GET/POST | 工作流管理 |
| `/api/v1/workflows/<id>/execute` | POST | 执行工作流 |
| `/api/v1/prompts/templates` | GET | Prompt 模板 |
| `/api/v1/knowledge/documents` | POST/GET | 知识库文档 |
| `/api/v1/collections` | GET | 向量集合 |
| `/api/v1/health` | GET | 健康检查 |

### 5.3 OpenAI Proxy (端口 8000)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/v1/models` | GET | 模型列表 |
| `/v1/chat/completions` | POST | 聊天补全 |
| `/v1/embeddings` | POST | 向量嵌入 |
| `/health` | GET | 健康检查 |

---

## 六、测试覆盖

### 6.1 测试文件统计

| 测试类型 | 文件数 | 说明 |
|----------|--------|------|
| 单元测试 | 87+ | 按角色分类 |
| 集成测试 | 24 | 服务间集成 |
| E2E 测试 (Playwright) | 41 | 前端 E2E |
| 性能测试 | 5 | 压力测试 |

### 6.2 测试规范

完整的测试规范位于 `docs/04-testing/test-specs/`，覆盖 321 个功能：

| 领域 | 功能数 |
|------|--------|
| 数据接入 | 20 |
| 数据处理 | 52 |
| 数据治理 | 112 |
| 监控运维 | 47 |
| 数据利用 | 55 |
| 平台支撑 | 35 |
| **总计** | **321** |

### 6.3 运行测试

```bash
# Python 测试
pytest tests/

# E2E 测试
npx playwright test

# 按优先级运行
pytest tests/ -m p0 -v
```

---

## 七、部署配置

### 7.1 本地开发

```bash
# Docker Compose 启动
docker-compose -f deploy/local/docker-compose.yml up -d

# 前端开发服务器
cd web && npm install && npm run dev
```

### 7.2 生产部署

```bash
# Kubernetes 部署
helm install one-data-studio deploy/k8s/charts/one-data-studio \
  -f deploy/k8s/charts/one-data-studio/values-production.yaml
```

### 7.3 环境变量

关键环境变量配置在 `deploy/local/.env.example`：

- `AUTH_MODE`: 认证模式 (true/false)
- `DATABASE_URL`: 数据库连接
- `REDIS_URL`: Redis 连接
- `MILVUS_HOST`: Milvus 地址
- `OPENAI_API_BASE`: OpenAI API 地址

---

## 八、当前进度

### 8.1 完成度矩阵

| 模块 | 完成度 | 说明 |
|------|--------|------|
| 后端服务 | 100% | 8个核心服务全部完成 |
| 前端应用 | 95% | 主要功能完成 |
| 部署配置 | 100% | 生产就绪 |
| 测试覆盖 | 93% | DataOps E2E 完成 |
| 代码质量 | 98% | 认证模块已统一 |

### 8.2 最近完成 (2026-02)

| 日期 | 工作内容 |
|------|----------|
| 2026-02-12 | 文档整理，移动 test-specs 到正确位置 |
| 2026-02-09 | 认证模块统一，console.log 清理 |
| 2026-02-09 | DataOps 功能测试规范 (321 功能) |
| 2026-02-08 | DataOps E2E 全流程测试 |
| 2026-02-07 | 用户生命周期测试，OCR 验证 |

### 8.3 三层集成完成度

| 集成方向 | 完成度 | 说明 |
|----------|--------|------|
| Data → Model | 90% | 数据集注册、MinIO 集成 |
| Model → Agent | 85% | OpenAI 兼容 API、流式响应 |
| Data → Agent | 75% | Text2SQL、元数据查询 |

---

## 九、技术债务

### 9.1 已清理

| 项目 | 完成日期 |
|------|----------|
| 认证模块统一 | 2026-02-09 |
| console.log 清理 | 2026-02-09 |
| 向量检索功能改进 | 2026-02-04 |
| 分阶段测试计划 | 2026-02-04 |

### 9.2 待改进

| 优先级 | 功能 | 位置 |
|--------|------|------|
| P1 | 工作流编辑器完善 | `web/src/pages/workflows/` |
| P1 | 模型热切换 | `services/openai-proxy/` |
| P2 | 数据集版本控制 | `services/data-api/` |
| P2 | 自动触发训练 | `services/model-api/` |

---

## 十、开发规范

### 10.1 代码风格

- **不可变性优先**: 始终创建新对象，永不突变
- **小文件组织**: 200-400 行典型，800 行最大
- **类型安全**: 显式类型，运行时与编译时契约一致
- **声明式配置**: 减少分支，数据驱动

### 10.2 文档规范

- 中文交流与文档
- 代码使用英文
- 进度保存到 `/docs/progress/`
- 完成报告保存到 `/docs/reports/completed/`

### 10.3 测试规范

- TDD 强制: 先写测试
- 80%+ 覆盖率目标
- 按优先级标记 (p0/p1/p2)

---

## 十一、关键文件路径

### 11.1 配置文件

| 文件 | 用途 |
|------|------|
| `deploy/local/docker-compose.yml` | 本地开发环境 |
| `deploy/local/.env.example` | 环境变量模板 |
| `web/vite.config.ts` | 前端构建配置 |
| `playwright.config.ts` | E2E 测试配置 |

### 11.2 核心代码

| 文件 | 用途 |
|------|------|
| `services/shared/auth/` | 统一认证模块 |
| `services/data-api/app.py` | 数据 API 入口 |
| `services/agent-api/app.py` | Agent API 入口 |
| `web/src/App.tsx` | 前端入口 |

### 11.3 记忆系统

| 文件 | 用途 |
|------|------|
| `memory/MEMORY.md` | 长期记忆（结构化知识）|
| `memory/daily/YYYY-MM-DD.md` | 每日笔记（工作日志）|

---

## 十二、快速启动指南

### 12.1 开发环境

```bash
# 1. 克隆项目
git clone <repo-url>
cd one-data-studio

# 2. 启动后端服务
docker-compose -f deploy/local/docker-compose.yml up -d

# 3. 启动前端
cd web && npm install && npm run dev

# 4. 访问应用
open http://localhost:5173
```

### 12.2 运行测试

```bash
# Python 测试
pytest tests/unit/ -v

# E2E 测试
npx playwright test --project=chromium

# P0 核心测试
pytest tests/ -m p0 -v
```

---

## 十三、注意事项

### 13.1 环境要求

- Docker 20.10+
- Node.js 18+
- Python 3.10+
- 16GB+ 内存（运行所有服务）

### 13.2 常见问题

1. **内存不足**: 使用分阶段测试，参考 `docs/07-operations/phased-testing-guide.md`
2. **认证失败**: 检查 `AUTH_MODE` 环境变量
3. **向量检索失败**: 确保 Milvus 服务运行

### 13.3 联系方式

- 项目文档: `/docs/`
- 技术债务: `/docs/TECH_DEBT.md`
- 项目状态: `/docs/PROJECT_STATUS.md`

---

> **文档生成**: 2026-02-12
> **维护者**: AI Assistant
