# 系统时序图

本文档包含两个核心场景的详细时序图，展示 Alldata、Cube Studio 和 Bisheng 三者如何协同工作。

---

## 场景一：研发态（Build Phase）

**数据清洗与模型生产流水线**

这个流程展示了数据工程师和算法工程师如何协作，将原始数据转化为可用的模型服务。

```mermaid
sequenceDiagram
    autonumber
    actor DataEng as 数据工程师
    actor AlgoEng as 算法工程师

    box "Alldata (数据治理平台)" #e1f5fe
        participant AD_ETL as ETL/数据开发
        participant AD_Meta as 元数据中心
    end

    box "存储基础设施" #eeeeee
        participant Storage as MinIO/HDFS (数据湖)
        participant VectorDB as 向量数据库
    end

    box "Cube Studio (AI中台)" #e8f5e9
        participant Cube_NB as Notebook/开发环境
        participant Cube_Job as 训练任务(K8s)
        participant Cube_Serving as 模型服务(API)
    end

    %% --- 阶段1：数据准备 ---
    DataEng->>AD_ETL: 1. 定义数据清洗任务 (ETL)
    AD_ETL->>Storage: 2. 抽取并清洗原始数据
    AD_ETL->>Storage: 3. 写入标准训练数据集 (Parquet/JSONL)
    AD_ETL->>VectorDB: 4. (可选) 文档数据向量化入库
    AD_ETL->>AD_Meta: 5. 注册数据集元数据 (版本v1.0)

    %% --- 阶段2：模型开发与微调 ---
    AlgoEng->>Cube_NB: 6. 启动开发环境
    Cube_NB->>AD_Meta: 7. 查询可用数据集路径
    AD_Meta-->>Cube_NB: 返回 S3/HDFS 路径

    Cube_NB->>Cube_Job: 8. 提交分布式微调任务 (Fine-tuning)
    activate Cube_Job
    Cube_Job->>Storage: 9. 挂载/读取清洗后的数据
    Cube_Job->>Cube_Job: 10. 执行训练 (LoRA/Full)
    Cube_Job->>Storage: 11. 保存模型权重文件
    deactivate Cube_Job

    %% --- 阶段3：模型服务化 ---
    AlgoEng->>Cube_Serving: 12. 一键部署模型 (Model Deploy)
    Cube_Serving->>Storage: 13. 加载模型权重
    Cube_Serving-->>AlgoEng: 14. 返回 API Endpoint (OpenAI兼容接口)
```

### 流程解析

**阶段1：数据准备 (步骤 1-5)**
- **Alldata** 负责把"脏数据"变成"标准数据"并入库（MinIO 或 向量库）
- **Alldata** 将数据位置通知给元数据中心，打破数据与算法的壁垒

**阶段2：模型开发与微调 (步骤 6-11)**
- **Cube Studio** 直接消费 Alldata 产出的数据进行训练
- 训练任务自动挂载存储，无需手动下载数据
- 模型权重保存回共享存储

**阶段3：模型服务化 (步骤 12-14)**
- 一键部署模型为 API 服务
- 暴露 OpenAI 兼容接口供上层应用调用

---

## 场景二：运行态（Run Phase）

**智能应用交互 (RAG + Text-to-SQL)**

这个流程展示了最终用户如何在 Bisheng 构建的应用中，同时利用非结构化知识（RAG）和结构化数据（SQL）。

