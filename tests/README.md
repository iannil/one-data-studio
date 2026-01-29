# ONE-DATA-STUDIO 测试文档

## 概述

本文档描述 ONE-DATA-STUDIO 项目的测试体系结构和执行方法。

## 测试架构

```
tests/
├── unit/                    # 单元测试
│   ├── fixtures/           # 测试数据工厂
│   ├── test_data_administrator/    # 数据管理员单元测试
│   ├── test_data_engineer/        # 数据工程师单元测试
│   ├── test_ai_engineer/           # 算法工程师单元测试
│   ├── test_business_user/         # 业务用户单元测试
│   └── test_system_admin/          # 系统管理员单元测试
│
├── integration/             # 集成测试
│   ├── conftest.py
│   ├── test_data_pipeline_integration.py
│   ├── test_rag_integration.py
│   └── test_cross_service_integration.py
│
├── e2e/                     # 端到端测试
│   └── user-lifecycle/      # 用户生命周期测试
│       ├── data-administrator.spec.ts
│       ├── data-engineer.spec.ts
│       ├── ai-engineer.spec.ts
│       ├── business-user.spec.ts
│       ├── system-admin.spec.ts
│       └── cross-role-workflow.spec.ts
│
├── mocks/                   # Mock 服务
│   ├── mock_vllm.py       # Mock vLLM 客户端
│   ├── mock_milvus.py     # Mock Milvus 客户端
│   └── mock_kettle.py     # Mock Kettle 客户端
│
├── data/                    # 测试数据
│   ├── sql/               # SQL 脚本
│   └── documents/         # 测试文档
│
├── performance/            # 性能测试
│   └── etl-performance.py
│
├── conftest.py             # 共享配置
├── pytest.ini              # Pytest 配置
├── run_tests.sh            # 测试执行脚本
└── test_report_config.py   # 报告配置
```

## 测试覆盖统计

### 按角色统计

| 角色 | 单元测试 | 集成测试 | E2E测试 | 总计 |
|------|---------|---------|--------|------|
| 数据管理员 | 68 | - | 5 | 73 |
| 数据工程师 | 30 | - | 5 | 35 |
| 算法工程师 | 23 | - | 5 | 28 |
| 业务用户 | 38 | - | 5 | 43 |
| 系统管理员 | 26 | - | 5 | 31 |
| **总计** | **185** | **14** | **25** | **224** |

### 按优先级统计

| 优先级 | 用例数 | 状态 |
|--------|--------|------|
| P0 | 199 | ✅ 通过 |
| P1 | 20 | ✅ 通过 |
| P2 | 5 | ✅ 通过 |

## 快速开始

### 安装依赖

```bash
pip install -r requirements-test.txt
npx playwright install --with-deps
```

### 运行测试

```bash
# 使用 Makefile
make test-all              # 运行所有测试
make test-unit             # 运行单元测试
make test-p0               # 运行P0测试

# 使用脚本
./tests/run_tests.sh -t unit -l p0
./tests/run_tests.sh --role data_administrator

# 直接使用 pytest
pytest tests/unit/test_data_administrator/ -v
pytest tests/unit/ -m p0 -x
```

## 按角色测试

### 数据管理员测试

```bash
# 单元测试
pytest tests/unit/test_data_administrator/test_datasource.py -v
pytest tests/unit/test_data_administrator/test_metadata_scan.py -v
pytest tests/unit/test_data_administrator/test_sensitivity.py -v

# E2E测试
npx playwright test tests/e2e/user-lifecycle/data-administrator.spec.ts
```

### 数据工程师测试

```bash
# 单元测试
pytest tests/unit/test_data_engineer/test_data_collection.py -v
pytest tests/unit/test_data_engineer/test_etl_orchestration.py -v
pytest tests/unit/test_data_engineer/test_masking.py -v
```

### 算法工程师测试

```bash
# 单元测试
pytest tests/unit/test_ai_engineer/test_notebook.py -v
pytest tests/unit/test_ai_engineer/test_training.py -v
pytest tests/unit/test_ai_engineer/test_deployment.py -v
```

