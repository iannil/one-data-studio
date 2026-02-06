# DataOps 真实 API 验证测试实施进度

**日期**: 2026-02-07
**状态**: 进行中
**负责人**: Claude

## 概述

本任务旨在为 DataOps 平台创建真实 API 验证测试，使用 Playwright 非 headless 模式连接真实后端 API，验证所有页面是否正常工作。

## 目标

1. 扩展现有验证器辅助类，添加 Console 捕获和 Network 监控
2. 创建真实 API 验证测试文件
3. 添加 Playwright 测试项目配置
4. 创建便捷运行脚本
5. 生成完整的验证报告

## 实施进度

### 已完成

#### 1. 扩展验证器辅助类 (Step 1)

**文件**: `tests/e2e/helpers/data-ops-validator.ts`

**新增功能**:
- Console 捕获器
  - 捕获 `console.log`, `console.warn`, `console.error`, `console.info`, `console.debug`
  - 记录日志级别、消息、堆栈信息、时间戳
- Network 监控器
  - 捕获所有 API 请求（`/api/` 和 `/graphql`）
  - 记录请求 URL、方法、状态码、响应时间、成功状态
- 真实 API 模式
  - 添加 `useRealAPI` 配置选项
  - 禁用 Mock 路由
- 扩展页面配置
  - 新增运维中心页面（调度管理、智能调度、执行记录、资源监控、操作日志、告警规则）
  - 新增元数据图谱页面（元数据图谱、元数据搜索、影响分析）
- 新增接口
  - `ConsoleLogEntry`: Console 日志条目
  - `ApiRequestRecord`: API 请求记录
  - `DATA_OPS_LIVE_PAGES`: 真实 API 验证页面配置
  - `DATA_OPS_PAGES_BY_MODULE`: 按模块分组的页面配置

**新增页面数量**: 9 个
- 运维中心: 6 个页面
- 元数据图谱: 3 个页面

#### 2. 创建真实 API 验证测试 (Step 2)

**文件**: `tests/e2e/data-ops-live-validation.spec.ts`

**功能特性**:
- 连接真实后端 API（不使用 Mock）
- 测试所有 DataOps 页面（30+ 个页面）
- 生成详细验证报告
- 按模块分组测试：
  - 数据管理模块
  - 数据开发模块
  - 运维中心模块
  - 元数据管理模块
  - 分析工具模块
  - 数据集模块

**报告格式**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ [数据源] /data/datasources
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
页面加载: 1.2s ✓
布局检查: ✓
JS错误: 无
API请求: 3个 (全部成功)
  ✓ GET /api/v1/data/datasources (200, 234ms)
  ✓ GET /api/v1/metadata/tables (200, 156ms)
  ✓ GET /api/v1/data/statistics (200, 89ms)
Console日志: 2条
  ℹ [Info] Data sources loaded
  ⚠ [Warn] One datasource is disconnected
截图: test-results/screenshots/live/data-sources-2026-02-07.png
```

**最终汇总报告**:
- 总页面数、通过数、失败数
- 失败页面详情（带错误信息）
- API 请求统计
- Console 错误汇总
- 加载时间排名

#### 3. 添加 Playwright 测试项目 (Step 3)

**文件**: `playwright.config.ts`

**新增项目配置**:
```typescript
{
  name: 'data-ops-live',
  use: {
    ...devices['Desktop Chrome'],
    // 非 headless 模式通过环境变量控制
    headless: process.env.HEADLESS !== 'false',
  },
  testMatch: /data-ops-live-validation\.spec\.ts/,
}
```

#### 4. 创建运行脚本 (Step 4)

**文件**: `scripts/run-live-validation.sh`

**功能**:
- 便捷运行脚本
- 支持命令行参数：
  - `-h, --help`: 显示帮助信息
  - `-d, --debug`: 调试模式（打开 Playwright Inspector）
  - `-H, --headless`: 使用 headless 模式
  - `-u, --update`: 更新 Playwright 浏览器
  - `-p, --project`: 指定项目名称
  - `-t, --test`: 运行单个测试文件
  - `-b, --base-url`: 指定基础 URL
- 后端服务检查
- 自动创建截图目录

## 待验证

### 运行测试

```bash
# 方式1: 使用脚本（推荐）
./scripts/run-live-validation.sh

# 方式2: 直接使用 npx
HEADLESS=false npx playwright test --project=data-ops-live

# 方式3: 调试模式
npx playwright test --project=data-ops-live --debug
```

### 验收标准

- [ ] 所有 DataOps 页面能够正常打开
- [ ] 真实 API 请求正常响应（无 4xx/5xx 错误，或可接受的错误）
- [ ] 无致命 JavaScript 错误
- [ ] 页面基本布局和功能组件可见
- [ ] 生成完整的验证报告

## 技术细节

### 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `tests/e2e/helpers/data-ops-validator.ts` | 修改 | 添加 Console/Network 捕获 |
| `tests/e2e/data-ops-live-validation.spec.ts` | 新建 | 真实 API 验证测试 |
| `playwright.config.ts` | 修改 | 添加 data-ops-live 项目 |
| `scripts/run-live-validation.sh` | 新建 | 运行脚本 |
| `docs/progress/2026-02-07-data-ops-live-validation.md` | 新建 | 进度文档 |

### 测试覆盖页面

#### 数据管理 (11个)
1. 数据源 (`/data/datasources`)
2. 元数据管理 (`/metadata`)
3. 版本对比 (`/metadata/version-diff`)
4. 特征存储 (`/data/features`)
5. 数据标准 (`/data/standards`)
6. 数据资产 (`/data/assets`)
7. 数据服务 (`/data/services`)
8. BI 报表 (`/data/bi`)
9. 指标体系 (`/data/metrics`)
10. 系统监控 (`/data/monitoring`)
11. 智能预警 (`/data/alerts`)

#### 数据开发 (10个)
1. ETL 任务 (`/data/etl`)
2. Kettle 引擎 (`/data/kettle`)
3. Kettle 配置生成 (`/data/kettle-generator`)
4. 文档 OCR (`/data/ocr`)
5. 数据质量 (`/data/quality`)
6. 数据血缘 (`/data/lineage`)
7. 离线开发 (`/data/offline`)
8. 实时开发 (`/data/streaming`)
9. 实时 IDE (`/data/streaming-ide`)

#### 运维中心 (6个)
1. 调度管理 (`/operations/scheduling`)
2. 智能调度 (`/operations/smart-scheduling`)
3. 执行记录 (`/operations/execution-records`)
4. 资源监控 (`/operations/resource-monitor`)
5. 操作日志 (`/operations/logs`)
6. 告警规则 (`/operations/alert-rules`)

#### 元数据管理 (5个)
1. 元数据管理 (`/metadata`)
2. 版本对比 (`/metadata/version-diff`)
3. 元数据图谱 (`/metadata/graph`)
4. 元数据搜索 (`/metadata/search`)
5. 影响分析 (`/metadata/impact-analysis`)

#### 分析工具 (2个)
1. Notebook (`/model/notebooks`)
2. SQL Lab (`/model/sql-lab`)

#### 数据集 (1个)
1. 数据集 (`/datasets`)

**总计**: 35 个页面

## 风险和注意事项

1. **后端依赖**: 需要后端服务运行中
2. **认证**: 需要有效的登录凭证
3. **数据依赖**: 某些页面可能需要特定数据才能正常显示
4. **性能**: 35 个页面完整测试可能需要 5-10 分钟

## 下一步

1. 运行测试并验证结果
2. 根据测试结果调整验收标准
3. 优化测试性能
4. 添加 CI/CD 集成
