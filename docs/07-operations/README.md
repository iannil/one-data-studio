# 运维文档

本目录包含系统运维和部署相关的文档。

## 文档列表

| 文档 | 描述 |
|------|------|
| [硬件要求](./hardware-requirements.md) | 开发环境硬件配置评估 |
| [部署指南](./deployment.md) | 生产环境部署步骤 |
| [分阶段测试指南](./phased-testing-guide.md) | 资源受限环境下的分阶段测试 |
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

## 快速开始

### 1. 配置环境

```bash
cd deploy/local
cp .env.example .env
# 编辑 .env 文件设置必要的密码
```

### 2. 分阶段测试（适用于 16GB 内存）

```bash
# 运行测试脚本
chmod +x test-phased.sh
./test-phased.sh all    # 运行全部阶段
./test-phased.sh 1      # 仅阶段 1
./test-phased.sh status # 查看状态
```

详细说明请参考 [分阶段测试指南](./phased-testing-guide.md)。
