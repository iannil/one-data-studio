# Phase 2: 渐进迁移（Apache Hop + ShardingSphere）进度追踪

## 概述

本阶段实现 `tech-optimization-roadmap.md` Phase 2 的三个核心任务：
1. Apache Hop 新任务试点
2. Hop Server 集成层开发（双引擎支持）
3. ShardingSphere 透明脱敏 POC

## 实施进度

### 任务 1: Apache Hop 集成模块 ✅ 完成

**完成时间**: 2026-01-31

**新建文件**:
- `services/data-api/integrations/hop/__init__.py` - 模块导出
- `services/data-api/integrations/hop/config.py` - HopConfig 配置类
- `services/data-api/integrations/hop/hop_bridge.py` - Hop Server REST API 客户端

**实现功能**:
- `HopConfig`: 从环境变量加载配置（HOP_SERVER_URL, HOP_SERVER_USER, HOP_SERVER_PASSWORD, HOP_ENABLED）
- `HopBridge`: Hop Server REST API 客户端
  - `health_check()`: 服务健康检查
  - `register_pipeline()` / `execute_pipeline()` / `get_pipeline_status()`: Pipeline 管理
  - `stop_pipeline()` / `remove_pipeline()` / `list_pipelines()`: Pipeline 生命周期
  - `register_workflow()` / `execute_workflow()` / `get_workflow_status()` / `list_workflows()`: Workflow 管理
- `PipelineResult` / `WorkflowResult`: 执行结果数据类，包含状态属性（is_running, is_finished, is_success, is_error）

### 任务 2: Hop Server 集成层开发 ✅ 完成

**完成时间**: 2026-01-31

**修改文件**:
- `services/data-api/integrations/__init__.py` - 添加 Hop 可选导入
- `services/data-api/models/etl.py` - 添加 HOP 引擎枚举和模型字段
- `services/data-api/services/kettle_orchestration_service.py` - 重构为双引擎支持
- `services/data-api/app.py` - 添加 Hop 状态端点

**实现功能**:
- `ETLEngine` 枚举: KETTLE, HOP, AUTO
- `ETLEngineType` 模型枚举添加 HOP
- `ETLTask` 模型添加 `hop_pipeline_path`, `hop_workflow_path`, `hop_params` 字段
- 双引擎编排服务:
  - `_select_engine()`: 根据 engine_type 选择引擎（auto 优先 Hop，不可用时回退 Kettle）
  - `_execute_via_hop()`: Hop 路径执行
  - `_execute_via_kettle()`: Kettle 路径执行（保持兼容）
  - `get_available_engines()`: 返回所有可用引擎状态
  - `get_hop_status()`: Hop Server 详细状态
- `OrchestrationRequest` 添加 `engine_type` 字段（默认 "auto"）
- `OrchestrationResult` 添加 `engine_used` 字段

**新增 API 端点**:
- `GET /api/v1/etl/hop-status`: Hop Server 状态
- `GET /api/v1/etl/engines`: 所有 ETL 引擎状态

### 任务 3: ShardingSphere 透明脱敏 POC ✅ 完成

**完成时间**: 2026-01-31

**新建文件**:
- `services/data-api/integrations/shardingsphere/__init__.py` - 模块导出
- `services/data-api/integrations/shardingsphere/config.py` - ShardingSphereConfig 配置类
- `services/data-api/integrations/shardingsphere/masking_rule_generator.py` - 脱敏规则生成器
- `services/data-api/integrations/shardingsphere/client.py` - ShardingSphere Proxy 客户端

**实现功能**:
- `ShardingSphereConfig`: 从环境变量加载配置
- `MaskingRuleGenerator`: 敏感类型 → ShardingSphere 脱敏算法映射
  - 支持: phone, email, id_card, bank_card, name, address 等
  - `from_sensitivity_results()`: 从敏感扫描结果批量生成规则
  - `generate_mask_rule_sql()`: 生成 CREATE MASK RULE DistSQL
  - `generate_mask_rule_yaml()`: 生成 YAML 配置
- `ShardingSphereClient`: 通过 MySQL 协议连接 ShardingSphere Proxy
  - `health_check()`: 健康检查
  - `execute_distsql()`: 执行 DistSQL
  - `apply_mask_rules()` / `list_mask_rules()` / `remove_mask_rules()`: 脱敏规则管理
  - `show_databases()` / `get_status()`: 状态查询

**修改文件**:
- `services/data-api/integrations/__init__.py` - 添加 ShardingSphere 可选导入
- `services/data-api/app.py` - 添加 ShardingSphere API 端点

**新增 API 端点**:
- `GET /api/v1/masking/shardingsphere/status`: ShardingSphere Proxy 状态
- `POST /api/v1/masking/shardingsphere/generate-rules`: 从敏感扫描结果生成脱敏规则
- `POST /api/v1/masking/shardingsphere/apply-rules`: 应用脱敏规则到 Proxy
- `GET /api/v1/masking/shardingsphere/rules/{database}`: 查看已生效规则
- `DELETE /api/v1/masking/shardingsphere/rules/{database}/{table}`: 移除脱敏规则

### 部署配置更新 ✅ 完成

**完成时间**: 2026-01-31

**修改文件**: `deploy/local/docker-compose.yml`

**新增服务**:
```yaml
hop-server:
  image: apache/hop:2.8.0
  ports: ["8182:8182"]
  profiles: [etl]

shardingsphere-proxy:
  image: apache/shardingsphere-proxy:5.4.1
  ports: ["3307:3307", "33071:33071"]
  profiles: [security]
```

