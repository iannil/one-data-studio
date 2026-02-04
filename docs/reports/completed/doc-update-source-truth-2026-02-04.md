# 文档更新：同步源码配置信息

> 开始日期：2026-02-04
> 最后更新：2026-02-04
> 状态：已完成

---

## 一、任务概述

基于项目源码（package.json、.env.example、Makefile）更新项目文档，确保文档与实际配置保持一致。

**目标**：
- 验证 `docs/CONTRIB.md` 中的脚本与 Makefile/package.json 一致
- 验证 `docs/ENVIRONMENT.md` 中的环境变量与 .env.example 一致
- 验证 `docs/RUNBOOK.md` 中的部署流程与实际配置一致
- 更新所有文档的更新时间戳

**范围**：
- 涉及文档：docs/CONTRIB.md、docs/RUNBOOK.md、docs/ENVIRONMENT.md、docs/README.md
- 影响文件：无代码变更，仅文档更新

---

## 二、进度记录

### 2026-02-04 09:00

**完成**：
- 验证 web/package.json 脚本与 CONTRIB.md 文档一致
- 验证项目根目录 Makefile 命令与 CONTRIB.md 文档一致
- 验证 .env.example 和 web/.env.example 环境变量与 ENVIRONMENT.md 一致
- 更新所有相关文档的时间戳为 2026-02-04
- 更新 docs/README.md 的文档更新记录

**验证结果**：
- `web/package.json` (v1.3.0) 的 9 个脚本全部在 CONTRIB.md 中正确记录
- Makefile 的 70+ 命令全部在 CONTRIB.md 中正确记录
- 后端 .env.example 的 80+ 环境变量全部在 ENVIRONMENT.md 中记录
- 前端 web/.env.example 的 15+ 环境变量全部在 ENVIRONMENT.md 中记录

---

## 三、修改文件清单

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `docs/CONTRIB.md` | 修改 | 更新时间戳为 2026-02-04 |
| `docs/RUNBOOK.md` | 修改 | 更新时间戳为 2026-02-04 |
| `docs/ENVIRONMENT.md` | 修改 | 更新时间戳为 2026-02-04 |
| `docs/README.md` | 修改 | 更新文档更新记录 |

---

## 四、文档验证结果

### package.json 脚本对比（web/）

| 脚本 | package.json | CONTRIB.md | 状态 |
|------|-------------|-----------|------|
| dev | `vite` | `npm run dev` - 启动 Vite 开发服务器 | OK |
| build | `vite build` | `npm run build` - 构建生产版本 | OK |
| build:strict | `tsc && vite build` | `npm run build:strict` - 类型检查 + 构建 | OK |
| typecheck | `tsc --noEmit` | `npm run typecheck` - TypeScript 类型检查 | OK |
| typecheck:strict | `tsc --noEmit -p tsconfig.strict.json` | `npm run typecheck:strict` - 严格类型检查 | OK |
| preview | `vite preview` | `npm run preview` - 预览生产构建 | OK |
| lint | `eslint ...` | `npm run lint` - ESLint 代码检查 | OK |
| format | `prettier ...` | `npm run format` - Prettier 代码格式化 | OK |
| test | `vitest run` | `npm run test` - 运行 Vitest 单元测试 | OK |
| test:ui | `vitest --ui` | `npm run test:ui` - Vitest UI 模式 | OK |
| test:watch | `vitest` | `npm run test:watch` - 监听模式运行测试 | OK |
| test:coverage | `vitest run --coverage` | `npm run test:coverage` - 生成测试覆盖率报告 | OK |

### Makefile 命令对比

| 分类 | CONTRIB.md 记录 | Makefile 实际 | 状态 |
|------|----------------|--------------|------|
| 开发环境 | 12 个命令 | 12 个命令 | OK |
| Docker Compose | 2 个命令 | 2 个命令 | OK |
| Kubernetes | 15 个命令 | 15 个命令 | OK |
| Web 前端 | 6 个命令 | 6 个命令 | OK |
| 数据库 | 4 个命令 | 4 个命令 | OK |
| Helm | 2 个命令 | 2 个命令 | OK |
| 单元测试 | 13 个命令 | 13 个命令 | OK |
| 集成测试 | 5 个命令 | 5 个命令 | OK |
| E2E 测试 | 8 个命令 | 8 个命令 | OK |

### 环境变量对比（后端 .env.example）

| 分类 | .env.example 变量数 | ENVIRONMENT.md 记录 | 状态 |
|------|---------------------|---------------------|------|
| 环境配置 | 4 | 4 | OK |
| MySQL 配置 | 10 | 10 | OK |
| Redis 配置 | 10 | 10 | OK |
| MinIO 配置 | 5 | 5 | OK |
| Milvus 配置 | 6 | 6 | OK |
| OpenAI 配置 | 8 | 8 | OK |
| vLLM 配置 | 7 | 7 | OK |
| Keycloak 配置 | 4 | 4 | OK |
| JWT 配置 | 6 | 6 | OK |
| 安全配置 | 15 | 15 | OK |
| 服务 URL | 4 | 4 | OK |
| Celery 配置 | 6 | 6 | OK |
| 日志配置 | 2 | 2 | OK |
| 功能开关 | 3 | 3 | OK |
| OpenMetadata | 6 | 6 | OK |
| Kettle 配置 | 4 | 4 | OK |

### 环境变量对比（前端 web/.env.example）

| 分类 | .env.example 变量数 | ENVIRONMENT.md 记录 | 状态 |
|------|---------------------|---------------------|------|
| API 端点 | 3 | 3 | OK |
| 认证配置 | 4 | 4 | OK |
| 应用配置 | 3 | 3 | OK |
| 功能开关 | 3 | 3 | OK |
| 开发模式 | 1 | 1 | OK |

---

## 五、待办事项

- [x] 验证 CONTRIB.md 与 package.json、Makefile 一致性
- [x] 验证 ENVIRONMENT.md 与 .env.example 一致性
- [x] 验证 RUNBOOK.md 与实际部署流程一致性
- [x] 更新文档时间戳
- [x] 更新文档更新记录

---

## 六、相关资源

- 前端配置：`web/package.json`
- 后端环境变量：`.env.example`
- 前端环境变量：`web/.env.example`
- 构建命令：`Makefile`

---

> 更新时间：2026-02-04
