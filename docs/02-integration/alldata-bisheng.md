# Alldata 与 Bisheng 集成方案

## 集成目标

打通**数据底座**与**应用编排**之间的连接，实现：
- 基于元数据的 Text-to-SQL
- 向量知识库检索 (RAG)
- 结构化与非结构化数据统一查询

## 架构图

```
┌──────────────────────────────────────────────────────────────┐
│                       Bisheng (L4)                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    应用编排层                        │    │
│  │  ┌─────────────┐   ┌─────────────┐   ┌───────────┐ │    │
│  │  │ SQL Agent   │   │ RAG Agent   │   │ 用户输入  │ │    │
│  │  └──────┬──────┘   └──────┬──────┘   └─────┬─────┘ │    │
│  └─────────┼──────────────────┼────────────────┼────────┘    │
└────────────┼──────────────────┼────────────────┼─────────────┘
             │                  │                │
        元数据查询          向量检索          SQL 执行
             │                  │                │
             ↓                  ↓                ↓
┌──────────────────────────────────────────────────────────────┐
│                       Alldata (L2)                           │
│  ┌─────────────┐   ┌─────────────┐   ┌───────────────────┐  │
│  │ 元数据中心   │   │ 向量数据库  │   │   业务数仓        │  │
│  │  (Metadata) │   │ (Vector DB) │   │  (Doris/Hive)    │  │
│  └─────────────┘   └─────────────┘   └───────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## 核心场景

### 场景一：Text-to-SQL（结构化数据查询）

```mermaid
sequenceDiagram
    participant User as 用户
    participant Bisheng as Bisheng SQL Agent
    participant Meta as Alldata 元数据中心
    participant LLM as LLM
    participant DW as 业务数仓

    User->>Bisheng: "上个月销售额是多少？"
    Bisheng->>Meta: 获取相关表元数据
    Meta-->>Bisheng: 返回表结构 (sales, orders)
    Bisheng->>LLM: 生成 SQL (带 Schema 上下文)
    LLM-->>Bisheng: SELECT sum(amount) FROM sales...
    Bisheng->>DW: 执行 SQL
    DW-->>Bisheng: 返回查询结果
    Bisheng-->>User: "上个月销售额为 500 万"
```

### 场景二：RAG 检索（非结构化知识）

```mermaid
sequenceDiagram
    participant User as 用户
    participant Bisheng as Bisheng RAG Agent
    participant VectorDB as Alldata 向量库
    participant LLM as LLM

    User->>Bisheng: "销售政策有什么变化？"
    Bisheng->>VectorDB: 向量检索相似文档
    VectorDB-->>Bisheng: 返回相关文档片段
    Bisheng->>LLM: 生成回答 (RAG)
    LLM-->>Bisheng: 返回自然语言回答
    Bisheng-->>User: "根据最新政策..."
```

### 场景三：混合查询（RAG + SQL）

```mermaid
sequenceDiagram
    participant User as 用户
    participant Bisheng as Bisheng 编排器
    participant SQLAgent as SQL Agent
    participant RAGAgent as RAG Agent
    participant Meta as 元数据中心
    participant VectorDB as 向量库
    participant LLM as LLM

    User->>Bisheng: "分析上月销售下滑原因"
    Bisheng->>SQLAgent: 查询销售数据
    SQLAgent->>Meta: 获取表结构
    SQLAgent->>LLM: 生成 SQL
    Note over SQLAgent: 获取数据: -15%

    Bisheng->>RAGAgent: 检索相关政策
    RAGAgent->>VectorDB: 向量检索
    Note over RAGAgent: 获取政策文档

    Bisheng->>LLM: 综合分析 (数据+文档)
    LLM-->>Bisheng: "销售下滑15%，主要原因是..."
    Bisheng-->>User: 返回分析结果
```

## API 规范

### 元数据查询接口

```http
GET /api/v1/metadata/tables?keywords=sales,orders
Accept: application/json

{
  "tables": [
    {
      "database": "business_db",
      "table": "sales",
      "description": "销售事实表",
      "columns": [
        {
          "name": "order_id",
          "type": "bigint",
          "comment": "订单ID",
          "nullable": false
        },
        {
          "name": "amount",
          "type": "decimal(18,2)",
          "comment": "订单金额",
          "nullable": false
        },
        {
          "name": "order_date",
          "type": "date",
          "comment": "订单日期",
          "nullable": false
        }
      ],
      "relations": [
        {
          "type": "foreign_key",
          "ref_table": "customers",
          "ref_column": "customer_id"
        }
      ],
      "sample_data": [
        {"order_id": 1, "amount": 100.00, "order_date": "2024-01-01"}
      ]
    }
  ]
}
```

### SQL 执行接口

```http
POST /api/v1/query/execute
Content-Type: application/json

