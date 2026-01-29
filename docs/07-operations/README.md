# 运维文档

本目录包含系统运维和部署相关的文档。

## 文档列表

| 文档 | 描述 |
|------|------|
| [部署指南](./deployment.md) | 生产环境部署步骤 |
| [灾难恢复](./disaster-recovery.md) | 灾难恢复流程和计划 |
| [运维指南](./operations-guide.md) | 日常运维操作手册 |
| [性能调优](./performance-tuning.md) | 系统性能优化建议 |
| [安全加固](./security-hardening.md) | 安全加固配置指南 |
| [安全扫描报告](./security-scan-report.md) | 安全漏洞扫描结果 |
| [安全概览](./security-overview.md) | 安全策略与配置总览 |
| [Docker 故障排查](./troubleshooting-docker.md) | Docker 相关问题排查 |
| [故障排查](./troubleshooting.md) | 通用故障排查指南 |

## 部署架构

```
┌─────────────────────────────────────────┐
│            Nginx (端口 80/443)           │
├─────────────────────────────────────────┤
│ data-api │ agent-api │ openai-proxy│
├─────────────────────────────────────────┤
│         PostgreSQL / MinIO / Redis       │
└─────────────────────────────────────────┘
```
