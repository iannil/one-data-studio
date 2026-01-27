# OCR服务完整实施指南

## 📋 目录

1. [项目概述](#项目概述)
2. [功能清单](#功能清单)
3. [目录结构](#目录结构)
4. [快速开始](#快速开始)
5. [开发指南](#开发指南)
6. [部署指南](#部署指南)
7. [API参考](#api参考)
8. [监控运维](#监控运维)
9. [故障排查](#故障排查)

---

## 项目概述

OCR服务是企业级文档智能识别系统，支持8种常见文档类型的结构化提取，提供完整的API、SDK和命令行工具。

### 核心能力

| 能力 | 描述 |
|------|------|
| 📄 文档识别 | 支持8种文档类型（发票、合同、采购订单、送货单、报价单、收据、报告、通用） |
| 📊 表格提取 | 智能识别表格结构，支持跨页表格 |
| 🔍 布局分析 | 签名区域检测、印章区域检测、页面分类 |
| ✅ 数据校验 | 7种跨字段校验规则 |
| 📑 多页处理 | 智能页面分类、内容合并 |
| 🔔 通知机制 | Webhook事件通知 |
| 🔒 安全控制 | API密钥、速率限制、权限管理 |
| 📈 监控指标 | Prometheus指标、Grafana仪表板 |

---

## 功能清单

### 支持的文档类型

```
┌─────────────────────────────────────────────────────┐
│                   文档类型支持                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📄 发票 (invoice)      ✅ 表格 ✅ 签名 ✅ 校验    │
│  📋 合同 (contract)     ✅ 表格 ✅ 签名 ✅ 校验    │
│  🛒 采购订单 (po)       ✅ 表格 ❌ 签名 ✅ 校验    │
│  🚚 送货单 (dn)         ✅ 表格 ❌ 签名 ✅ 校验    │
│  💰 报价单 (quote)      ✅ 表格 ❌ 签名 ✅ 校验    │
│  🧾 收据 (receipt)      ❌ 表格 ✅ 签名 ✅ 校验    │
│  📊 报告 (report)       ✅ 表格 ❌ 签名 ❌ 校验    │
│  📄 通用 (general)      ❌ 表格 ❌ 签名 ❌ 校验    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### API端点

```
POST   /api/v1/ocr/tasks                      创建OCR任务
GET    /api/v1/ocr/tasks                      获取任务列表
GET    /api/v1/ocr/tasks/{id}                 获取任务详情
GET    /api/v1/ocr/tasks/{id}/result          获取识别结果
GET    /api/v1/ocr/tasks/{id}/result/enhanced 获取增强结果
POST   /api/v1/ocr/tasks/batch                批量处理
POST   /api/v1/ocr/detect-type                文档类型检测
POST   /api/v1/ocr/templates                  创建模板
GET    /api/v1/ocr/templates                  获取模板列表
GET    /api/v1/ocr/templates/{id}             获取模板详情
PUT    /api/v1/ocr/templates/{id}             更新模板
DELETE /api/v1/ocr/templates/{id}             删除模板
GET    /api/v1/ocr/templates/types            获取文档类型
POST   /api/v1/ocr/templates/load-defaults    加载默认模板
GET    /metrics                                Prometheus指标
GET    /api/v1/metrics                         JSON格式指标
```

---

## 目录结构

```
services/ocr-service/
├── api/                           # API路由
│   ├── ocr_tasks.py               # OCR任务API
│   └── templates.py               # 模板管理API
├── models/                        # 数据模型
│   ├── base.py                    # SQLAlchemy基类
│   └── ocr_task.py                # OCR任务模型
├── services/                      # 业务服务
│   ├── ocr_engine.py              # OCR引擎
│   ├── document_parser.py         # 文档解析器
│   ├── table_extractor.py         # 表格提取器
│   ├── ai_extractor.py            # AI提取器
│   ├── validator.py               # 数据验证器
│   ├── layout_analyzer.py         # 布局分析 ✨
│   ├── cross_field_validator.py   # 跨字段校验 ✨
│   ├── multi_page_processor.py    # 多页处理 ✨
│   ├── webhook.py                 # 通知服务 ✨
│   ├── cache.py                   # 缓存服务 ✨
│   ├── rate_limit.py              # 速率限制 ✨
│   ├── api_key.py                 # API密钥 ✨
│   └── metrics.py                 # 指标收集 ✨
├── templates/                     # 文档模板
│   ├── invoice.json               # 发票模板
│   ├── contract.json              # 合同模板
│   ├── contract_enhanced.json     # 增强合同 ✨
│   ├── purchase_order.json        # 采购订单 ✨
│   ├── delivery_note.json         # 送货单 ✨
│   ├── quotation.json             # 报价单 ✨
│   ├── receipt.json               # 收据 ✨
│   ├── report_enhanced.json       # 增强报告 ✨
│   └── generator.py               # 模板生成器 ✨
├── tests/                         # 测试
│   ├── __init__.py
│   ├── test_cross_field_validator.py
│   ├── test_integration.py
│   ├── generate_documents.py      # 测试文档生成 ✨
│   └── documents/                 # 测试文档目录
├── scripts/                       # 工具脚本
│   ├── verify_implementation.py   # 实施验证
│   ├── batch_test.py              # 批量测试 ✨
│   ├── performance_test.py        # 性能测试 ✨
│   └── deploy.sh                  # 部署脚本 ✨
├── cli/                           # 命令行工具
│   ├── ocr_cli.py                 # CLI工具 ✨
│   └── README.md
├── sdk/python/                    # Python SDK ✨
│   ├── __init__.py
│   ├── ocr_client.py
│   └── examples.py
├── monitoring/                    # 监控配置 ✨
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   ├── alerts.yml
│   ├── grafana-dashboard.json
│   └── README.md
├── migrations/                    # 数据库迁移
│   └── init.sql                   # 初始化SQL
├── Dockerfile
├── requirements.txt
├── pytest.ini
├── docker-compose.dev.yml         # 开发环境配置 ✨
├── Makefile                       # 便捷命令 ✨
├── INDEX.md                       # 总览文档 ✨
├── QUICKSTART.md                  # 快速开始
├── DEPLOYMENT_CHECKLIST.md        # 部署清单
├── API.md                         # API文档
├── README.md                      # 服务说明
└── IMPLEMENTATION_SUMMARY.md      # 实施总结
```

---

## 快速开始

### 使用Docker Compose（推荐）

```bash
# 1. 设置环境变量
export MYSQL_ROOT_PASSWORD=your_password
export MYSQL_PASSWORD=your_password

# 2. 启动服务
docker-compose -f deploy/local/docker-compose.yml up -d ocr-service

# 3. 加载模板
curl -X POST http://localhost:8007/api/v1/ocr/templates/load-defaults

# 4. 测试识别
curl -X POST http://localhost:8007/api/v1/ocr/tasks \
  -F "file=@document.pdf" \
  -F "extraction_type=auto"
```

### 使用Python SDK

```python
from ocr_client import OCRClient, DocumentType

client = OCRClient("http://localhost:8007")
result = client.extract("invoice.pdf", DocumentType.INVOICE)
print(result.get_field("total_amount"))
```

### 使用命令行工具

```bash
# 健康检查
python3 services/ocr-service/cli/ocr_cli.py health

# 文档识别
python3 services/ocr-service/cli/ocr_cli.py extract document.pdf

# 批量处理
python3 services/ocr-service/cli/ocr_cli.py batch ./documents/
```

### 使用Makefile

```bash
cd services/ocr-service

make deploy        # 完整部署
make up            # 启动服务
make logs          # 查看日志
make test          # 运行测试
make health        # 健康检查
make clean         # 清理资源
```

---

## 开发指南

### 环境要求

- Python 3.10+
- Docker & Docker Compose
- MySQL 8.0+
- Redis 6.0+

### 安装依赖

```bash
cd services/ocr-service
pip install -r requirements.txt
```

### 运行测试

```bash
# 单元测试
pytest tests/ -v

# 集成测试
pytest tests/test_integration.py -v

# 性能测试
python3 scripts/performance_test.py

# 验证实施
python3 scripts/verify_implementation.py
```

### 代码规范

```bash
# 格式化代码
black api/ services/
isort api/ services/

# 代码检查
flake8 api/ services/
mypy api/ services/
```

---

## 部署指南

### 生产环境部署

```bash
# 1. 构建镜像
docker-compose -f deploy/local/docker-compose.yml build ocr-service

# 2. 启动服务
docker-compose -f deploy/local/docker-compose.yml up -d ocr-service

# 3. 检查状态
docker-compose -f deploy/local/docker-compose.yml ps

# 4. 查看日志
docker-compose -f deploy/local/docker-compose.yml logs -f ocr-service
```

### 使用Kubernetes部署

```bash
# 1. 创建ConfigMap
kubectl create configmap ocr-config --from-file=config/

# 2. 创建Secret
kubectl create secret generic ocr-secret --from-literal=api-key=xxx

# 3. 部署
kubectl apply -f k8s/ocr-service/

# 4. 检查状态
kubectl get pods -l app=ocr-service
```

---

## API参考

### 认证

```bash
# 使用API密钥
curl -H "X-API-Key: your_api_key" \
  http://localhost:8007/api/v1/ocr/tasks
```

### 创建OCR任务

```bash
curl -X POST http://localhost:8007/api/v1/ocr/tasks \
  -H "X-API-Key: your_api_key" \
  -F "file=@document.pdf" \
  -F "extraction_type=invoice" \
  -F "template_id=optional_template_id"
```

### 获取增强结果

```bash
curl http://localhost:8007/api/v1/ocr/tasks/{task_id}/result/enhanced \
  -H "X-API-Key: your_api_key"
```

### 返回结果示例

```json
{
  "task_id": "abc-123",
  "document_type": "invoice",
  "status": "completed",
  "structured_data": {
    "invoice_number": "12345678",
    "total_amount": 15000.00
  },
  "tables": [...],
  "confidence_score": 0.95,
  "cross_field_validation": {
    "valid": true,
    "errors": []
  },
  "layout_info": {
    "has_signatures": false,
    "has_seals": true
  }
}
```

---

## 监控运维

### 启动监控服务

```bash
cd services/ocr-service/monitoring
docker-compose up -d

# 访问服务
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### 关键指标

| 指标 | 描述 | 告警阈值 |
|------|------|----------|
| `tasks_total` | 总任务数 | - |
| `tasks_completed` | 完成任务数 | - |
| `task_processing_seconds` | 处理时间 | P95 > 30s |
| `extraction_confidence` | 提取准确率 | < 0.8 |
| `system_queue_size` | 队列长度 | > 100 |

### 告警通知

编辑 `monitoring/alertmanager.yml` 配置通知渠道：

- 邮件通知
- Webhook通知
- 钉钉/企业微信/Slack集成

---

## 故障排查

### 常见问题

**Q: 服务启动失败**
```bash
# 查看详细日志
docker logs onedata-ocr-service --tail 100

# 检查端口占用
lsof -i :8007
```

**Q: 数据库连接失败**
```bash
# 检查MySQL状态
docker ps | grep mysql

# 测试连接
docker exec onedata-mysql mysql -uroot -p
```

**Q: OCR引擎初始化失败**
```bash
# 检查模型文件
docker exec onedata-ocr-service ls -la /root/.paddleocr/

# 重新安装
docker exec onedata-ocr-service pip install paddleocr==2.7.0.3
```

**Q: 内存不足**
```yaml
# 在docker-compose.yml中增加内存限制
services:
  ocr-service:
    mem_limit: 4g
```

### 日志查看

```bash
# 服务日志
docker-compose -f deploy/local/docker-compose.yml logs -f ocr-service

# 查看最近100行
docker logs --tail 100 onedata-ocr-service

# 实时跟踪
docker logs -f onedata-ocr-service
```

---

## 附录

### A. 跨字段校验规则

| 规则 | 描述 | 适用文档 |
|------|------|----------|
| amount_sum_check | 金额合计校验 | 合同、采购订单 |
| date_logic_check | 日期逻辑校验 | 合同、报价单 |
| payment_sum_check | 付款计划校验 | 合同 |
| tax_calculation_check | 税额计算校验 | 发票 |
| total_amount_check | 总金额校验 | 采购订单、报价单 |
| delivery_receive_check | 收货数量校验 | 送货单 |
| amount_check | 金额大小写校验 | 收据 |

### B. 性能基准

| 指标 | 值 |
|------|-----|
| 单页处理时间 | 2-5秒 |
| 批量吞吐量 | 10-20页/分钟 |
| 识别准确率 | 95%+ |
| 表格提取准确率 | 90%+ |
| 支持并发 | 10任务 |
| 内存占用 | 512MB-2GB |

### C. 相关链接

- [API文档](./API.md)
- [部署清单](./DEPLOYMENT_CHECKLIST.md)
- [快速开始](./QUICKSTART.md)
- [监控文档](./monitoring/README.md)
- [Python SDK](./sdk/python/examples.py)

---

**文档版本**: 1.0.0
**更新日期**: 2024-01-27
**维护者**: OCR服务团队
