# 用户生命周期 E2E 测试

完整的用户生命周期端到端测试套件，覆盖用户从创建到删除的全过程。

## 目录结构

```
user-lifecycle/
├── fixtures/
│   ├── user-lifecycle.fixture.ts    # 用户生命周期管理 fixtures
│   └── test-data.fixture.ts         # 测试数据管理 fixtures
├── helpers/
│   ├── user-management.ts           # 用户管理 UI 操作
│   ├── role-management.ts           # 角色管理辅助函数
│   └── verification.ts              # 权限验证辅助函数
├── user-creation.spec.ts            # 用户创建测试
├── user-activation.spec.ts          # 用户激活测试
├── role-assignment.spec.ts          # 角色分配测试
├── permission-change.spec.ts        # 权限变更测试
├── user-status.spec.ts              # 用户状态管理测试
├── user-deletion.spec.ts            # 用户删除测试
├── role-access-matrix.spec.ts       # 角色权限矩阵测试
├── cross-role-functional.spec.ts    # 跨角色功能测试
└── user-lifecycle.spec.ts           # 全生命周期 E2E 测试
```

## 测试覆盖

### 用户生命周期阶段

| 阶段 | 状态 | 测试文件 |
|-----|------|---------|
| 创建阶段 | `pending` | `user-creation.spec.ts` |
| 激活阶段 | `active` | `user-activation.spec.ts` |
| 角色分配 | - | `role-assignment.spec.ts` |
| 日常使用 | `active` | `permission-change.spec.ts` |
| 权限变更 | - | `permission-change.spec.ts` |
| 停用阶段 | `inactive` | `user-status.spec.ts` |
| 锁定阶段 | `locked` | `user-status.spec.ts` |
| 删除阶段 | `deleted` | `user-deletion.spec.ts` |

### 角色覆盖

| 角色 | 测试数量 | 主要测试文件 |
|-----|---------|-------------|
| admin | 20+ | `role-access-matrix.spec.ts` |
| data_engineer | 20+ | `role-access-matrix.spec.ts` |
| ai_developer | 20+ | `role-access-matrix.spec.ts` |
| data_analyst | 15+ | `role-access-matrix.spec.ts` |
| user | 15+ | `role-access-matrix.spec.ts` |
| guest | 10+ | `role-access-matrix.spec.ts` |

## 运行测试

### 运行所有用户生命周期测试

```bash
# 有头模式（推荐）
npx playwright test --project=user-lifecycle

# 无头快速模式
npx playwright test --project=user-lifecycle-fast

# 使用运行脚本
cd tests/e2e/user-lifecycle
./scripts/run-tests.sh

# 生成 HTML 报告
./scripts/run-tests.sh -r html
```

### 运行特定测试套件

```bash
# 用户创建测试
npx playwright tests/e2e/user-lifecycle/user-creation.spec.ts

# 角色权限矩阵测试
npx playwright tests/e2e/user-lifecycle/role-access-matrix.spec.ts

# 全生命周期测试
npx playwright tests/e2e/user-lifecycle/user-lifecycle.spec.ts
```

### 测试用户初始化

```bash
# 创建测试用户
./scripts/setup-test-users.sh

# 清理测试用户
./scripts/cleanup-test-users.sh
```

### 生成测试报告

```bash
# HTML 报告
npx playwright test --project=user-lifecycle --reporter=html

# JSON 报告
npx playwright test --project=user-lifecycle --reporter=json

# JUnit 报告
npx playwright test --project=user-lifecycle --reporter=junit
```

## 环境变量

测试需要以下环境变量：

```bash
# 基础 URL
BASE_URL=http://localhost:3000

# API URLs
BISHENG_API_URL=http://localhost:8000
ALLDATA_API_URL=http://localhost:8001
CUBE_API_URL=http://localhost:8002
OPENAI_API_URL=http://localhost:8003

# 认证
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=one-data-studio
KEYCLOAK_CLIENT_ID=web-frontend
```

## 测试数据

测试使用以下预定义的测试用户：

| 用户名 | 角色 | 状态 | 用途 |
|-------|------|------|------|
| test_admin | admin | active | 管理员操作 |
| test_de | data_engineer | active | 数据工程师测试 |
| test_ai | ai_developer | active | AI 开发者测试 |
| test_da | data_analyst | active | 数据分析师测试 |
| test_user | user | active | 普通用户测试 |
| test_guest | guest | active | 访客测试 |
| test_pending | user | pending | 待激活用户 |
| test_inactive | user | inactive | 停用用户 |
| test_locked | user | locked | 锁定用户 |
| test_deleted | user | deleted | 已删除用户 |

## API 覆盖

测试覆盖以下 API 端点：

- `POST /api/v1/users` - 创建用户
- `GET /api/v1/users` - 获取用户列表
- `GET /api/v1/users/{id}` - 获取用户详情
- `PUT /api/v1/users/{id}` - 更新用户
- `DELETE /api/v1/users/{id}` - 删除用户
- `POST /api/v1/users/{id}/roles` - 分配角色
- `DELETE /api/v1/users/{id}/roles/{role_id}` - 撤销角色
- `POST /api/v1/users/{id}/activate` - 激活用户
- `POST /api/v1/users/{id}/deactivate` - 停用用户
- `POST /api/v1/users/{id}/unlock` - 解锁用户

## 前端路由覆盖

测试覆盖以下前端路由：

### 管理模块
- `/admin/users` - 用户管理
- `/admin/roles` - 角色管理
- `/admin/groups` - 用户组管理
- `/admin/audit` - 审计日志
- `/admin/settings` - 系统设置

### 数据管理模块
- `/data/datasources` - 数据源
- `/data/datasets` - 数据集
- `/data/metadata` - 元数据
- `/data/features` - 特征存储
- `/data/standards` - 数据标准
- `/data/lineage` - 数据血缘
- `/data/quality` - 数据质量

### 开发模块
- `/development/notebook` - Notebook
- `/development/sql-lab` - SQL Lab
- `/development/etl` - ETL 任务

### AI 应用模块
- `/ai/chat` - AI 对话
- `/ai/workflows` - 工作流
- `/ai/prompts` - Prompt 管理
- `/ai/knowledge` - 知识库
- `/ai/agents` - Agent

## 维护指南

### 添加新测试

1. 在对应的 `.spec.ts` 文件中添加测试用例
2. 使用 `test.describe` 组织相关测试
3. 使用适当的 fixtures 和 helpers

### 修改测试数据

编辑 `fixtures/user-lifecycle.fixture.ts` 中的 `TEST_USERS` 对象。

### 扩展角色权限

编辑 `helpers/role-management.ts` 中的 `ROLE_PERMISSIONS` 配置。

## 故障排查

### 测试失败

1. 检查环境变量是否正确设置
2. 确认后端服务正在运行
3. 查看测试报告中的截图和视频

### 超时错误

增加测试超时时间：

```typescript
test.setTimeout(120000); // 2分钟
```

### 认证问题

确保 Keycloak 服务正常运行，测试用户已创建。