```mermaid
sequenceDiagram
    autonumber
    actor User as 业务用户

    box "Bisheng (应用编排平台)" #fff3e0
        participant App_Flow as 应用流程编排
        participant Agent_SQL as SQL Agent
        participant Agent_RAG as RAG 检索器
    end

    box "Alldata (数据资产)" #e1f5fe
        participant VectorDB as 向量数据库 (知识)
        participant DataWarehouse as 业务数仓 (Doris/Hive)
    end

    box "Cube Studio (算力引擎)" #e8f5e9
        participant LLM_API as 私有大模型 API
    end

    %% --- 用户提问 ---
    User->>App_Flow: 1. 提问: "查询上个月销售额，并结合《销售政策》分析原因"

    %% --- 分支A：结构化数据查询 (Text-to-SQL) ---
    App_Flow->>Agent_SQL: 2. 路由请求: 提取"上个月销售额"
    Agent_SQL->>LLM_API: 3. 发送Schema+问题，请求生成SQL
    LLM_API-->>Agent_SQL: 返回: SELECT sum(sales) ...
    Agent_SQL->>DataWarehouse: 4. 执行 SQL 查询
    DataWarehouse-->>Agent_SQL: 返回结果: "500万"

    %% --- 分支B：非结构化知识检索 (RAG) ---
    App_Flow->>Agent_RAG: 5. 路由请求: 提取"销售政策"相关
    Agent_RAG->>VectorDB: 6. 向量检索相似文档块
    VectorDB-->>Agent_RAG: 返回: "政策文档片段A, 片段B..."

    %% --- 最终合成 ---
    App_Flow->>LLM_API: 7. 组装最终 Prompt (用户问题 + SQL结果 + 文档片段)
    Note right of App_Flow: Prompt: "已知销售额500万，政策如下...请分析原因"
    LLM_API-->>App_Flow: 8. 生成最终自然语言回答
    App_Flow-->>User: 9. 回复: "上月销售额500万。根据政策..."
```

### 流程解析

**用户提问 (步骤 1)**
- 用户提出复杂的混合问题，涉及数据查询和知识检索

**分支A：结构化数据查询 (步骤 2-4)**
- **Agent_SQL** 负责处理数值查询部分
- 调用 **LLM_API** 生成 SQL（注入元数据 Schema）
- 在 **DataWarehouse** 中执行查询获取结果

**分支B：非结构化知识检索 (步骤 5-6)**
- **Agent_RAG** 负责处理文档知识部分
- 在 **VectorDB** 中进行向量相似度检索

**最终合成 (步骤 7-9)**
- **App_Flow** 整合 SQL 结果和检索到的文档片段
- 组装完整 Prompt 调用 **LLM_API** 生成最终回答
- 返回给用户自然语言的分析结果

---

## 价值链总结

通过这两个时序图可以看出：

1. **Alldata 是"供货商"**：保证原材料（数据）的质量和供给。
2. **Cube Studio 是"加工厂"**：提供机器（算力）和工艺（模型），把原材料变成能力（API）。
3. **Bisheng 是"零售商"**：把能力包装成产品（App），直接服务消费者（用户）。

这种架构实现了**数据流、模型流、业务流**的完美闭环。

---

## 场景三：数据全生命周期（Full Data Lifecycle）

**从基础设施到智能应用的完整数据旅程**

这个流程展示了数据从底层基础设施（L1）经过数据治理（L2）、算法推理（L3）到应用编排（L4）的完整生命周期。涵盖八个阶段：数据源接入、元数据发现、敏感识别、ETL加工、元数据同步、资产评估、知识索引、智能查询。