### 业务用户测试

```bash
# 单元测试
pytest tests/unit/test_business_user/test_knowledge_base.py -v
pytest tests/unit/test_business_user/test_intelligent_query.py -v
pytest tests/unit/test_business_user/test_bi_visualization.py -v
```

### 系统管理员测试

```bash
# 单元测试
pytest tests/unit/test_system_admin/test_system_config.py -v
pytest tests/unit/test_system_admin/test_user_management.py -v
pytest tests/unit/test_system_admin/test_monitoring.py -v
```

## 测试标记

### 按类型

- `unit` - 单元测试（不依赖外部服务）
- `integration` - 集成测试（需要外部服务）
- `e2e` - 端到端测试
- `performance` - 性能测试
- `security` - 安全测试

### 按优先级

- `p0` - P0 优先级（核心功能，阻塞发布）
- `p1` - P1 优先级（重要功能）
- `p2` - P2 优先级（一般功能）

### 按角色

- `data_administrator` - 数据管理员
- `data_engineer` - 数据工程师
- `ai_engineer` - 算法工程师
- `business_user` - 业务用户
- `system_admin` - 系统管理员

### 依赖标记

- `requires_db` - 需要数据库
- `requires_milvus` - 需要 Milvus
- `requires_minio` - 需要 MinIO
- `requires_redis` - 需要 Redis
- `requires_vllm` - 需要 vLLM 服务

## Mock 服务

测试框架包含以下 Mock 服务，用于模拟外部依赖：

1. **MockVLLMClient** - 模拟 LLM 推理服务
   - 聊天补全
   - 向量嵌入生成
   - 预设响应模板

2. **MockMilvusClient** - 模拟向量数据库
   - 集合管理
   - 向量插入
   - 相似度搜索

3. **MockKettleClient** - 模拟 ETL 工具
   - Kettle XML 生成
   - 任务执行
   - 清洗规则生成

## CI/CD 集成

测试已配置支持 CI/CD 流水线：

```yaml
# .github/workflows/test.yml 示例
name: 测试

on: [push, pull_request]

jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: 安装依赖
        run: pip install -r requirements-test.txt
      - name: 运行 P0 单元测试
        run: pytest tests/unit/ -m p0 --cov-fail-under=70

  integration-test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
      minio:
        image: minio/minio
    steps:
      - uses: actions/checkout@v3
      - name: 运行集成测试
        run: pytest tests/integration/ -m integration

  e2e-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: 安装 Playwright
        run: npx playwright install --with-deps
      - name: 运行 E2E 测试
        run: npx playwright test
```

## 测试报告

测试执行完成后会生成以下报告：

1. **HTML 测试报告**: `reports/html/index.html`
2. **覆盖率报告**: `htmlcov/index.html`
3. **JUnit XML**: `reports/junit.xml`

## 常见问题

### Q: 如何运行特定优先级的测试？

```bash
pytest tests/unit/ -m p0  # 只运行P0
pytest tests/unit/ -m "p0 and not slow"  # 排除慢速测试
```

### Q: 如何调试单个测试？

```bash
pytest tests/unit/test_data_administrator/test_datasource.py::TestDataSourceRegistration::test_register_mysql_datasource -v -s
```

### Q: 如何只运行失败的测试？

```bash
pytest --lf  # 只运行上次失败的测试
```

### Q: E2E 测试需要什么环境？

E2E 测试需要前端应用运行。确保：

```bash
# 启动前端
cd web && npm run dev

# 运行 E2E 测试
npx playwright test
```

## 维护指南

### 添加新测试

1. 确定测试所属角色和优先级
2. 选择合适的测试文件（单元/集成/E2E）
3. 遵循现有命名规范
4. 添加适当的 pytest 标记
5. 更新本文档的测试统计

### Mock 服务更新

当需要新的 Mock 行为时，更新 `tests/mocks/` 下的相应文件。

### 测试数据更新

测试 SQL 和文档数据位于 `tests/data/` 目录下，根据需要更新。
