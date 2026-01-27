# OCR文档识别服务

企业级OCR文档智能识别服务，支持8种常见文档类型的结构化提取。

## 快速导航

| 文档 | 描述 |
|------|------|
| [QUICKSTART.md](./QUICKSTART.md) | 5分钟快速开始指南 |
| [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) | 部署检查清单 |
| [API.md](./API.md) | 完整API文档 |
| [README.md](./README.md) | 服务详细说明 |
| [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) | 实施总结 |
| [cli/README.md](./cli/README.md) | 命令行工具文档 |
| [sdk/python/examples.py](./sdk/python/examples.py) | Python SDK示例 |

## 功能特性

### 支持的文档类型

| 类型 | 描述 | 表格提取 | 签名检测 | 跨字段校验 |
|------|------|----------|----------|------------|
| 📄 发票 | 增值税发票、普通发票 | ✅ | ✅ | ✅ |
| 📋 合同 | 各类合同协议 | ✅ | ✅ | ✅ |
| 🛒 采购订单 | PO采购单 | ✅ | ❌ | ✅ |
| 🚚 送货单 | 物流送货单 | ✅ | ❌ | ✅ |
| 💰 报价单 | 商业报价单 | ✅ | ❌ | ✅ |
| 🧾 收据 | 各类收据 | ❌ | ✅ | ✅ |
| 📊 报告 | 分析报告 | ✅ | ❌ | ❌ |
| 📄 通用文档 | 一般文档 | ❌ | ❌ | ❌ |

### 核心能力

1. **智能识别**
   - 基于PaddleOCR的高精度文字识别
   - 支持50+种语言（中文、英文等）
   - 自动文档类型检测

2. **表格提取**
   - 智能检测表格区域
   - 保留表格结构
   - 跨页表格合并

3. **布局分析**
   - 签名区域识别
   - 印章区域检测
   - 页面分类（封面/正文/签署页）

4. **数据校验**
   - 7种跨字段校验规则
   - 完整性检查
   - 业务规则验证

5. **多格式支持**
   - 输入：PDF、JPG、PNG、BMP、DOCX、XLSX
   - 输出：JSON、结构化数据

## 快速开始

### 1. 启动服务

```bash
docker-compose -f deploy/local/docker-compose.yml up -d ocr-service
```

### 2. 加载模板

```bash
curl -X POST http://localhost:8007/api/v1/ocr/templates/load-defaults
```

### 3. 识别文档

```bash
# 使用curl
curl -X POST http://localhost:8007/api/v1/ocr/tasks \
  -F "file=@document.pdf" \
  -F "extraction_type=auto"

# 使用CLI工具
ocr-cli extract document.pdf

# 使用Python SDK
python3 -c "from ocr_client import extract_document; print(extract_document('document.pdf').structured_data)"
```

## 客户端SDK

### Python SDK

```python
from ocr_client import OCRClient, DocumentType

# 创建客户端
client = OCRClient("http://localhost:8007")

# 提取文档
result = client.extract("invoice.pdf", DocumentType.INVOICE)

# 获取字段
print(result.get_field("total_amount"))

# 检查结果
if result.is_valid():
    print("验证通过!")
```

### JavaScript/TypeScript

```typescript
import { OCRClient, DocumentType } from '@/services/ocr';

const client = new OCRClient();
const result = await client.extract('file.pdf', DocumentType.INVOICE);
console.log(result.structured_data);
```

### 命令行工具

```bash
# 安装
pip install -r requirements.txt

# 使用
ocr-cli extract document.pdf --type invoice
```

## API端点

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | /api/v1/ocr/tasks | 创建识别任务 |
| GET | /api/v1/ocr/tasks/{id} | 获取任务状态 |
| GET | /api/v1/ocr/tasks/{id}/result | 获取识别结果 |
| GET | /api/v1/ocr/tasks/{id}/result/enhanced | 获取增强结果 |
| POST | /api/v1/ocr/tasks/batch | 批量识别 |
| POST | /api/v1/ocr/detect-type | 检测文档类型 |
| GET | /api/v1/ocr/templates | 获取模板列表 |
| POST | /api/v1/ocr/templates | 创建模板 |
| POST | /api/v1/ocr/templates/load-defaults | 加载默认模板 |

## 配置说明

### 环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| DATABASE_URL | - | 数据库连接URL |
| REDIS_URL | redis://localhost:6379/0 | Redis连接URL |
| OPENAI_API_KEY | - | OpenAI API密钥（可选） |
| OCR_ENGINE | paddleocr | OCR引擎选择 |
| MAX_FILE_SIZE | 52428800 | 最大文件大小（字节） |
| TEMP_DIR | /tmp/ocr | 临时文件目录 |

### OCR引擎选择

| 引擎 | 优点 | 缺点 |
|------|------|------|
| paddleocr | 中文识别准确率高 | 模型较大 |
| tesseract | 轻量级 | 中文识别一般 |
| easyocr | 多语言支持 | 速度较慢 |

## 测试

### 运行测试

```bash
# 单元测试
cd services/ocr-service
pytest tests/

# 批量功能测试
python3 scripts/batch_test.py

# 验证实施
python3 scripts/verify_implementation.py
```

### 测试文档

准备测试文档放在 `tests/documents/` 目录：
- sample_invoice.pdf - 发票样本
- sample_contract.pdf - 合同样本
- sample_purchase_order.pdf - 采购订单样本
- 等等...

## 性能指标

| 指标 | 值 |
|------|-----|
| 单页处理时间 | 2-5秒 |
| 批量吞吐量 | 10-20页/分钟 |
| 识别准确率 | 95%+ |
| 表格提取准确率 | 90%+ |
| 支持并发 | 10任务 |

## 常见问题

### Q: 如何处理大文件？

A: 大文件会自动分页处理，可以调整`MAX_FILE_SIZE`环境变量增加限制。

### Q: 如何自定义字段提取？

A: 通过`/api/v1/ocr/templates`端点创建自定义模板，定义需要的字段。

### Q: 如何提高识别准确率？

A:
1. 确保文档清晰（DPI 200+）
2. 选择正确的文档类型
3. 使用自定义模板
4. 对扫描件进行预处理

### Q: 支持哪些语言？

A: 支持中英文混合识别，PaddleOCR支持80+种语言。

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                     Web UI                          │
│                   (React + TS)                      │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI Service                    │
│  ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │ OCR API  │ │ Template │ │  Background Tasks   │ │
│  └──────────┘ └──────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  PaddleOCR  │  │   Camelot   │  │   OpenAI    │
│   (文本)    │  │   (表格)    │  │   (增强)    │
└─────────────┘  └─────────────┘  └─────────────┘
        │                 │
        ▼                 ▼
┌─────────────┐  ┌─────────────┐
│    MySQL    │  │    Redis    │
│  (数据存储) │  │   (缓存)    │
└─────────────┘  └─────────────┘
```

## 版本历史

### v1.0.0 (2024-01-27)

- ✅ 支持8种文档类型
- ✅ 智能表格提取
- ✅ 签名/印章区域检测
- ✅ 跨字段校验规则
- ✅ 多页文档处理
- ✅ Python SDK
- ✅ 命令行工具
- ✅ RESTful API

## 许可证

内部项目，版权归公司所有。

## 联系方式

- 技术支持: support@example.com
- 问题反馈: https://github.com/example/ocr-service/issues
