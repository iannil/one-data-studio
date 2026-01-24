# ONE-DATA-STUDIO 部署脚本

本目录包含部署和测试相关的脚本。

## 脚本说明

### 部署脚本

| 脚本 | 说明 |
|------|------|
| `deploy-phase1.sh` | 阶段1: 基础设施部署 (数据库、存储) |
| `deploy-phase2.sh` | 阶段2: 应用服务部署 |
| `deploy-all.sh` | 完整部署 (phase1 + phase2) |
| `deploy.sh` | 通用部署脚本 |
| `rollback.sh` | 回滚部署 |
| `blue-green-deploy.sh` | 蓝绿部署 |

### 清理脚本

| 脚本 | 说明 |
|------|------|
| `clean.sh` | 清理所有 K8s 资源 |

### 测试脚本

| 脚本 | 说明 |
|------|------|
| `test-all.sh` | 运行所有集成测试 |
| `test-e2e.sh` | 端到端测试 |

### 辅助脚本

| 脚本 | 说明 |
|------|------|
| `install-kind.sh` | 安装 Kind 本地 K8s 集群 |
| `port-forward.sh` | 启动端口转发 |
| `validate-secrets.sh` | 验证密钥配置 |

## 使用方法

```bash
# 完整部署
cd deploy/scripts
./deploy-all.sh

# 清理资源
./clean.sh

# 运行测试
./test-all.sh

# 端口转发
./port-forward.sh
```

## 运维脚本

运维相关脚本（灾难恢复、密钥轮换）位于 `/scripts/` 目录。