**新增环境变量** (data-api):
- HOP_SERVER_URL, HOP_SERVER_USER, HOP_SERVER_PASSWORD, HOP_ENABLED
- ETL_ENGINE (auto/kettle/hop)
- SHARDINGSPHERE_PROXY_URL, SHARDINGSPHERE_USER, SHARDINGSPHERE_PASSWORD, SHARDINGSPHERE_ENABLED

**新增 volumes**:
- hop_data, hop_config
- shardingsphere_conf, shardingsphere_ext

### 单元测试 ✅ 完成

**完成时间**: 2026-01-31

**新建文件**:
- `tests/unit/test_hop_bridge.py` (32 用例)
  - TestHopConfig: 配置加载
  - TestHopBridgeSession: HTTP 会话
  - TestHopBridgeHealthCheck: 健康检查
  - TestHopBridgePipelineOperations: Pipeline 操作
  - TestHopBridgeWorkflowOperations: Workflow 操作
  - TestPipelineResult / TestWorkflowResult: 结果属性

- `tests/unit/test_shardingsphere_client.py` (40 用例)
  - TestShardingSphereConfig: 配置加载
  - TestMaskingRuleGenerator: 算法映射、SQL/YAML 生成
  - TestMaskingRuleGeneratorFromResults: 批量转换
  - TestMaskingRuleGeneratorSQL: SQL 生成
  - TestMaskingRuleGeneratorYAML: YAML 生成
  - TestShardingSphereClient: 客户端操作
  - TestShardingSphereIntegrationInit: 模块导入

- `tests/unit/test_dual_engine_orchestration.py` (34 用例)
  - TestEngineSelection: 引擎选择逻辑
  - TestExecuteViaCarte: 远程执行
  - TestGetAvailableEngines: 可用引擎查询
  - TestGetHopStatus: Hop 状态查询
  - TestOrchestrationRequest/Result: 请求/结果字段
  - TestETLEngineEnum: 引擎枚举
  - TestOrchestrationStatus: 状态枚举
  - TestServiceInitialization: 服务初始化
  - TestDataQualityReport: 数据质量报告

**测试总数**: 106 用例全部通过 ✅

## 验证方式

### 1. Hop Server 验证
```bash
# 启动 Hop Server
docker-compose --profile etl up -d hop-server data-api

# 检查状态
curl http://localhost:8001/api/v1/etl/hop-status
curl http://localhost:8001/api/v1/etl/engines
```

### 2. 双引擎编排验证
```bash
# 使用 Hop 引擎执行
curl -X POST http://localhost:8001/api/v1/etl/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"transformation_path": "/path/to/pipeline.hpl", "engine_type": "hop"}'

# 使用 auto 模式（优先 Hop）
curl -X POST http://localhost:8001/api/v1/etl/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"transformation_path": "/path/to/transform.ktr", "engine_type": "auto"}'
```

### 3. ShardingSphere 验证
```bash
# 启动 ShardingSphere Proxy
docker-compose --profile security up -d shardingsphere-proxy data-api

# 检查状态
curl http://localhost:8001/api/v1/masking/shardingsphere/status

# 生成脱敏规则
curl -X POST http://localhost:8001/api/v1/masking/shardingsphere/generate-rules \
  -H "Content-Type: application/json" \
  -d '{
    "database": "test_db",
    "table": "users",
    "sensitivity_results": [
      {"column_name": "phone", "sensitivity_type": "phone"},
      {"column_name": "email", "sensitivity_type": "email"}
    ]
  }'
```

### 4. 单元测试验证
```bash
# 运行所有 Phase 2 测试
python3 -m pytest tests/unit/test_hop_bridge.py tests/unit/test_shardingsphere_client.py tests/unit/test_dual_engine_orchestration.py -v
```

## 关键文件清单

| 文件路径 | 状态 | 任务 |
|---------|------|------|
| `services/data-api/integrations/hop/__init__.py` | ✅ 新建 | Hop |
| `services/data-api/integrations/hop/config.py` | ✅ 新建 | Hop |
| `services/data-api/integrations/hop/hop_bridge.py` | ✅ 新建 | Hop |
| `services/data-api/integrations/shardingsphere/__init__.py` | ✅ 新建 | SS |
| `services/data-api/integrations/shardingsphere/config.py` | ✅ 新建 | SS |
| `services/data-api/integrations/shardingsphere/masking_rule_generator.py` | ✅ 新建 | SS |
| `services/data-api/integrations/shardingsphere/client.py` | ✅ 新建 | SS |
| `services/data-api/integrations/__init__.py` | ✅ 修改 | Hop + SS |
| `services/data-api/models/etl.py` | ✅ 修改 | Hop |
| `services/data-api/services/kettle_orchestration_service.py` | ✅ 修改 | 双引擎 |
| `services/data-api/app.py` | ✅ 修改 | Hop + SS |
| `deploy/local/docker-compose.yml` | ✅ 修改 | Hop + SS |
| `tests/unit/test_hop_bridge.py` | ✅ 新建 | 测试 |
| `tests/unit/test_shardingsphere_client.py` | ✅ 新建 | 测试 |
| `tests/unit/test_dual_engine_orchestration.py` | ✅ 新建 | 测试 |

## 后续计划

Phase 2 已完成全部核心实现。后续可考虑：

1. **集成测试**: 添加端到端集成测试验证完整流程
2. **监控指标**: 添加 Prometheus 指标采集（引擎选择、执行时间、成功率）
3. **UI 集成**: 前端添加 ETL 引擎选择和 ShardingSphere 规则管理界面
4. **文档完善**: 添加用户操作手册和运维指南
