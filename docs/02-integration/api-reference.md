# API 参考文档

ONE-DATA-STUDIO API 接口文档

## 目录

- [概述](#概述)
- [Data API](#data-api)
- [Agent API](#agent-api)
- [Model API](#model-api)
- [错误码](#错误码)

---

## 概述

### 基础 URL

| 服务 | 环境 | URL |
|------|------|-----|
| Data API | 开发 | http://localhost:8080 |
| Data API | 生产 | https://api.example.com/data |
| Agent API | 开发 | http://localhost:8081 |
| Agent API | 生产 | https://api.example.com/agent |
| Model API | 开发 | http://localhost:8000 |
| Model API | 生产 | https://api.example.com/model |

### 认证方式

API 使用 Bearer Token 认证：

```http
GET /api/v1/workflows
Authorization: Bearer your-access-token
```

### 请求头

| 头部 | 值 | 必需 |
|------|-----|------|
| Content-Type | application/json | 是（POST/PUT） |
| Authorization | Bearer {token} | 是（已认证接口） |
| X-Request-ID | {uuid} | 否 |

### 响应格式

成功响应：
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

错误响应：
```json
{
  "code": 40001,
  "message": "Invalid request",
  "details": { ... }
}
```

---

## Data API

### 数据集管理

#### 创建数据集

```http
POST /api/v1/datasets
Content-Type: application/json
```

**请求体**:
```json
{
  "name": "销售数据",
  "description": "2024年销售数据集",
  "storage_type": "s3",
  "storage_path": "s3://bucket/sales/",
  "format": "parquet",
  "tags": ["sales", "2024"],
  "row_count": 1000000,
  "size_bytes": 104857600
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "dataset_id": "ds-abc123"
  }
}
```

#### 获取数据集列表

```http
GET /api/v1/datasets?status=active&limit=20
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "dataset_id": "ds-abc123",
      "name": "销售数据",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 获取数据集详情

```http
GET /api/v1/datasets/{dataset_id}
```

#### 更新数据集

```http
PUT /api/v1/datasets/{dataset_id}
Content-Type: application/json
```

#### 删除数据集

```http
DELETE /api/v1/datasets/{dataset_id}
```

### 元数据管理

#### 获取数据库列表

```http
GET /api/v1/metadata/databases
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "databases": [
      {
        "name": "sales_dw",
        "tables_count": 15
      }
    ]
  }
}
```

#### 获取表列表

```http
GET /api/v1/metadata/databases/{database}/tables
```

#### 获取表详情

```http
GET /api/v1/metadata/databases/{database}/tables/{table}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "name": "orders",
    "columns": [
      {
        "name": "id",
        "type": "INT",
        "primary_key": true,
        "nullable": false
      }
    ]
  }
}
```

---

## Agent API

### 工作流管理

#### 创建工作流

```http
POST /api/v1/workflows
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "name": "客服助手工作流",
  "description": "基于 RAG 的智能客服",
  "type": "rag"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "workflow_id": "wf-xyz789"
  }
}
```

#### 获取工作流列表

```http
GET /api/v1/workflows
Authorization: Bearer {token}
```

#### 获取工作流详情

```http
GET /api/v1/workflows/{workflow_id}
Authorization: Bearer {token}
```

#### 更新工作流

```http
PUT /api/v1/workflows/{workflow_id}
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "name": "更新后的名称",
  "description": "更新后的描述",
  "definition": {
    "version": "1.0",
    "nodes": [...],
    "edges": [...]
  }
}
```

#### 删除工作流

```http
DELETE /api/v1/workflows/{workflow_id}
Authorization: Bearer {token}
```

### 工作流执行

#### 启动工作流

```http
POST /api/v1/workflows/{workflow_id}/start
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "inputs": {
    "query": "用户查询内容"
  }
}
```

**响应**:
```json
{
  "code": 0,
  "message": "Workflow started",
  "data": {
    "execution_id": "exec-123",
    "status": "running"
  }
}
```

#### 停止工作流

```http
POST /api/v1/workflows/{workflow_id}/stop
Content-Type: application/json
Authorization: Bearer {token}
```

#### 获取执行状态

```http
GET /api/v1/workflows/{workflow_id}/status?execution_id={execution_id}
Authorization: Bearer {token}
```

#### 获取执行日志

```http
GET /api/v1/executions/{execution_id}/logs
Authorization: Bearer {token}
```

### 聊天接口

#### 发送消息

```http
POST /api/v1/chat
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "message": "介绍一下这个平台",
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 2000,
  "conversation_id": "conv-123"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "reply": "ONE-DATA-STUDIO 是一个...",
    "conversation_id": "conv-123",
    "model": "gpt-4o-mini"
  }
}
```

### 文档管理

#### 上传文档

```http
POST /api/v1/documents/upload
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "content": "文档内容...",
  "file_name": "manual.pdf",
  "title": "用户手册",
  "collection": "knowledge-base"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "Document uploaded and indexed",
  "data": {
    "doc_id": "doc-abc123",
    "chunk_count": 25
  }
}
```

#### 列出文档

```http
GET /api/v1/documents?collection=knowledge-base
Authorization: Bearer {token}
```

#### 删除文档

```http
DELETE /api/v1/documents/{doc_id}
Authorization: Bearer {token}
```

### RAG 查询

```http
POST /api/v1/rag/query
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "question": "如何使用这个平台？",
  "collection": "knowledge-base",
  "top_k": 5
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "根据文档...",
    "sources": ["doc-abc123"],
    "retrieved_count": 3
  }
}
```

### Text-to-SQL

```http
POST /api/v1/text2sql
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "natural_language": "查询最近一周的订单",
  "database": "sales_dw",
  "selected_tables": ["orders", "customers"]
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "sql": "SELECT * FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
    "confidence": 0.85
  }
}
```

### Agent 工具

#### 列出可用工具

```http
GET /api/v1/tools
Authorization: Bearer {token}
```

#### 执行工具

```http
POST /api/v1/tools/{tool_name}/execute
Content-Type: application/json
Authorization: Bearer {token}
```

#### 运行 Agent

```http
POST /api/v1/agent/run
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "query": "帮我查询最新订单并生成报表",
  "agent_type": "react",
  "model": "gpt-4o-mini",
  "max_iterations": 10
}
```

### 会话管理

#### 获取会话列表

```http
GET /api/v1/conversations?limit=20
Authorization: Bearer {token}
```

#### 获取会话详情

```http
GET /api/v1/conversations/{conversation_id}
Authorization: Bearer {token}
```

#### 创建会话

```http
POST /api/v1/conversations
Content-Type: application/json
Authorization: Bearer {token}
```

#### 删除会话

```http
DELETE /api/v1/conversations/{conversation_id}
Authorization: Bearer {token}
```

### 工作流调度

#### 创建调度

```http
POST /api/v1/workflows/{workflow_id}/schedules
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "type": "cron",
  "cron_expression": "0 0 * * *",
  "enabled": true,
  "max_retries": 3,
  "timeout_seconds": 3600
}
```

#### 删除调度

```http
DELETE /api/v1/schedules/{schedule_id}
Authorization: Bearer {token}
```

#### 暂停/恢复调度

```http
POST /api/v1/schedules/{schedule_id}/pause
Authorization: Bearer {token}
```

```http
POST /api/v1/schedules/{schedule_id}/resume
Authorization: Bearer {token}
```

---

## Model API

OpenAI 兼容的模型服务接口。

### 获取模型列表

```http
GET /v1/models
Authorization: Bearer {token}
```

**响应**:
```json
{
  "data": [
    {
      "id": "gpt-4o-mini",
      "object": "model",
      "created": 1234567890,
      "owned_by": "organization"
    }
  ],
  "object": "list"
}
```

### 聊天补全

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "你是一个智能助手"},
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.7,
  "max_tokens": 2000,
  "stream": false
}
```

