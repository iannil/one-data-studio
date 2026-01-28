# 测试文档

本目录包含测试相关的文档。

## 文档列表

| 文档 | 描述 |
|------|------|
| [用户生命周期测试用例](./user-lifecycle-test-cases.md) | 各角色用户生命周期的端到端测试场景 |

## 测试目录结构

```
tests/
├── unit/          # 单元测试
├── integration/   # 集成测试
├── e2e/           # 端到端测试
├── performance/   # 性能测试
└── fixtures/      # 测试夹具和数据
```

## 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行端到端测试
npx playwright test tests/e2e/
```
