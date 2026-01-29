# Bisheng API

大模型应用开发平台 API 服务。

## 功能

- 聊天接口（集成 LLM）
- RAG 查询
- 工作流管理与执行
- 会话管理
- Text-to-SQL 生成
- Agent 工具注册与调用
- 工作流调度
- JWT 认证授权

## 配置

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接 URL | *必需* |
| `CUBE_API_URL` | Cube API 地址 | `http://vllm-serving:8000` |
| `ALDATA_API_URL` | Alldata API 地址 | `http://alldata-api:8080` |
| `MILVUS_HOST` | Milvus 向量库地址 | `localhost` |
| `MILVUS_PORT` | Milvus 端口 | `19530` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | *可选* |
| `AUTH_MODE` | 是否启用认证 | `true` |
| `JWT_SECRET_KEY` | JWT 密钥 | *必需* |
| `PORT` | 服务端口 | `8081` |

## 可选依赖

### 数据库驱动

根据工作流中使用的数据库节点类型，需要安装相应的驱动：

```bash
# PostgreSQL 异步支持（用于 database.py 异步连接）
pip install asyncpg

# MySQL 异步支持（用于 database.py, tools.py 异步连接）
pip install aiomysql

# 同步驱动（通常已随 SQLAlchemy 安装）
pip install psycopg2-binary  # PostgreSQL
pip install pymysql          # MySQL
```

如未安装可选驱动，相关数据库节点将返回友好错误提示，不会导致服务崩溃。

### 向量库驱动

```bash
# Milvus 向量库支持
pip install pymilvus>=2.3.0
```

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行服务
python app.py

# 运行测试
pytest tests/
```

## API 端点

### 聊天
- `POST /api/v1/chat/completions` - 聊天补全
- `POST /api/v1/chat/rag` - RAG 增强聊天

### 工作流
- `GET /api/v1/workflows` - 列出工作流
- `POST /api/v1/workflows` - 创建工作流
- `GET /api/v1/workflows/{id}` - 获取工作流详情
- `POST /api/v1/workflows/{id}/execute` - 执行工作流
- `POST /api/v1/workflows/{id}/stop` - 停止执行

### 会话
- `GET /api/v1/conversations` - 列出会话
- `POST /api/v1/conversations` - 创建会话
- `GET /api/v1/conversations/{id}/messages` - 获取消息

### Agent
- `GET /api/v1/tools` - 列出可用工具
- `POST /api/v1/tools/{name}/execute` - 执行工具

### 调度
- `GET /api/v1/schedules` - 列出调度
- `POST /api/v1/schedules` - 创建调度
