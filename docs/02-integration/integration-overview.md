# 核心模块集成方案

要让三个平台像一个平台一样工作，需要解决三个关键的"连接"问题。

## 三大集成点概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Bisheng (L4)                             │
│                    应用编排 | Agent | RAG                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    Text-to-SQL           模型 API 调用          向量检索
         │                     │                     │
         ↓                     ↓                     ↓
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Alldata (L2)  │──→│  Cube Studio    │──→│   Alldata       │
│  元数据/数仓    │   │   (L3)          │   │  向量数据库     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

## 集成点一：Alldata → Cube Studio

### 痛点
算法工程师通常需要花 80% 时间找数据、洗数据。

### 技术方案：统一存储协议与数据集版本化

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Alldata    │────→│  MinIO/HDFS │←────│ Cube Studio │
│  ETL 任务   │     │  数据湖存储 │     │  训练任务   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                      │
       │  注册数据集                          │  挂载数据
       ↓                                      ↓
┌─────────────────────────────────────────────────────┐
│              元数据中心 (API)                        │
│  数据路径 | 版本号 | Schema | 统计信息              │
└─────────────────────────────────────────────────────┘
```

### 实施步骤

1. Alldata 完成 ETL 任务后，将清洗后的数据（CSV/Parquet/TFRecord）写入对象存储（如 MinIO）
2. Alldata 调用 Cube Studio 的 API，自动注册一个"Dataset"对象
3. Cube Studio 的 Pipeline 中，用户直接通过 `mount` 方式或 SDK 读取该 Dataset

### API 示例

```python
# Alldata 侧：注册数据集
POST /api/v1/datasets
{
    "name": "sales_data_v1.0",
    "path": "s3://etl-output/sales/2024-01/",
    "format": "parquet",
    "schema": {...},
    "tags": ["sales", "cleansed"]
}

# Cube Studio 侧：使用数据集
from cube_sdk import Dataset
ds = Dataset.get("sales_data_v1.0")
df = ds.read()  # 自动挂载，直接读取
```

---

## 集成点二：Cube Studio → Bisheng

### 痛点
Bisheng 默认使用公有云 LLM，私有化部署需要稳定的本地模型 API。

### 技术方案：Model-as-a-Service (MaaS) 接口标准化

```
┌─────────────────────────────────────────────────────────┐
│                  Bisheng (L4)                           │
│                 应用编排层                               │
└────────────────────────┬────────────────────────────────┘
                         │ OpenAI 兼容 API
                         │ /v1/chat/completions
                         ↓
┌─────────────────────────────────────────────────────────┐
│               Cube Studio (L3)                          │
│         Istio Gateway → vLLM/TGI Pods                   │
│                                                         │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐               │
│    │  Pod 1  │  │  Pod 2  │  │  Pod N  │ (HPA 自动伸缩)│
│    └─────────┘  └─────────┘  └─────────┘               │
└─────────────────────────────────────────────────────────┘
```

### 实施步骤

1. Cube Studio 利用 **vLLM** 或 **TGI** 容器化部署微调好的模型
2. Cube Studio 通过 Istio 网关暴露 Service Endpoint
3. Bisheng 后台增加"自定义模型接入"配置
4. **弹性伸缩**：依靠 K8s HPA 自动增加推理 Pod

### 配置示例

```yaml
# Bisheng 模型配置
models:
  - name: "enterprise-llama"
    type: "openai-compatible"
    base_url: "http://cube-serving/v1"
    api_key: "${CUBE_API_KEY}"
    features: ["chat", "completion"]
```

---

## 集成点三：Alldata → Bisheng

### 痛点
大模型通常不懂企业的数据库表结构，无法准确查询业务数据。

### 技术方案：基于元数据的 Text-to-SQL

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   用户提问   │────→│   Bisheng    │────→│    LLM       │
│ "上月销售额?" │     │  SQL Agent   │     │  生成 SQL    │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            ↑
                            │ 获取元数据
                            ↓
                   ┌──────────────────┐
                   │    Alldata       │
                   │  元数据中心 API   │
                   │  表结构 | 注释    │
                   │  关联关系        │
                   └──────────────────┘
```

### 实施步骤

1. Alldata 管理企业数仓的**元数据**（表名、字段、注释、关联关系）
2. Bisheng 开发专用组件"SQL Agent"
3. 用户提问时，Bisheng 从 Alldata 获取相关表元数据，注入 Prompt
4. LLM 生成 SQL，回传给 Alldata 执行

### Prompt 模板

```
你是一个 SQL 专家。请根据以下表结构生成查询：

表：orders
- id (INT): 订单ID
- amount (DECIMAL): 订单金额
- created_at (DATETIME): 创建时间
- customer_id (INT): 客户ID

用户问题：{user_question}

请生成 SQL 查询：
```

---

## 集成顺序建议

| 阶段 | 集成点 | 优先级 | 说明 |
|------|--------|--------|------|
| 第一阶段 | Alldata → Cube | P0 | 数据是基础，先打通数据链路 |
| 第二阶段 | Cube → Bisheng | P0 | 模型服务是核心能力 |
| 第三阶段 | Alldata → Bisheng | P1 | Text-to-SQL 是增强功能 |