```mermaid
sequenceDiagram
    autonumber
    actor User as 用户

    box "L4 应用编排层 (Bisheng)" #fff3e0
        participant Web as 前端(React)
        participant Bisheng as Bisheng API
        participant Agent as Agent引擎
    end

    box "L3 算法引擎层 (Cube Studio)" #e8f5e9
        participant vLLM as vLLM 推理服务
    end

    box "L2 数据底座层 (Alldata)" #e1f5fe
        participant Alldata as Alldata API
        participant Kettle as Kettle ETL引擎
    end

    box "元数据治理" #f3e5f5
        participant OM as OpenMetadata
    end

    box "L1 基础设施层" #eeeeee
        participant MySQL as MySQL
        participant MinIO as MinIO(S3)
        participant Milvus as Milvus(向量库)
        participant ES as Elasticsearch
        participant Redis as Redis
    end

    %% ================================================================
    %% 阶段一：数据源接入与元数据发现
    %% ================================================================
    rect rgb(227, 242, 253)
    Note over User,Redis: 阶段一：数据源接入与元数据自动发现

    User->>Web: 注册业务数据源
    Web->>Alldata: POST /api/v1/datasources
    Alldata->>MySQL: 测试连接 & 持久化配置
    MySQL-->>Alldata: DataSource 创建成功
    Alldata-->>Web: 返回 datasource_id

    User->>Web: 启动元数据自动扫描
    Web->>Alldata: POST /api/v1/metadata/auto-scan
    activate Alldata
    Note right of Alldata: MetadataAutoScanEngine

    Alldata->>MySQL: SELECT FROM INFORMATION_SCHEMA.TABLES
    MySQL-->>Alldata: 返回 50 张表结构

    Alldata->>MySQL: SELECT FROM INFORMATION_SCHEMA.COLUMNS
    MySQL-->>Alldata: 返回 1200 列定义

    Note right of Alldata: AI标注阶段
    Alldata->>Alldata: 规则匹配列名<br/>(id→主键, created_at→创建时间)
    Alldata->>vLLM: POST /v1/chat/completions<br/>请求AI标注表/列业务描述
    vLLM-->>Alldata: 返回AI描述

    Alldata->>MySQL: 批量保存<br/>MetadataDatabase / MetadataTable / MetadataColumn
    deactivate Alldata
    Alldata-->>Web: 扫描完成 (50表, 1200列已标注)
    end

    %% ================================================================
    %% 阶段二：敏感数据自动识别
    %% ================================================================
    rect rgb(255, 243, 224)
    Note over User,Redis: 阶段二：敏感数据自动识别

    User->>Web: 启动敏感数据扫描
    Web->>Alldata: POST /api/v1/sensitivity/scan/start
    activate Alldata
    Note right of Alldata: SensitivityAutoScanService

    Alldata->>MySQL: 加载全部 MetadataColumn
    MySQL-->>Alldata: 返回 1200 列

    loop 逐列扫描
        Alldata->>Alldata: 1. 正则匹配列名模式<br/>(phone/email/id_card/bank_card...)
        Alldata->>MySQL: 2. SELECT TOP 200 采样数据
        MySQL-->>Alldata: 返回样本值
        Alldata->>Alldata: 3. 内容正则匹配<br/>match_rate > 30% → 标记敏感
    end

    Alldata->>Alldata: 计算置信度<br/>confidence = 60 + match_rate × 30

    Alldata->>MySQL: 更新 MetadataColumn<br/>sensitivity_type = pii/financial/credential<br/>sensitivity_level = confidential/restricted

    Alldata->>MySQL: 自动生成 MaskingRule<br/>(手机→partial_mask, 身份证→id_card_mask...)
    deactivate Alldata
    Alldata-->>Web: 扫描完成 (PII:15列, 金融:8列, 凭证:3列)
    end

    %% ================================================================
    %% 阶段三：智能ETL编排与数据加工
    %% ================================================================
    rect rgb(232, 245, 233)
    Note over User,Redis: 阶段三：智能ETL编排与数据加工

    User->>Web: 创建ETL编排任务
    Web->>Alldata: POST /api/v1/kettle/orchestrate
    activate Alldata
    Note right of Alldata: KettleOrchestrationService

    Note right of Alldata: ▶ 分析阶段 (ANALYZING)
    Alldata->>MySQL: 查询源表结构 + 敏感标记 + NULL统计
    MySQL-->>Alldata: 列定义 / NULL率 / 敏感类型

    Note right of Alldata: ▶ AI推荐阶段 (RECOMMENDING)
    Alldata->>vLLM: POST /v1/chat/completions<br/>请求清洗规则推荐
    vLLM-->>Alldata: 返回清洗建议<br/>(去NULL/去重/格式标准化/异常值处理)

    Alldata->>Alldata: AIImputationService:<br/>缺失模式分析 (random/block/systematic)<br/>推荐填充策略 (均值/中位数/KNN/前向填充)

    Alldata->>Alldata: DataMaskingService:<br/>生成脱敏配置<br/>(手机:138****1234, 身份证:110101****1234<br/>银行卡:6222****1234, 邮箱:t***@domain)

    Note right of Alldata: ▶ 生成阶段 (GENERATING)
    Alldata->>Alldata: KettleAIIntegrator 转换规则→XML步骤:<br/>清洗→IfFieldValueIsNull/FilterRows<br/>填充→AnalyticQuery(LAG/LEAD)/DBLookup<br/>脱敏→ScriptValueMod(JavaScript)

    Note right of Alldata: ▶ 执行阶段 (EXECUTING)
    Alldata->>Kettle: 提交 Kettle 转换XML
    activate Kettle

    Kettle->>MySQL: TableInput: 读取源数据
    Kettle->>Kettle: Step1: 数据清洗<br/>(NULL处理/去重/格式化)
    Kettle->>Kettle: Step2: 缺失值填充<br/>(AnalyticQuery/StreamLookup)
    Kettle->>Kettle: Step3: 数据脱敏<br/>(ScriptValueMod: AES/SHA256/正则)
    Kettle->>MySQL: TableOutput: 写入目标表
    deactivate Kettle
    Kettle-->>Alldata: 执行报告 (处理行数/耗时/成功率)

    Alldata->>MinIO: 存储ETL产出数据集 (Parquet/CSV)
    MinIO-->>Alldata: 返回 S3 presigned URL
    deactivate Alldata
    Alldata-->>Web: ETL编排完成
    end

    %% ================================================================
    %% 阶段四：元数据同步与数据血缘
    %% ================================================================
    rect rgb(243, 229, 245)
    Note over User,Redis: 阶段四：元数据同步与数据血缘追踪

    User->>Web: 同步元数据到 OpenMetadata
    Web->>Alldata: POST /api/v1/openmetadata/sync
    activate Alldata
    Note right of Alldata: MetadataSyncService

    Alldata->>OM: GET /services/databaseServices/name/alldata-service
    OM-->>Alldata: 404 (不存在)
    Alldata->>OM: POST /services/databaseServices<br/>创建 alldata-service (MySQL类型)
    OM->>MySQL: 持久化服务注册
    OM->>ES: 索引服务元数据
    OM-->>Alldata: 服务创建成功

    loop 逐表同步 (50张表)
        Alldata->>Alldata: 类型映射 (varchar→VARCHAR, int→INT...)<br/>敏感性标签转换 (pii→PersonalData Tag)<br/>合并AI描述到description
        Alldata->>OM: POST /tables<br/>{name, databaseSchema, columns[], tags[], description}
        OM->>MySQL: 持久化表+列元数据
        OM->>ES: 全文索引 (支持搜索)
        OM-->>Alldata: FQN: alldata-service.{db}.{table}
    end

    Note right of Alldata: ▶ 血缘推送 (OpenLineageService)
    Alldata->>Alldata: 提取ETL任务的<br/>source_tables[] → target_tables[]
    Alldata->>OM: PUT /lineage<br/>{fromEntity: source_fqn, toEntity: target_fqn}<br/>附带 transformation SQL
    OM->>MySQL: 存储血缘边 (DAG图)
    OM-->>Alldata: 血缘创建成功
    deactivate Alldata
    Alldata-->>Web: 同步完成 (synced:50, lineage:23条边)
    end

    %% ================================================================
    %% 阶段五：资产编目与价值评估
    %% ================================================================
    rect rgb(255, 253, 231)
    Note over User,Redis: 阶段五：数据资产编目与价值评估

    User->>Web: 自动编目 + 评估资产价值
    Web->>Alldata: POST /api/v1/assets/auto-catalog
    Alldata->>MySQL: 查询已治理的 MetadataTable 列表
    MySQL-->>Alldata: 返回50张表
    Alldata->>Alldata: 自动生成 DataAsset 记录<br/>(匹配分类/推断类型/分配负责人)
    Alldata->>MySQL: 批量保存 DataAsset
    Alldata-->>Web: 编目完成 (50项资产)

    Web->>Alldata: POST /api/v1/assets/value/batch-evaluate
    activate Alldata
    Note right of Alldata: AssetValueCalculator

    par 并行计算四维度
        Alldata->>MySQL: 使用度评分 (权重35%)<br/>查询次数/活跃用户/下游依赖/复用率
    and
        Alldata->>MySQL: 业务度评分 (权重30%)<br/>核心指标/SLA等级/业务域重要性
    and
        Alldata->>MySQL: 质量度评分 (权重20%)<br/>完整性/准确性/一致性/时效性
    and
        Alldata->>MySQL: 治理度评分 (权重15%)<br/>负责人/描述/血缘/质量规则/安全等级
    end

    Alldata->>Alldata: 综合评分 = Σ(维度 × 权重)<br/>评级: S(≥80) / A(≥60) / B(≥40) / C(<40)
    Alldata->>MySQL: 保存 AssetValueMetrics + AssetValueHistory
    deactivate Alldata
    Alldata-->>Web: 评估完成<br/>(S级:5项, A级:12项, B级:20项, C级:13项)
    end

    %% ================================================================
    %% 阶段六：表融合分析
    %% ================================================================
    rect rgb(232, 245, 233)
    Note over User,Redis: 阶段六：多表融合与JOIN推荐

    User->>Web: 分析表关联关系
    Web->>Alldata: POST /api/v1/fusion/detect-join-keys
    activate Alldata
    Note right of Alldata: TableFusionService

    Alldata->>Alldata: 精确名称匹配 (confidence=0.95)<br/>模糊名称匹配 Levenshtein (≥0.7)<br/>语义匹配 (user_id ≈ uid, confidence=0.8)
    Alldata->>MySQL: 采样1000行做值级匹配
    MySQL-->>Alldata: overlap_rate计算
    Alldata-->>Web: 候选JOIN键列表

    Web->>Alldata: POST /api/v1/fusion/validate-join
    Alldata->>MySQL: 统计 match_rate/coverage/skew/orphan
    MySQL-->>Alldata: JOIN质量指标
    Alldata->>Alldata: 综合评分 & 推荐JOIN类型<br/>(INNER/LEFT/RIGHT)

    Web->>Alldata: POST /api/v1/fusion/generate-kettle-config
    Alldata->>Alldata: 生成JOIN转换Kettle XML
    deactivate Alldata
    Alldata-->>Web: 返回融合配置 + SQL模板 + 索引建议
    end

    %% ================================================================
    %% 阶段七：知识库向量索引构建
    %% ================================================================
    rect rgb(227, 242, 253)
    Note over User,Redis: 阶段七：企业知识库向量索引构建

    User->>Web: 上传企业文档到知识库
    Web->>Bisheng: POST /api/v1/documents/upload
    activate Bisheng

    Bisheng->>MinIO: 存储原始文档 (PDF/Word/TXT)
    MinIO-->>Bisheng: 存储成功

    Bisheng->>Bisheng: 文档解析 & 分块<br/>(RecursiveTextSplitter)

    Bisheng->>vLLM: POST /v1/embeddings<br/>文档分块 → 向量化
    vLLM-->>Bisheng: 返回 embedding 向量

    Bisheng->>Milvus: INSERT INTO collection<br/>(向量 + 元数据 + 文档ID)
    Milvus-->>Bisheng: 索引构建完成

    Bisheng->>MySQL: 保存 IndexedDocument 记录
    deactivate Bisheng
    Bisheng-->>Web: 文档索引成功 (128个分块)
    end

    %% ================================================================
    %% 阶段八：智能查询 — Text-to-SQL + RAG
    %% ================================================================
    rect rgb(252, 228, 236)
    Note over User,Redis: 阶段八：智能查询 — Text-to-SQL + RAG 融合

    User->>Web: "上季度销售额TOP10产品，并结合销售政策分析原因"
    Web->>Bisheng: POST /api/v1/agent/run

    Bisheng->>Agent: 创建 ReActAgent (max_iterations=10)
    activate Agent

    Note over Agent,vLLM: ▶ 迭代1: 意图识别与规划
    Agent->>vLLM: POST /v1/chat/completions<br/>System: ReAct Prompt Template<br/>User: 用户问题
    vLLM-->>Agent: Thought: 需要先查SQL获取销售数据,<br/>再检索销售政策文档<br/>Action: text_to_sql

    Note over Agent,MySQL: ▶ 迭代2: Text-to-SQL 执行
    Agent->>Alldata: GET /api/v1/metadata/databases/{db}/tables/{table}
    Alldata->>MySQL: 查询元数据
    MySQL-->>Alldata: 返回表结构 (列名/类型/关系)
    Alldata-->>Agent: Schema信息

    Agent->>vLLM: POST /v1/chat/completions<br/>Schema注入 → 生成SQL
    vLLM-->>Agent: SELECT product_name, SUM(amount)...<br/>WHERE quarter = 'Q3' GROUP BY ... TOP 10

    Agent->>Agent: SQL安全检查<br/>(拒绝DROP/DELETE/TRUNCATE)
    Agent->>MySQL: 执行查询SQL
    MySQL-->>Agent: Observation: 结果集 (10行)

    Note over Agent,Milvus: ▶ 迭代3: RAG知识检索
    Agent->>vLLM: POST /v1/chat/completions
    vLLM-->>Agent: Action: vector_search<br/>query="销售政策"

    Agent->>vLLM: POST /v1/embeddings (查询向量化)
    vLLM-->>Agent: query embedding

    Agent->>Milvus: vector_search (top_k=5)
    Milvus-->>Agent: Observation: 5个相关文档片段

    Note over Agent,vLLM: ▶ 迭代4: 综合分析与回答
    Agent->>vLLM: POST /v1/chat/completions<br/>Context: SQL结果 + 文档片段 + 用户问题
    vLLM-->>Agent: Final Answer:<br/>"上季度TOP10产品如下...根据《销售政策》分析..."

    deactivate Agent

    Bisheng->>MySQL: 保存 Conversation + Message
    Bisheng->>Redis: 缓存会话上下文

    Bisheng-->>Web: 返回结构化回答
    Web-->>User: 展示结果 (回答 + SQL + 引用来源 + 图表)
    end
```

