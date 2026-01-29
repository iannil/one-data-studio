# ONE-DATA-STUDIO Demo 演示指南

本文档提供了完整的平台演示流程，包括场景说明、操作步骤和验证点。

## 目录

- [准备阶段](#准备阶段)
- [核心场景演示](#核心场景演示)
- [三大集成验证](#三大集成验证)
- [故障排查](#故障排查)
- [FAQ](#faq)

---

## 准备阶段

### 1. 环境检查

在开始演示前，确保所有服务正常运行：

```bash
# 检查服务状态
kubectl get pods -n one-data-system

# 或使用 Docker Compose
docker-compose ps
```

预期输出：
- `data-api-*` - Running
- `agent-api-*` - Running
- `openai-proxy-*` - Running
- `mysql-*` - Running
- `minio-*` - Running
- `milvus-*` - Running
- `vllm-serving-*` - Running（可选，用于模型推理）

### 2. 健康检查

```bash
# Data API
curl http://localhost:8080/api/v1/health

# Agent API
curl http://localhost:8081/api/v1/health

# OpenAI Proxy
curl http://localhost:8000/health
```

### 3. 前端访问

```
http://localhost:3000
```

---

## 核心场景演示

### 场景一：数据治理与元数据管理

**演示目标**：展示 Data 的数据治理能力

#### 步骤 1：查看数据集列表

1. 登录系统后，导航至「数据管理」→「数据集」
2. 查看已注册的数据集列表

**验证点**：
- 数据集列表正常显示
- 可以看到数据集名称、类型、记录数等信息

#### 步骤 2：查看数据集详情

1. 点击任意数据集进入详情页
2. 查看数据集的 Schema、预览数据

**验证点**：
- Schema 表格正确显示字段信息
- 数据预览正常加载

#### 步骤 3：查询元数据

1. 导航至「数据管理」→「元数据」
2. 选择数据库和表查看详细信息

**验证点**：
- 表字段、类型、注释正确显示
- 表关系（外键）正确展示

### 场景二：RAG 知识问答

**演示目标**：展示基于向量检索的增强生成能力

#### 步骤 1：上传知识文档

1. 导航至「知识库」→「文档管理」
2. 点击「上传文档」
3. 选择示例文档（如产品说明书、技术文档）

```bash
# 也可以通过 API 上传
curl -X POST http://localhost:8081/api/v1/documents/upload \
  -H "Content-Type: application/json" \
  -d '{
    "content": "ONE-DATA-STUDIO 是一个融合了数据治理、模型训练和应用编排的企业级 AI 平台...",
    "file_name": "intro.txt",
    "title": "平台介绍",
    "collection": "demo"
  }'
```

**验证点**：
- 文档上传成功
- 显示 chunk 数量和向量索引状态

#### 步骤 2：RAG 问答

1. 导航至「AI 聊天」页面
2. 在系统设置中选择 RAG 模式
3. 输入问题：`"ONE-DATA-STUDIO 平台有哪些主要功能？"`

**验证点**：
- 回答基于上传的知识库内容
- 显示引用来源（文档名、相关度分数）
- 回答准确、完整

### 场景三：Text-to-SQL 智能查询

**演示目标**：展示基于元数据的自然语言 SQL 生成

#### 步骤 1：选择数据库表

1. 导航至「数据分析」→「Text2SQL」
2. 选择数据库（如 `sales_dw`）
3. 勾选需要查询的表（如 `orders`, `customers`）

**验证点**：
- 表列表正确加载
- 字段信息正确显示

#### 步骤 2：自然语言查询

1. 输入自然语言问题：`"查找最近一周订单金额前10的客户"`
2. 点击「生成 SQL」

**验证点**：
- 生成的 SQL 语法正确
- SQL 符合查询意图
- 可以查看执行结果（数据预览）

#### 步骤 3：执行查询

1. 点击「执行查询」
2. 查看查询结果

**验证点**：
- 查询结果正确返回
- 数据展示格式正确

### 场景四：工作流编排

**演示目标**：展示可视化工作流编辑和执行能力

#### 步骤 1：创建工作流

1. 导航至「工作流」→「工作流列表」
2. 点击「新建工作流」
3. 输入名称：`"Demo RAG 工作流"`

#### 步骤 2：设计工作流

1. 从左侧节点面板拖拽节点到画布：
   - `输入节点` - 用户查询
   - `检索节点` - 向量检索
   - `LLM 节点` - 大模型生成
   - `输出节点` - 返回结果

2. 连接节点形成数据流
3. 配置每个节点的参数

**验证点**：
- 拖拽操作流畅
- 节点连接正常
- 配置面板正常显示

#### 步骤 3：保存并运行

1. 点击「保存」按钮
2. 点击「运行」按钮
3. 输入测试查询：`"什么是 RAG？"`
4. 查看执行结果

**验证点**：
- 工作流保存成功
- 执行状态正确显示
- 返回预期的结果

### 场景五：Agent 工具调用

**演示目标**：展示 Agent 的自主工具调用能力

#### 步骤 1：配置 Agent

1. 导航至「AI Agent」→「Agent 模板」
2. 选择或创建 Agent 配置
3. 配置可用工具（如：SQL 查询、向量检索）

#### 步骤 2：运行 Agent

1. 输入复杂问题：`"帮我分析一下最近的销售数据，并找出趋势"`
2. 观察 Agent 的思考过程
3. 查看最终结果

**验证点**：
- Agent 正确选择工具
- 工具调用结果显示清晰
- 最终答案综合了多个工具的结果

---

## 三大集成验证

### 集成点 1：Data → Cube Studio（数据集注册与读取）

**验证目标**：确认 Data 的数据集可以被 Cube Studio 的训练任务消费

#### API 验证

```bash
# 1. 在 Data 注册数据集
curl -X POST http://localhost:8080/api/v1/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "demo_dataset",
    "source_type": "table",
    "source_config": {
      "database": "sales_dw",
      "table": "orders"
    }
  }'

# 2. 获取数据集详情
curl http://localhost:8080/api/v1/datasets/demo_dataset

# 3. 检查数据集是否可被 Cube Studio 访问
# (Cube Studio 应能通过统一的存储协议访问数据)
```

**验证点**：
- 数据集注册成功
- 元数据正确存储
- 数据文件可访问

### 集成点 2：Cube Studio → Agent（模型服务调用）

**验证目标**：确认 Agent 可以通过 OpenAI 兼容 API 调用 Cube Studio 部署的模型

#### API 验证

```bash
# 1. 查看 Cube Studio 可用模型
curl http://localhost:8002/v1/models

# 2. 通过 Agent 代理调用模型
curl -X POST http://localhost:8081/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "model": "qwen-14b-chat",
    "temperature": 0.7
  }'

# 3. 验证响应来自真实模型
# 检查响应中的 model 字段
```

**验证点**：
- 模型列表正确返回
- 聊天响应来自真实模型（非 Mock）
- 流式输出正常工作

### 集成点 3：Data → Agent（Text-to-SQL 元数据查询）

**验证目标**：确认 Agent 的 Text-to-SQL 功能能正确获取 Data 的元数据

#### API 验证

```bash
# 1. 查询 Data 元数据
curl http://localhost:8080/api/v1/metadata/databases/sales_dw/tables

# 2. 通过 Agent 生成 SQL
curl -X POST http://localhost:8081/api/v1/text2sql \
  -H "Content-Type: application/json" \
  -d '{
    "natural_language": "查询销售额最高的10个产品",
    "database": "sales_dw"
  }'

# 3. 验证生成的 SQL 使用了正确的表和字段
```

**验证点**：
- 元数据 API 正常响应
- 生成的 SQL 使用正确的表名和字段
- SQL 语法正确可执行

---

## 故障排查

### 问题 1：服务无法启动

**症状**：Pod 状态为 CrashLoopBackOff 或容器立即退出

**排查步骤**：
```bash
# 查看 Pod 日志
kubectl logs -f <pod-name> -n one-data-system

# 查看事件
kubectl describe pod <pod-name> -n one-data-system
```

**常见原因**：
- 数据库连接失败：检查 `MYSQL_*` 环境变量
- 端口冲突：检查服务端口是否被占用
- 资源不足：检查节点资源使用情况

### 问题 2：向量检索无结果

**症状**：RAG 问答返回默认答案，没有引用知识库

**排查步骤**：
```bash
# 检查 Milvus 连接
curl http://localhost:8081/api/v1/collections

# 查看已索引文档
curl http://localhost:8081/api/v1/documents
```

**常见原因**：
- Milvus 未启动：检查 Milvus 服务状态
- 文档未索引：重新上传文档
- Embedding 服务不可用：检查 OpenAI Proxy 配置

### 问题 3：工作流执行失败

**症状**：工作流运行后显示失败状态

**排查步骤**：
```bash
# 查看工作流执行日志
curl http://localhost:8081/api/v1/executions/<execution-id>/logs

# 查看工作流状态
curl http://localhost:8081/api/v1/workflows/<workflow-id>/status
```

**常见原因**：
- 节点配置错误：检查节点参数
- 外部服务不可用：检查依赖服务状态
- 超时：增加执行超时时间

---

## FAQ

### Q1：如何快速准备演示数据？

**A**：使用内置的数据初始化脚本：

```bash
# Python
python scripts/init_demo_data.py

# 或直接使用 API
bash scripts/upload_demo_docs.sh
```

### Q2：演示时模型响应慢怎么办？

**A**：
1. 使用较小的模型（如 `qwen-7b-chat` 而非 `qwen-14b-chat`）
2. 减少 `max_tokens` 参数
3. 启用流式输出以改善用户体验

### Q3：如何离线演示？

**A**：
1. 预先上传所有需要的文档
2. 确保模型已下载并加载
3. 使用 Mock 模式进行部分功能演示

### Q4：演示中遇到错误如何处理？

**A**：
1. 保持冷静：大多数错误不影响整体演示
2. 快速切换到备用场景
3. 记录错误细节，演示后分析
4. 不要在现场调试问题

---

## 演示检查清单

### 开始前检查

- [ ] 所有服务运行正常
- [ ] 健康检查通过
- [ ] 演示数据已准备
- [ ] 浏览器可以访问前端

### 场景演示检查

- [ ] 数据集列表正常显示
- [ ] 文档上传成功
- [ ] RAG 问答返回知识库内容
- [ ] Text-to-SQL 生成正确 SQL
- [ ] 工作流创建和运行成功
- [ ] Agent 工具调用正常

### 集成验证检查

- [ ] Data → Cube 数据集可访问
- [ ] Cube → Agent 模型调用成功
- [ ] Data → Agent 元数据获取成功

### 结束后检查

- [ ] 收集反馈意见
- [ ] 记录演示中发现的问题
- [ ] 更新已知问题列表
- [ ] 清理演示数据（如需要）

---

## 附录：演示环境配置

### 推荐配置

| 组件 | 配置 | 说明 |
|------|------|------|
| CPU | 8 核 | 基础运行 |
| 内存 | 16GB | 包含模型加载 |
| 存储 | 50GB | 数据和日志 |
| GPU | 可选 | 模型推理加速 |

### 快速启动命令

```bash
# 完整启动
kubectl apply -f deploy/kubernetes/

# 或使用 Docker Compose
docker-compose up -d

# 等待服务就绪
kubectl wait --for=condition=ready pod -l app=data-api -n one-data-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=agent-api -n one-data-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=openai-proxy -n one-data-system --timeout=300s
```

---

*最后更新：2025-01-24*
