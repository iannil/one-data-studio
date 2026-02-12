# 测试文档

本目录包含测试相关的文档。

## 文档列表

| 文档 | 描述 |
|------|------|
| [测试计划](./test-plan.md) | 测试策略和测试计划 |
| [用户生命周期测试用例](./user-lifecycle-test-cases.md) | 各角色用户生命周期的端到端测试场景 |
| [最终改进建议](./final-improvements.md) | 测试改进建议总结 |
| [功能测试规范](./test-specs/) | DataOps 平台功能测试规范（321 个功能） |

## 功能测试规范 (test-specs/)

DataOps 平台功能测试规范目录，包含 321 个功能的完整测试规范：

| 文件 | 领域 | 功能数 |
|------|------|--------|
| [01-data-ingestion.md](./test-specs/01-data-ingestion.md) | 数据接入 | 20 |
| [02-data-processing.md](./test-specs/02-data-processing.md) | 数据处理 | 52 |
| [03-data-governance.md](./test-specs/03-data-governance.md) | 数据治理 | 112 |
| [04-monitoring-ops.md](./test-specs/04-monitoring-ops.md) | 监控运维 | 47 |
| [05-data-utilization.md](./test-specs/05-data-utilization.md) | 数据利用 | 55 |
| [06-platform-support.md](./test-specs/06-platform-support.md) | 平台支撑 | 35 |
| **总计** | **6 领域** | **321** |

## 测试目录结构

```
tests/
├── unit/          # 单元测试
│   ├── test_data_administrator/  # 数据管理员测试
│   ├── test_data_engineer/       # 数据工程师测试
│   ├── test_ai_engineer/         # 算法工程师测试
│   ├── test_business_user/       # 业务用户测试
│   └── test_system_admin/        # 系统管理员测试
├── integration/   # 集成测试
├── e2e/           # 端到端测试 (Playwright)
├── performance/   # 性能测试
├── mocks/         # Mock 服务
├── fixtures/      # 测试夹具和数据
└── run_tests.sh   # 测试执行脚本
```

## 测试统计

| 测试类型 | 文件数 | 覆盖场景 |
|----------|--------|----------|
| 单元测试 | 87+ | 按角色分类 + 基础功能 |
| 集成测试 | 24 | 服务间集成 |
| E2E 测试 (Python) | 15 | 用户生命周期 |
| E2E 测试 (Playwright) | 41 | 前端 E2E |
| 性能测试 | 5 | 压力测试 |

## 运行测试

### 使用测试脚本

```bash
# 运行所有测试
./tests/run_tests.sh -t all

# 运行单元测试
./tests/run_tests.sh -t unit

# 运行 P0 优先级测试
./tests/run_tests.sh -l p0

# 按角色运行测试
./tests/run_tests.sh --role data_administrator

# 生成覆盖率报告
./tests/run_tests.sh -c -r
```

### 使用 pytest

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 按角色运行
pytest tests/unit/test_data_administrator/ -v

# 运行 P0 测试
pytest tests/ -m p0 -v
```

### 使用 Makefile

```bash
# 运行所有单元测试
make test-unit

# 按角色运行
make test-data-administrator
make test-ai-engineer

# 运行 P0 测试
make test-p0-all

# 运行集成测试
make test-integration

# 生成测试报告
make test-report
```

### E2E 测试 (Playwright)

```bash
# 运行所有 E2E 测试
cd tests/e2e && npx playwright test

# 按角色运行
npx playwright test data-administrator.spec.ts
npx playwright test ai-engineer.spec.ts

# 运行跨角色工作流测试
npx playwright test cross-role-workflow.spec.ts
```

## 测试标记

### 优先级标记

| 标记 | 说明 |
|------|------|
| `p0` | P0 优先级测试（核心功能，阻塞发布） |
| `p1` | P1 优先级测试（重要功能，应该修复） |
| `p2` | P2 优先级测试（一般功能，可延后） |

### 角色标记

| 标记 | 说明 |
|------|------|
| `data_administrator` | 数据管理员测试 |
| `data_engineer` | 数据工程师测试 |
| `ai_engineer` | 算法工程师测试 |
| `business_user` | 业务用户测试 |
| `system_admin` | 系统管理员测试 |

### 依赖标记

| 标记 | 说明 |
|------|------|
| `requires_db` | 需要数据库 |
| `requires_milvus` | 需要 Milvus |
| `requires_minio` | 需要 MinIO |
| `requires_redis` | 需要 Redis |
| `requires_vllm` | 需要 vLLM 服务 |
| `requires_kettle` | 需要 Kettle |
| `requires_auth` | 需要认证服务 |

## 测试覆盖报告

测试完成后，覆盖率报告会生成在以下位置：

- **HTML 报告**: `htmlcov/index.html`
- **XML 报告**: `coverage.xml`
- **终端报告**: 运行时输出

## 归档文档

过时的测试文档已归档到 `docs/99-archived/testing-2025/`：

- `test-final-improvements.md`
- `test-final-report.md`
- `test-final-summary.md`
- `test-fix-summary.md`
- `test-improvement-summary.md`
- `test-execution-report.md`
- `final-test-summary.md`
