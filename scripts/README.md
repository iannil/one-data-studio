# ONE-DATA-STUDIO 运维脚本

本目录包含生产环境运维相关的脚本。

## 脚本说明

| 脚本 | 说明 |
|------|------|
| `disaster-recovery.sh` | 灾难恢复脚本 |
| `rotate-encryption-keys.sh` | 加密密钥轮换 |
| `rotate-secrets.sh` | 密钥轮换 |

## 部署相关脚本

部署相关的脚本已移至 `/deploy/scripts/` 目录：
- `deploy-phase1.sh` - 基础设施部署
- `deploy-phase2.sh` - 应用服务部署
- `deploy-all.sh` - 完整部署
- `clean.sh` - 资源清理
- `test-all.sh` - 集成测试
- `test-e2e.sh` - 端到端测试
- `port-forward.sh` - 端口转发
- `install-kind.sh` - Kind 集群安装
- `validate-secrets.sh` - 密钥验证

## 使用方法

```bash
# 灾难恢复
./scripts/disaster-recovery.sh restore

# 密钥轮换
./scripts/rotate-secrets.sh
```
