# 归档文档

本目录存放 ONE-DATA-STUDIO 项目的归档内容。

---

## 目录结构

```
99-archived/
├── README.md                    # 本文件
├── helm-chart-backup/           # Helm Chart 备份
├── k8s-config-backup/           # K8s 配置备份
├── testing-2025/                # 2025 年测试文档归档
├── status-reports/              # 历史项目状态报告
│   └── project-status-2026-01-30.md
└── progress-reports/            # 历史进展报告
    └── project-progress-2026-02-09.md
```

---

## 归档文档说明

### status-reports/

历史项目状态报告，已被最新的 `docs/PROJECT_STATUS.md` 替代。

| 文件 | 归档日期 | 原因 |
|------|----------|------|
| `project-status-2026-01-30.md` | 2026-02-12 | 被更新的 PROJECT_STATUS.md (2026-02-12) 替代 |

### progress-reports/

历史进展报告，内容已整合到 `docs/PROJECT_STATUS.md`。

| 文件 | 归档日期 | 原因 |
|------|----------|------|
| `project-progress-2026-02-09.md` | 2026-02-12 | 内容已整合，避免重复 |

### current-status-2026-02-04-archived.md

2026-02-04 的项目状态快照，保留作为历史参考。

---

## 已删除的归档内容

### mock-services/ (已删除)

**删除日期**: 2025-01-24

**删除原因**:
- Data API 真实服务已实现完成 (`services/data-api/`)
- Agent API 真实服务已实现完成 (`services/agent-api/`)
- Mock 服务不再需要，已被真实 API 替代

**原包含文件**:
- `data-api-mock.yaml` - Data API Mock 服务配置
- `agent-api-mock.yaml` - Agent API Mock 服务配置

**替代方案**: 使用 `services/data-api/` 和 `services/agent-api/` 中的真实 API 服务。

### code-audit-2026-01-28.md (已删除)

**删除日期**: 2026-01-29

**删除原因**:
- 内容已完整合并到 `docs/03-progress/current-status.md`
- 避免重复维护，减少文档冗余

**替代方案**: 使用 `docs/03-progress/current-status.md` 和 `docs/03-progress/tech-debt.md` 作为代码状态和技术债务追踪。

### FEATURES-2.md (已删除)

**删除日期**: 2026-01-29

**删除原因**:
- 与 `docs/FEATURES.md` (现已移动到 `docs/00-project/features.md`) 内容重复
- FEATURES.md 更完整（包含完成度百分比）

**替代方案**: 使用 `docs/00-project/features.md` 作为功能清单。

---

## 归档文档说明

### implementation-status.md (已删除)

**归档日期**: 2025-01-24

**归档原因**:
- 内容已合并到 `docs/03-progress/current-status.md`
- 避免重复维护两份进度文档

**替代方案**: 使用 `docs/03-progress/current-status.md` 作为唯一进度追踪文档。

### testing-2025/ (已归档)

**归档日期**: 2026-01-29

**归档原因**:
- 过时的测试执行报告和改进文档
- 测试功能已完成，这些是临时报告文档

**包含文件**:
- `test-final-improvements.md` - 最终改进建议（已过时）
- `test-final-report.md` - 最终测试报告（已过时）
- `test-final-summary.md` - 最终测试总结（已过时）
- `test-fix-summary.md` - 修复总结（已过时）
- `test-improvement-summary.md` - 改进总结（已过时）
- `test-execution-report.md` - 执行报告（已过时）
- `final-test-summary.md` - 测试总结（已过时）

**替代方案**: 使用 `docs/04-testing/test-plan.md` 和 `docs/04-testing/final-improvements.md` 作为当前测试文档。

---

## 如何恢复归档内容

归档文件仅供参考和历史记录用途。如需恢复，可以从 Git 历史记录中获取：

```bash
# 查看 Git 历史中的文件
git log --all --full-history -- docs/99-archived/

# 恢复特定版本的文件
git checkout <commit-hash> -- docs/99-archived/<file>
```

---

## 更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-02-12 | 添加 status-reports/ 和 progress-reports/ 归档说明 |
| 2026-02-12 | 归档 project-status-2026-01-30.md 和 project-progress-2026-02-09.md |
| 2026-01-29 | 删除 code-audit-2026-01-28.md（内容已合并到 current-status.md）|
| 2026-01-29 | 记录 FEATURES-2.md 删除（重复内容）|
| 2026-01-29 | 更新目录结构说明 |
| 2025-01-24 | 删除 mock-services/ 目录 |
| 2025-01-24 | 删除 implementation-status.md |

---

## 联系方式

如有问题，请查看项目主文档或提 Issue。
