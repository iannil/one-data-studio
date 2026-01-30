# 文档命名规范

> 本文档定义项目中各类文档的命名规则。

---

## 一、通用规则

1. **使用英文小写字母**
2. **单词之间用连字符 (`-`) 分隔**
3. **不使用空格、下划线或特殊字符**
4. **文件扩展名使用 `.md`**

---

## 二、按文档类型分类

### 2.1 进度文档

**位置**：`/docs/progress/`

**格式**：`{模块}-{功能描述}.md`

**示例**：
- `agent-api-vector-search.md`
- `web-chat-history.md`
- `data-api-metadata-sync.md`

### 2.2 完成报告

**位置**：`/docs/reports/completed/`

**格式**：`{模块}-{功能描述}-{YYYY-MM-DD}.md`

**示例**：
- `agent-api-vector-search-2026-01-30.md`
- `web-chat-history-2026-02-01.md`

### 2.3 项目状态报告

**位置**：`/docs/reports/`

**格式**：`project-status-{YYYY-MM-DD}.md`

**示例**：
- `project-status-2026-01-30.md`
- `project-status-2026-02-01.md`

### 2.4 验收报告

**位置**：`/docs/reports/`

**格式**：`{模块}-acceptance-{YYYY-MM-DD}.md`

**示例**：
- `agent-api-acceptance-2026-01-30.md`
- `web-acceptance-2026-02-01.md`

### 2.5 技术文档

**位置**：按主题分类在对应目录

**格式**：`{主题描述}.md`

**示例**：
- `platform-overview.md` (在 `01-architecture/`)
- `api-specifications.md` (在 `02-integration/`)
- `test-plan.md` (在 `04-testing/`)

---

## 三、模块命名映射

| 模块标识 | 对应服务/组件 |
|----------|---------------|
| `agent-api` | Agent API 服务 |
| `data-api` | Data API 服务 |
| `openai-proxy` | OpenAI 兼容代理 |
| `admin-api` | 管理后台 API |
| `model-api` | MLOps 模型管理 |
| `ocr-service` | OCR 文档识别 |
| `behavior-service` | 用户行为分析 |
| `web` | 前端应用 |
| `deploy` | 部署配置 |
| `shared` | 共享模块 |

---

## 四、日期格式

- **标准格式**：`YYYY-MM-DD`（如 `2026-01-30`）
- **用于文件名时**：不使用分隔符，直接连接（如 `20260130`）或使用连字符
- **推荐**：使用连字符格式 `2026-01-30`

---

## 五、禁止使用

- 中文字符（文件名中）
- 空格
- 下划线 `_`
- 驼峰命名 (`camelCase`)
- 大写字母

---

> 更新时间：2026-01-30