**响应**:
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！有什么可以帮助你的吗？"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 30,
    "total_tokens": 50
  }
}
```

### 嵌入向量

```http
POST /v1/embeddings
Content-Type: application/json
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "model": "text-embedding-ada-002",
  "input": "要生成嵌入向量的文本"
}
```

**响应**:
```json
{
  "data": [
    {
      "embedding": [0.1, 0.2, ...],
      "index": 0,
      "object": "embedding"
    }
  ],
  "model": "text-embedding-ada-002",
  "usage": {
    "prompt_tokens": 10,
    "total_tokens": 10
  }
}
```

---

## 错误码

### 通用错误码 (1xxxx)

| 错误码 | 描述 |
|--------|------|
| 0 | 成功 |
| 10001 | 未知错误 |
| 10002 | 无效请求 |
| 10003 | 缺少必需参数 |
| 10004 | 参数格式错误 |
| 10005 | 请求频率超限 |

### 认证授权错误 (2xxxx)

| 错误码 | 描述 |
|--------|------|
| 20001 | 未授权 |
| 20002 | Token 已过期 |
| 20003 | Token 无效 |
| 20004 | 用户不存在 |
| 20005 | 账户已被禁用 |

### 资源错误 (3xxxx)

| 错误码 | 描述 |
|--------|------|
| 30001 | 资源不存在 |
| 30002 | 资源已存在 |
| 30003 | 资源冲突 |
| 30004 | 资源被锁定 |

### 服务错误 (4xxxx)

| 错误码 | 描述 |
|--------|------|
| 40001 | 数据库错误 |
| 40002 | 存储错误 |
| 40003 | 向量数据库错误 |
| 40004 | 外部 API 错误 |
| 40005 | 超时错误 |

### 工作流错误 (5xxxx)

| 错误码 | 描述 |
|--------|------|
| 50001 | 工作流不存在 |
| 50002 | 工作流执行失败 |
| 50003 | 工作流验证失败 |
| 50004 | 节点执行失败 |
| 50005 | 调度错误 |

---

## SDK 使用示例

### Python SDK

```python
from one_data import AgentClient

