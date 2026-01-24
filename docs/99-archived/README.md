# 归档文档

本目录存放 ONE-DATA-STUDIO 项目的归档内容。

---

## 目录结构

```
99-archived/
└── README.md                    # 本文件
```

---

## 已删除的归档内容

### mock-services/ (已删除)

**删除日期**: 2025-01-24

**删除原因**:
- Alldata API 真实服务已实现完成 (`services/alldata-api/`)
- Bisheng API 真实服务已实现完成 (`services/bisheng-api/`)
- Mock 服务不再需要，已被真实 API 替代

**原包含文件**:
- `alldata-api-mock.yaml` - Alldata API Mock 服务配置
- `bisheng-api-mock.yaml` - Bisheng API Mock 服务配置

**替代方案**: 使用 `services/alldata-api/` 和 `services/bisheng-api/` 中的真实 API 服务。

---

## 如何恢复归档内容

归档文件仅供参考和历史记录用途。如需恢复 Mock 服务用于测试，可以从 Git 历史记录中获取：

```bash
# 查看 Git 历史中的文件
git log --all --full-history -- docs/99-archived/mock-services/

# 恢复特定版本的文件
git checkout <commit-hash> -- docs/99-archived/mock-services/
```

---

## 联系方式

如有问题，请查看项目主文档或提 Issue。
