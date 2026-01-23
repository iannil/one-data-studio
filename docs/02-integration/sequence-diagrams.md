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