# 初始化客户端
client = AgentClient(
    base_url="http://localhost:8081",
    api_key="your-api-key"
)

# 创建工作流
workflow = client.workflows.create(
    name="测试工作流",
    type="rag"
)

# 执行工作流
execution = workflow.start(inputs={"query": "测试"})

# 获取结果
result = execution.wait_for_completion()
print(result.output)
```

### JavaScript SDK

```typescript
import { AgentClient } from '@one-data/sdk';

const client = new AgentClient({
  baseUrl: 'http://localhost:8081',
  apiKey: 'your-api-key'
});

// 创建工作流
const workflow = await client.workflows.create({
  name: '测试工作流',
  type: 'rag'
});

// 发送聊天消息
const response = await client.chat.send({
  message: '你好',
  model: 'gpt-4o-mini'
});

console.log(response.data.reply);
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v2.1.0 | 2024-01 | Sprint 10 完成，性能优化、安全加固、监控运维 |
| v2.0.0 | 2024-01 | Sprint 8-9 更新，添加调度和 Agent API |
| v1.5.0 | 2023-12 | 添加文档管理和 RAG API |
| v1.0.0 | 2023-11 | 初始版本 |

---

## 附录：健康检查接口

### GET /api/v1/health

深度健康检查接口，返回所有依赖服务的连通性状态。

**响应示例（正常）：**
```json
{
  "code": 0,
  "message": "healthy",
  "service": "agent-api",
  "version": "2.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 2.5
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.2,
      "used_memory_mb": 45.3
    },
    "milvus": {
      "status": "healthy",
      "latency_ms": 5.8,
      "collection_count": 3
    },
    "data_api": {
      "status": "healthy",
      "latency_ms": 15.2
    },
    "model_api": {
      "status": "healthy",
      "latency_ms": 8.5
    }
  }
}
```

**响应示例（降级）：**
```json
{
  "code": 1,
  "message": "degraded",
  "service": "agent-api",
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 2.5
    },
    "redis": {
      "status": "unhealthy",
      "error": "Connection refused"
    }
  }
}
```

HTTP 状态码：
- 200: 所有核心服务健康
- 503: 核心服务（如数据库）不可用