### 八阶段全生命周期解析

| 阶段 | 层级 | 核心服务 | 输入 | 输出 |
|------|------|---------|------|------|
| **1. 数据源接入** | L1→L2 | MetadataAutoScanEngine | 数据库连接信息 | MetadataDatabase/Table/Column |
| **2. 敏感识别** | L2+L3 | SensitivityAutoScanService | MetadataColumn + 采样数据 | sensitivity_type/level + MaskingRule |
| **3. ETL加工** | L2+L3 | KettleOrchestrationService | 源表 + AI推荐规则 | 清洗/填充/脱敏后的目标表 + S3数据集 |
| **4. 元数据同步** | L2→OM | MetadataSyncService + OpenLineageService | Alldata元数据 | OpenMetadata实体 + 血缘图 |
| **5. 资产评估** | L2 | AssetValueCalculator | DataAsset + 使用/业务/质量/治理指标 | 四维评分 + S/A/B/C评级 |
| **6. 表融合** | L2 | TableFusionService | 多表结构 + 采样数据 | JOIN键 + 策略推荐 + Kettle配置 |
| **7. 知识索引** | L4+L3 | Bisheng + vLLM + Milvus | 企业文档 (PDF/Word) | 向量索引 (embedding + metadata) |
| **8. 智能查询** | L4+L3+L2 | ReActAgent + Text-to-SQL + RAG | 用户自然语言问题 | 结构化回答 + SQL + 引用来源 |

