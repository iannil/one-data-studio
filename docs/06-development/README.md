# 开发文档

本目录包含开发指南和参考文档。

## 文档列表

| 文档 | 描述 |
|------|------|
| [API 测试指南](./api-testing-guide.md) | API 接口测试方法和示例 |
| [演示指南](./demo-guide.md) | 系统演示步骤和脚本 |
| [环境检查清单](./environment-checklist.md) | 开发环境配置检查项 |
| [POC 手册](./poc-playbook.md) | 概念验证实施手册 |
| [迭代计划](./sprint-plan.md) | 当前迭代任务和目标 |
| [K8s 故障排查](./troubleshooting-k8s.md) | Kubernetes 常见问题排查 |

## 快速开始

```bash
# 启动开发环境
docker-compose -f deploy/local/docker-compose.yml up -d

# 启动前端开发服务器
cd web && npm install && npm run dev
```
