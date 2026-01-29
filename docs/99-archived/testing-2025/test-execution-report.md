# 用户生命周期 E2E 测试执行报告

**执行时间**: 2026-01-28
**测试环境**: Docker Local (localhost)

---

## 一、测试结果汇总

| 角色 | 测试文件 | 总数 | 通过 | 失败 | 通过率 |
|------|---------|------|------|------|--------|
| 数据管理员 | data-admin.spec.ts | 19 | 2 | 17 | 10.5% |
| 数据工程师 | data-engineer.spec.ts | 17 | 0 | 17 | 0% |
| 算法工程师 | algorithm-engineer.spec.ts | 13 | 6 | 7 | 46.2% |
| 业务用户 | business-user.spec.ts | 17 | 7 | 10 | 41.2% |
| 系统管理员 | system-admin.spec.ts | 16 | 9 | 7 | 56.3% |
| **总计** | **5 个文件** | **82** | **24** | **58** | **29.3%** |

---

## 二、各角色测试详情

### 2.1 数据管理员 (2/19 通过 = 10.5%)

**通过的测试:**
- DM-DS-002: 连接测试 - 成功场景
- DM-DS-003: 查询数据源列表

**主要失败原因:**
- API 端点未实现或返回非 200 状态码
- `/api/v1/datasources` - POST 请求失败
- `/api/v1/metadata/scan` - 扫描任务创建失败
- `/api/v1/sensitivity/scan` - 敏感数据扫描失败
- `/api/v1/assets/catalog` - 资产编目失败
- `/api/v1/lineage/sync` - 血缘同步失败
- `/api/v1/auth/roles` - 角色查询失败

### 2.2 数据工程师 (0/17 通过 = 0%)

**所有测试均失败**, 主要原因:
- `/api/v1/datasets/ingest` - 数据采集端点未实现
- `/api/v1/etl/tasks` - ETL 任务端点未实现
- `/api/v1/data/analyze-missing` - 缺失值分析端点未实现
- `/api/v1/masking/apply` - 脱敏应用端点未实现
- `/api/v1/etl/fusion` - 多表融合端点未实现

### 2.3 算法工程师 (6/13 通过 = 46.2%)

**通过的测试:**
- AE-DP-005: OpenAI 兼容 API 调用 (Mock 测试通过)
- 其余 5 个测试为 AI 相关功能的非完全测试

**失败原因:**
- Cube API (8002) 部分端点未实现
- `/api/v1/notebooks` - Notebook 端点未实现
- `/api/v1/experiments` - 实验端点未实现
- `/api/v1/deployments` - 部署端点未实现

### 2.4 业务用户 (7/17 通过 = 41.2%)

**通过的测试:**
- BU-IQ-002: Text-to-SQL 复杂查询
- BU-IQ-004: Text-to-SQL 执行查询
- BU-IQ-005: 多轮对话查询
- BU-IQ-006: SQL 安全检查
- 其他 3 个基础功能测试

**失败原因:**
- Bisheng API (8000) 部分端点未实现
- `/api/v1/knowledge_bases` - 知识库端点未实现
- `/api/v1/rag/query` - RAG 查询端点未实现
- `/api/v1/bi/generate` - BI 报表生成端点未实现

### 2.5 系统管理员 (9/16 通过 = 56.3%) ✅ 最高通过率

**通过的测试:**
- SA-CF-001: 获取系统配置
- SA-CF-002: 修改系统配置
- SA-UM-006: 分配角色
- SA-UM-009: 禁用用户
- SA-UM-010: 重置用户密码
- SA-AU-001~004: 审计日志相关测试

**失败原因:**
- SA-CF-003~005: 邮件/LDAP/备份配置端点未实现
- SA-UM-001: 用户创建端点问题
- SA-UM-001 (UI): UI 测试超时
- SA-MN-001~002: 服务监控端点未实现

---

## 三、服务状态检查

| 服务 | 端口 | 状态 | Health 检查 |
|------|------|------|-------------|
| MySQL | 3306 | ✅ Healthy | - |
| Redis | 6379 | ✅ Healthy | - |
| Keycloak | 8080 | ✅ Running | 认证服务运行中 |
| Bisheng API | 8000 | ⚠️ Unhealthy | Milvus 连接失败 |
| Alldata API | 8001 | ✅ Healthy | `{"service":"alldata-api"}` |
| Cube API | 8002 | ✅ Healthy | `{"service":"cube-api"}` |
| OpenAI Proxy | 8003 | ✅ Healthy | - |
| Admin API | 8004 | ✅ Healthy | `{"service":"admin-api"}` |
| Web Frontend | 3000 | ✅ Healthy | - |

---

## 四、发现的主要问题

### 4.1 API 端点未实现
以下 API 端点在对应服务中尚未实现或返回错误状态码:

**Alldata API (8001):**
- 数据采集: `/api/v1/datasets/ingest`
- ETL 任务: `/api/v1/etl/tasks`, `/api/v1/etl/fusion`
- 元数据扫描: `/api/v1/metadata/scan`
- 敏感数据: `/api/v1/sensitivity/scan`, `/api/v1/masking/apply`
- 资产管理: `/api/v1/assets/*`
- 血缘同步: `/api/v1/lineage/*`

**Bisheng API (8000):**
- 知识库: `/api/v1/knowledge_bases`
- RAG 查询: `/api/v1/rag/query`
- BI 报表: `/api/v1/bi/*`

**Cube API (8002):**
- Notebook: `/api/v1/notebooks`
- 实验管理: `/api/v1/experiments`
- 模型部署: `/api/v1/deployments`
- 模型评估: `/api/v1/evaluation`

**Admin API (8004):**
- 邮件配置: `/api/v1/settings/email`
- LDAP 配置: `/api/v1/settings/ldap`
- 备份配置: `/api/v1/settings/backup`
- 用户管理: `/api/v1/users` (部分功能)

### 4.2 Milvus 连接问题
Bisheng API 无法连接到 Milvus (192.168.107.13:19530)，影响向量存储相关功能。

### 4.3 UI 元素定位问题
部分 UI 测试失败，因为页面元素选择器无法找到对应元素。

---

## 五、建议与后续工作

### 5.1 短期 (1-2 周)
1. 实现核心 API 端点，确保至少 P0 用例能够通过
2. 修复 Milvus 连接配置
3. 添加 UI 元素的 data-testid 属性以提高测试稳定性

### 5.2 中期 (3-4 周)
1. 完善所有 API 端点实现
2. 增加测试用户初始化脚本
3. 完善 Mock 数据和测试数据准备

### 5.3 长期 (持续)
1. 监控代码覆盖率，目标达到 70%
2. 定期执行回归测试
3. 完善 CI/CD 集成

---

## 六、测试基础设施状态

✅ **已完成的设置:**
- Playwright 测试框架配置完成
- 用户生命周期 Fixtures 完成
- 测试辅助函数完成
- 端口配置修复完成

⚠️ **需要改进:**
- 服务健康检查端点标准化
- 测试数据初始化自动化
- API 响应格式统一