### 跨层数据流向

```mermaid
graph TB
    subgraph "L1 基础设施层"
        MySQL[(MySQL)]
        MinIO[(MinIO)]
        Milvus[(Milvus)]
        ES[(Elasticsearch)]
        Redis[(Redis)]
    end

    subgraph "元数据治理"
        OM[OpenMetadata]
    end

    subgraph "L2 数据底座层 — Alldata"
        Scan[元数据扫描]
        Sens[敏感识别]
        ETL[ETL编排]
        Sync[元数据同步]
        Asset[资产评估]
        Fusion[表融合]
    end

    subgraph "L3 算法引擎层 — Cube Studio"
        vLLM[vLLM推理]
        Embed[Embedding服务]
    end

    subgraph "L4 应用编排层 — Bisheng"
        Agent[Agent引擎]
        RAG[RAG检索]
        T2S[Text-to-SQL]
        KB[知识库]
    end

    MySQL -->|INFORMATION_SCHEMA| Scan
    Scan -->|AI标注| vLLM
    Scan -->|MetadataColumn| Sens
    Sens -->|MaskingRule| ETL
    vLLM -->|清洗/填充建议| ETL
    ETL -->|Kettle XML| MySQL
    ETL -->|数据集| MinIO
    Scan -->|表结构+血缘| Sync
    Sync -->|REST API| OM
    OM -->|索引| ES
    Scan -->|DataAsset| Asset
    Asset -->|评分| MySQL
    Scan -->|多表结构| Fusion
    Fusion -->|JOIN配置| ETL

    KB -->|文档| MinIO
    KB -->|分块| Embed
    Embed -->|向量| Milvus

    Agent -->|Schema查询| Scan
    Agent -->|SQL生成| vLLM
    Agent -->|执行SQL| MySQL
    RAG -->|向量检索| Milvus
    RAG -->|生成回答| vLLM
    T2S -->|元数据| Scan
    T2S -->|SQL推理| vLLM
    Agent -->|会话| Redis

    style MySQL fill:#e8eaf6
    style MinIO fill:#e8eaf6
    style Milvus fill:#e8eaf6
    style ES fill:#e8eaf6
    style Redis fill:#e8eaf6
    style OM fill:#f3e5f5
    style vLLM fill:#e8f5e9
    style Embed fill:#e8f5e9
    style Agent fill:#fff3e0
    style RAG fill:#fff3e0
    style T2S fill:#fff3e0
    style KB fill:#fff3e0
```

### 关键集成协议

| 调用方 | 被调用方 | 协议 | 端点 |
|--------|---------|------|------|
| Alldata → vLLM | OpenAI兼容API | HTTP/JSON | `POST /v1/chat/completions` |
| Alldata → OpenMetadata | REST API v1 | HTTP/JSON | `POST /tables`, `PUT /lineage` |
| Bisheng → Alldata | 内部REST | HTTP/JSON | `GET /api/v1/metadata/databases/...` |
| Bisheng → vLLM | OpenAI兼容API | HTTP/JSON | `POST /v1/chat/completions`, `/v1/embeddings` |
| Bisheng → Milvus | pymilvus SDK | gRPC | `INSERT`, `SEARCH` |
| OpenMetadata → ES | REST Client | HTTP/JSON | 全文索引与搜索 |
| Kettle → MySQL | JDBC | TCP | `TableInput` / `TableOutput` |
| All → Redis | redis-py | TCP | 会话缓存 / 结果缓存 |
