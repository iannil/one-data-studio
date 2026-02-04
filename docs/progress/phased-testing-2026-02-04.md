# 分阶段测试计划实施报告

> **日期**: 2026-02-04
> **目的**: 记录分阶段测试计划的实施过程和成果

---

## 一、实施背景

### 硬件限制

```
内存: 16 GB
CPU: 8 核
存储: 926 GB (105 GB 可用)
平台: macOS (Darwin 25.2.0)
```

**问题**: 服务全量启动需要约 18-43GB 内存，无法在当前环境一次性启动全部服务。

**解决方案**: 实施分阶段测试计划，按服务依赖关系和内存占用分组测试。

---

## 二、实施内容

### 2.1 创建的文件

| 文件路径 | 说明 | 大小 |
|----------|------|------|
| `deploy/local/.env.example` | 环境变量模板 | 3.2 KB |
| `deploy/local/test-phased.sh` | 分阶段测试脚本 | 15.4 KB |
| `tests/integration/test_phase1_infrastructure.py` | 阶段1: 基础设施测试 | 20.3 KB |
| `tests/integration/test_phase2_metadata.py` | 阶段2: 元数据服务测试 | 35.5 KB |
| `tests/integration/test_phase3_apis.py` | 阶段3: API服务测试 | 26.1 KB |
| `tests/integration/test_phase4_agent.py` | 阶段4: Agent/模型测试 | 25.7 KB |
| `tests/integration/test_phase5_frontend.py` | 阶段5: 前端集成测试 | 20.4 KB |
| `tests/integration/test_phase6_extensions.py` | 阶段6: 扩展服务测试 | 21.4 KB |
| `docs/07-operations/phased-testing-guide.md` | 测试指南文档 | 12.8 KB |

**总计**: 9 个文件，约 180.8 KB

### 2.2 服务分组

| 组别 | 内存 | 服务 | 端口 |
|------|------|------|------|
| A 组 | ~4GB | mysql, redis, minio | 3306, 6379, 9000/9001 |
| B 组 | ~3.5GB | etcd, milvus, elasticsearch, openmetadata | 2379, 19530, 9200, 8585 |
| C 组 | ~2GB | data-api, admin-api, openai-proxy | 8001, 8004, 8003 |
| D 组 | ~1.5GB | agent-api, model-api | 8000, 8002 |
| E 组 | ~128MB | web-frontend | 3000 |
| F 组 | ~2.5GB | ocr-service, behavior-service, keycloak | 8007, 8008, 8080 |
| G 组 | ~6GB+ | kettle, superset, dolphinscheduler | 8088, 12345 |

---

## 三、测试脚本功能

### 3.1 test-phased.sh 主要功能

```bash
# 基本用法
./test-phased.sh [1-7|all|clean|status]

# 功能特性
- 自动健康检查等待
- 服务状态记录
- 内存使用监控
- 日志目录自动创建
- 彩色输出和进度提示
```

### 3.2 阶段定义

| 阶段 | 命令 | 包含服务 | 内存预估 |
|------|------|----------|----------|
| 阶段1 | `./test-phased.sh 1` | A 组 | ~4GB |
| 阶段2 | `./test-phased.sh 2` | A+B 组 | ~7.5GB |
| 阶段3 | `./test-phased.sh 3` | A+B+C 组 | ~9.5GB |
| 阶段4 | `./test-phased.sh 4` | A+B+C+D 组 | ~11GB |
| 阶段5 | `./test-phased.sh 5` | A+B+C+D+E 组 | ~11.1GB |
| 阶段6 | `./test-phased.sh 6` | 需停止部分服务 | ~9GB |
| 全部 | `./test-phased.sh all` | 阶段1-5 | ~11.1GB |

---

## 四、测试用例统计

### 4.1 各阶段测试用例数量

| 阶段 | 测试类 | 测试用例数 |
|------|--------|-----------|
| 阶段1 | 5 | 25 |
| 阶段2 | 5 | 35 |
| 阶段3 | 5 | 40 |
| 阶段4 | 5 | 40 |
| 阶段5 | 5 | 35 |
| 阶段6 | 4 | 30 |
| **合计** | **29** | **205** |

### 4.2 测试覆盖范围

**基础设施** (阶段1):
- MySQL 连接、事务、字符集、中文支持
- Redis 数据结构、过期时间、管道
- MinIO bucket、对象上传下载、预签名URL

**元数据服务** (阶段2):
- etcd 键值存储
- Milvus 集合、索引、向量搜索
- Elasticsearch 索引、搜索、聚合
- OpenMetadata 版本、配置

**API 服务** (阶段3):
- data-api 数据源、元数据、ETL
- admin-api 用户、角色、权限
- openai-proxy 模型路由、并发

**Agent/模型** (阶段4):
- agent-api 工作流、知识库、Agent
- model-api 模型、部署、训练

**前端集成** (阶段5):
- 页面访问、静态资源、CORS
- 前后端集成、WebSocket
- 可访问性测试

**扩展服务** (阶段6):
- OCR 文档识别
- 行为分析追踪
- Keycloak 认证

---

## 五、文档更新

### 5.1 新建文档

- `docs/07-operations/phased-testing-guide.md` - 完整测试指南

### 5.2 更新文档

- `docs/07-operations/README.md` - 添加快速开始和分阶段测试链接
- `docs/03-progress/current-status.md` - 更新进度记录
- `docs/03-progress/tech-debt.md` - 添加 Sprint 34 任务

---

## 六、使用示例

### 6.1 基本使用

```bash
# 1. 配置环境
cd deploy/local
cp .env.example .env
vim .env  # 修改密码

# 2. 运行阶段1测试
./test-phased.sh 1

# 3. 查看日志
ls -la test-logs/
cat test-logs/*/test.log

# 4. 清理环境
./test-phased.sh clean
```

### 6.2 运行特定阶段测试

```bash
# 仅测试基础设施
pytest tests/integration/test_phase1_infrastructure.py -v

# 仅测试元数据服务
pytest tests/integration/test_phase2_metadata.py -v

# 运行所有阶段测试
pytest tests/integration/test_phase*.py -v
```

---

## 七、下一步

1. **执行测试**: 在实际环境中运行测试并记录结果
2. **修复问题**: 根据测试结果修复发现的问题
3. **完善文档**: 补充测试结果和常见问题
4. **自动化 CI/CD**: 将测试集成到 CI/CD 流程

---

## 八、文件清单

### 实施文件

```
deploy/local/
├── .env.example           # 环境变量模板
└── test-phased.sh         # 测试脚本 (可执行)

tests/integration/
├── test_phase1_infrastructure.py
├── test_phase2_metadata.py
├── test_phase3_apis.py
├── test_phase4_agent.py
├── test_phase5_frontend.py
└── test_phase6_extensions.py

docs/07-operations/
└── phased-testing-guide.md
```

### 文档更新

```
docs/
├── 03-progress/
│   ├── current-status.md  # 更新
│   └── tech-debt.md       # 更新
└── 07-operations/
    └── README.md          # 更新
```

---

## 九、总结

本次实施完成了分阶段测试计划的全部基础内容：

1. ✅ 环境变量模板 (.env.example)
2. ✅ 自动化测试脚本 (test-phased.sh)
3. ✅ 6 个阶段的集成测试文件
4. ✅ 完整的测试指南文档
5. ✅ 相关文档更新

**成果**: 为资源受限环境提供了一套完整的分阶段测试解决方案，确保在 16GB 内存下可以验证所有核心功能。
