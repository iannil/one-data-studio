# DataOps 全流程 E2E 测试指南

## 概述

本测试演示 **DataOps 平台从数据接入到数据利用的完整流程**，使用 Playwright 进行端到端自动化测试。

## 测试流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DataOps 全流程测试                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │  阶段1: 数据接入  │───▶│  阶段2: 数据处理  │───▶│  阶段3: 数据治理  │      │
│  │                  │    │                  │    │                  │      │
│  │ • 注册数据源     │    │ • 创建 ETL 任务  │    │ • 元数据采集     │      │
│  │ • 测试连接       │    │ • 字段映射       │    │ • AI 智能标注    │      │
│  │ • 配置 CDC       │    │ • 执行同步       │    │ • 敏感扫描       │      │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘      │
│                                                             │               │
│                                                             ▼               │
│                                               ┌──────────────────┐            │
│                                               │  阶段4: 数据利用  │            │
│                                               │                  │            │
│                                               │ • Text-to-SQL    │            │
│                                               │ • RAG 检索       │            │
│                                               │ • BI 报表生成    │            │
│                                               └──────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 前置准备

### 1. 启动 Docker 服务

```bash
# 启动所有服务
docker-compose -f deploy/local/docker-compose.yml up -d

# 检查服务状态
docker-compose -f deploy/local/docker-compose.yml ps
```

### 2. 安装依赖

```bash
# 安装 NPM 依赖
npm install

# 安装 Playwright 浏览器
npx playwright install --with-deps chromium
```

## 运行测试

### 方式一：使用运行脚本（推荐）

```bash
# 前台运行（可观察浏览器操作）
./run-dataops-e2e.sh

# 后台运行
HEADED=false ./run-dataops-e2e.sh
```

### 方式二：直接使用 Playwright

```bash
# 前台运行（显示浏览器）
npx playwright test data-ops-full-workflow.spec.ts --headed=true

# 后台运行
npx playwright test data-ops-full-workflow.spec.ts

# 指定项目运行
npx playwright test data-ops-full-workflow.spec.ts --project=chromium-fast
```

## 测试步骤说明

### 阶段 1: 数据接入

| 步骤 | 操作 | 验证点 |
|------|------|--------|
| 1.1 | 访问数据源管理页面 | 页面正常加载 |
| 1.2 | 打开新建数据源对话框 | 模态框显示 |
| 1.3 | 填写数据源配置 | 表单字段填写正确 |
| 1.4 | 测试数据源连接 | 连接测试执行 |
| 1.5 | 创建数据源 | 数据源创建成功 |

### 阶段 2: 数据处理 (ETL)

| 步骤 | 操作 | 验证点 |
|------|------|--------|
| 2.1 | 访问 ETL 管理页面 | 页面正常加载 |
| 2.2 | 创建 ETL 任务 | 任务创建表单显示 |
| 2.3 | 配置字段映射 | 映射配置界面显示 |

### 阶段 3: 数据治理

| 步骤 | 操作 | 验证点 |
|------|------|--------|
| 3.1 | 访问元数据管理页面 | 页面正常加载 |
| 3.2 | 浏览数据库和表结构 | 树形结构显示 |
| 3.3 | 执行 AI 智能标注 | AI 标注功能触发 |
| 3.4 | 执行敏感数据扫描 | 扫描功能执行 |
| 3.5 | 搜索表和字段 | 搜索功能可用 |

### 阶段 4: 数据利用

| 步骤 | 操作 | 验证点 |
|------|------|--------|
| 4.1 | 访问 Text-to-SQL 页面 | 页面正常加载 |
| 4.2 | 执行自然语言查询 | 查询功能执行 |
| 4.3 | 访问 BI 报表页面 | 页面正常加载 |
| 4.4 | 访问数据服务页面 | 页面正常加载 |

## 查看测试结果

### 测试报告

```bash
# 打开 HTML 报告
npx playwright show-report

# 或直接打开文件
open test-results/dataops/index.html
```

### 测试截图

```bash
# 查看截图目录
ls -la test-results/dataops/

# 预览截图
open test-results/dataops/*.png
```

### 控制台输出

测试执行时会在控制台输出每个步骤的执行状态：

```
✓ 步骤 1.1: 成功访问数据源管理页面
✓ 步骤 1.2: 成功打开新建数据源对话框
✓ 步骤 1.3: 成功填写数据源配置信息
...
```

## 环境变量配置

可选环境变量（默认值已配置）：

```bash
# 前端地址
export BASE_URL=http://localhost:3000

# 后端 API 地址
export API_BASE=http://localhost:8001

# 测试数据库配置
export TEST_MYSQL_HOST=mysql
export TEST_MYSQL_USER=root
export TEST_MYSQL_PASSWORD=your_password
export TEST_MYSQL_DATABASE=onedata
```

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| Docker 服务未启动 | `docker-compose -f deploy/local/docker-compose.yml up -d` |
| 前端服务未启动 | `cd web && npm run dev` |
| Playwright 浏览器未安装 | `npx playwright install --with-deps chromium` |
| 测试超时 | 增加超时时间: `--timeout=120000` |
| 后端 API 无响应 | 检查 `docker-compose ps` 和服务日志 |

## 手动验证

测试完成后，可以手动验证以下功能：

1. 访问 http://localhost:3000/data/datasources 查看数据源
2. 访问 http://localhost:3000/metadata 查看元数据
3. 访问 http://localhost:3000/data/etl 查看 ETL 任务
4. 访问 http://localhost:3000/data/bi 查看 BI 报表

## 持续集成

在 CI 环境中运行：

```yaml
# GitHub Actions 示例
- name: Run DataOps E2E Tests
  run: |
    docker-compose -f deploy/local/docker-compose.yml up -d
    npm install
    npx playwright install --with-deps chromium
    npx playwright test data-ops-full-workflow.spec.ts --headed=false
```

## 相关文档

- [DataOps 平台概述](../../01-architecture/platform-overview.md)
- [Data 与 Agent 集成](../../02-integration/data-agent.md)
- [测试计划](../../04-testing/test-plan.md)
