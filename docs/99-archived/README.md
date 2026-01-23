# 归档文档

本目录存放 ONE-DATA-STUDIO 项目的归档内容。

---

## 目录结构

```
99-archived/
├── README.md                    # 本文件
├── mock-services/               # 归档的 Mock 服务配置
│   ├── alldata-api-mock.yaml    # Alldata API Mock 服务（已迁移至真实 API）
│   └── bisheng-api-mock.yaml    # Bisheng API Mock 服务（已迁移至真实 API）
└── deprecated/                  # 存放过时的文档和配置
```

---

## Mock 服务归档说明

### alldata-api-mock.yaml

**归档日期**: 2025-01-23

**归档原因**: Alldata API 真实服务已实现完成，Mock 服务不再需要。

**替代方案**: 使用 `docker/alldata-api/` 中的真实 API 服务。

---

### bisheng-api-mock.yaml

**归档日期**: 2025-01-23

**归档原因**: Bisheng API 真实服务已实现完成，Mock 服务不再需要。

**替代方案**: 使用 `docker/bisheng-api/` 中的真实 API 服务。

---

## 如何使用归档内容

归档文件仅供参考和历史记录用途。如需恢复 Mock 服务用于测试，可以：

1. 复制文件到 `k8s/applications/` 目录
2. 使用 `kubectl apply -f` 部署

---

## 联系方式

如有问题，请查看项目主文档或提 Issue。