{
  "sql": "SELECT sum(amount) as total FROM sales WHERE order_date >= '2024-01-01'",
  "database": "business_db",
  "timeout": 30,
  "limit": 10000
}

{
  "success": true,
  "data": [
    {"total": 5000000.00}
  ],
  "rows": 1,
  "duration_ms": 125
}
```

### 向量检索接口

```http
POST /api/v1/vector/search
Content-Type: application/json

{
  "query": "销售政策有哪些变化",
  "collection": "enterprise_docs",
  "top_k": 5,
  "filters": {
    "doc_type": "policy",
    "date": ">= 2024-01-01"
  }
}

{
  "results": [
    {
      "id": "doc_001",
      "content": "2024年销售政策更新：...",
      "metadata": {
        "doc_type": "policy",
        "title": "2024年销售政策",
        "date": "2024-01-15"
      },
      "score": 0.92
    }
  ]
}
```

## Text-to-SQL 实现

### Prompt 模板

```python
TEXT_TO_SQL_PROMPT = """
你是一个 SQL 专家。请根据以下信息生成 SQL 查询。

## 可用表结构

{table_schemas}

## 表关联关系

{table_relations}

## 用户问题

{user_question}

## 要求

1. 只返回 SQL 语句，不要解释
2. 使用标准 SQL 语法
3. 如果需要 JOIN，请在 WHERE 子句中明确关联条件
4. 注意日期格式的处理

## SQL 查询

```sql
"""
```

### 代码示例

```python
from bisheng.agents import SQLAgent
from alldata_client import MetadataClient, QueryClient

class AlldataSQLAgent(SQLAgent):
    def __init__(self):
        self.metadata_client = MetadataClient()
        self.query_client = QueryClient()
        self.llm = self.get_llm()

    def query(self, question: str) -> str:
        # 1. 获取相关表元数据
        tables = self.metadata_client.search_tables(question)

        # 2. 构建 Prompt
        prompt = self.build_prompt(question, tables)

        # 3. 生成 SQL
        sql = self.llm.generate(prompt)

        # 4. 执行查询
        result = self.query_client.execute(sql)

        # 5. 自然语言解释
        answer = self.llm.explain(result, question)

        return answer
```

## RAG 实现

### 代码示例

```python
from bisheng.agents import RAGAgent
from alldata_client import VectorClient

class AldataRAGAgent(RAGAgent):
    def __init__(self):
        self.vector_client = VectorClient()
        self.llm = self.get_llm()

    def query(self, question: str) -> str:
        # 1. 向量检索
        docs = self.vector_client.search(
            query=question,
            collection="enterprise_docs",
            top_k=5
        )

        # 2. 构建 RAG Prompt
        context = "\n".join([d["content"] for d in docs])
        prompt = f"""
参考以下文档回答问题：

{context}

问题：{question}

回答：
"""

        # 3. 生成回答
        answer = self.llm.generate(prompt)

        return answer
```

## 配置清单

### Bisheng 配置

```yaml
# config/alldata_integration.yaml
alldata:
  enabled: true
  api_endpoint: http://alldata-api.default.svc.cluster.local
  api_key: ${ALDATA_API_KEY}
  timeout: 30

  metadata:
    enabled: true
    cache_ttl: 3600

  query:
    enabled: true
    max_rows: 10000
    timeout: 30

  vector:
    enabled: true
    endpoint: http://alldata-vector.default.svc.cluster.local
    top_k: 5
```

### 元数据同步配置

```yaml
# Alldata 侧配置
bisheng_integration:
  metadata_sync:
    enabled: true
    sync_interval: 300s
    include_databases:
      - business_db
      - warehouse_db
    exclude_tables:
      - temp_*
      - test_*
```

## 测试用例

```python
def test_text_to_sql():
    agent = AlldataSQLAgent()
    result = agent.query("上个月销售额是多少？")
    assert "500万" in result

def test_rag():
    agent = AldataRAGAgent()
    result = agent.query("销售政策有什么变化？")
    assert len(result) > 0

def test_hybrid_query():
    agent = HybridAgent()
    result = agent.query("分析上月销售下滑原因")
    assert "原因" in result
```

## 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| SQL 语法错误 | Schema 信息不完整 | 检查元数据注册完整性 |
| 检索结果不相关 | 向量模型不适配 | 针对领域数据微调 Embedding 模型 |
| 查询超时 | 数据量大 | 添加查询限制，优化索引 |
