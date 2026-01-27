# OCR文档识别服务

支持非结构化文档（PDF、Word、Excel、图片、扫描件）的智能识别，提供结构化信息提取、表格识别、布局分析等功能。

## 功能特性

### 文档类型支持

| 文档类型 | 说明 | 支持格式 | 关键特性 |
|---------|------|----------|----------|
| **发票** | 增值税发票 | PDF, 图片 | 表格提取、税额校验 |
| **合同** | 各类合同文档 | PDF, Word | 表格提取、签名检测、跨字段校验 |
| **采购订单** | 采购订单 | PDF, 图片, Word, Excel | 明细项提取、金额校验 |
| **送货单** | 送货单 | PDF, 图片, Word, Excel | 数量校验、收货验证 |
| **报价单** | 报价单 | PDF, 图片, Word, Excel | 税费计算、有效期校验 |
| **收据** | 收据 | PDF, 图片 | 签名/印章检测、金额大写校验 |
| **报告** | 业务报告 | PDF, Word | 指标提取 |
| **通用文档** | 其他文档 | 所有格式 | 自定义字段提取 |

### 核心功能

#### 1. 多引擎OCR支持
- **PaddleOCR**: 推荐用于中文文档
- **Tesseract**: 备用引擎
- **EasyOCR**: 可选引擎

#### 2. 智能信息提取
- AI大模型提取 (OpenAI兼容API)
- 本地NLP模型提取 (PaddleNLP UIE)
- 模板化提取

#### 3. 表格识别
- Camelot PDF表格提取
- pdfplumber 表格提取
- 跨页表格合并

#### 4. 布局分析
- 页面类型识别（封面、正文、签署页、附件）
- 签名区域检测
- 印章区域检测
- 页眉页脚识别

#### 5. 数据校验
- 单字段格式校验
- 跨字段关联校验
- 业务规则校验
- 完整性检查

## 快速开始

### Docker部署

```bash
# 启动OCR服务
docker-compose -f deploy/local/docker-compose.yml up -d ocr-service

# 查看日志
docker-compose logs -f ocr-service
```

### 本地开发

```bash
# 安装依赖
cd services/ocr-service
pip install -r requirements.txt

# 启动服务
uvicorn app:app --host 0.0.0.0 --port 8007 --reload
```

## API使用

### 1. 创建OCR任务

```bash
curl -X POST "http://localhost:8007/api/v1/ocr/tasks?extraction_type=invoice" \
  -F "file=@invoice.pdf"
```

### 2. 批量处理

```bash
curl -X POST "http://localhost:8007/api/v1/ocr/tasks/batch" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "extraction_type=auto"
```

### 3. 自动识别文档类型

```bash
curl -X POST "http://localhost:8007/api/v1/ocr/detect-type" \
  -F "file=@document.pdf"
```

响应示例：
```json
{
  "detected_type": "invoice",
  "confidence": 0.95,
  "suggested_templates": ["template-invoice-001"],
  "metadata": {
    "file_name": "document.pdf",
    "file_size": 1234567,
    "page_count": 2,
    "text_length": 1234
  }
}
```

### 4. 获取增强结果（含校验）

```bash
curl -X GET "http://localhost:8007/api/v1/ocr/tasks/{task_id}/result/enhanced?include_validation=true&include_layout=true"
```

### 5. 加载默认模板

```bash
curl -X POST "http://localhost:8007/api/v1/ocr/templates/load-defaults"
```

## 模板配置

### 模板结构

```json
{
  "name": "模板名称",
  "description": "模板描述",
  "type": "document_type",
  "category": "category",
  "supported_formats": ["pdf", "image"],
  "fields": [
    {
      "name": "字段中文名",
      "key": "field_key",
      "required": true,
      "validation": {
        "type": "string|number|date|email|phone|credit_code",
        "min_length": 2,
        "max_value": 100
      },
      "keywords": ["关键词1", "关键词2"]
    }
  ],
  "tables": [
    {
      "name": "表格名称",
      "key": "table_key",
      "required": false,
      "header_keywords": ["表头关键词"],
      "fields": [
        {"name": "列名", "key": "col_key"}
      ]
    }
  ],
  "layout_detection": {
    "signature_regions": [
      {"keywords": ["甲方签字"], "label": "party_a_signature"}
    ],
    "seal_regions": [
      {"keywords": ["公章"], "label": "official_seal"}
    ]
  },
  "cross_field_validation": [
    {
      "rule": "amount_sum_check",
      "description": "金额合计校验",
      "fields": ["total_amount", "items"],
      "validation": "sum(items.amount) == total_amount",
      "severity": "warning"
    }
  ],
  "post_processing": {
    "date_format": "YYYY-MM-DD",
    "amount_format": "number"
  }
}
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `DATABASE_URL` | 数据库连接字符串 | mysql+pymysql://root:password@localhost:3306/ocr_service |
| `REDIS_URL` | Redis连接字符串 | redis://localhost:6379/0 |
| `OPENAI_API_KEY` | OpenAI API密钥 | - |
| `OPENAI_API_BASE` | OpenAI API基础URL | - |
| `OCR_ENGINE` | OCR引擎选择 | paddleocr |
| `MAX_FILE_SIZE` | 最大文件大小 | 52428800 |
| `TEMP_DIR` | 临时文件目录 | /tmp/ocr |

## 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_cross_field_validator.py -v

# 生成覆盖率报告
pytest tests/ --cov=services --cov-report=html
```

## 架构说明

```
services/ocr-service/
├── app.py                    # FastAPI应用入口
├── models/                   # 数据模型
│   ├── base.py              # SQLAlchemy基础模型
│   ├── ocr_task.py          # OCR任务模型
│   ├── ocr_result.py        # OCR结果模型
│   └── extraction_rule.py   # 提取规则模型
├── services/                 # 业务服务层
│   ├── ocr_engine.py        # OCR引擎核心
│   ├── document_parser.py   # 文档解析器
│   ├── table_extractor.py   # 表格提取器
│   ├── ai_extractor.py       # AI信息抽取器
│   ├── nlp_extractor.py     # NLP本地抽取器
│   ├── validator.py         # 数据验证器
│   ├── layout_analyzer.py   # 布局分析器
│   ├── cross_field_validator.py  # 跨字段校验器
│   └── multi_page_processor.py  # 多页处理器
├── api/                      # API路由
│   ├── ocr_tasks.py         # OCR任务API
│   └── templates.py         # 模板管理API
├── templates/                # 预设模板
│   ├── invoice.json         # 发票模板
│   ├── contract.json        # 合同模板
│   ├── contract_enhanced.json  # 增强合同模板
│   ├── purchase_order.json  # 采购订单模板
│   ├── delivery_note.json   # 送货单模板
│   ├── quotation.json       # 报价单模板
│   ├── receipt.json         # 收据模板
│   └── report.json          # 报告模板
└── tests/                    # 测试用例
    ├── test_cross_field_validator.py
    └── test_layout_analyzer.py
```

## 常见问题

### 1. OCR服务启动失败

检查依赖是否正确安装：
```bash
pip list | grep paddleocr
pip list | grep pymupdf
```

### 2. 数据库连接失败

检查DATABASE_URL配置是否正确，确保MySQL服务已启动。

### 3. AI提取功能不可用

检查OPENAI_API_KEY和OPENAI_API_BASE环境变量是否正确配置。

### 4. 表格提取不准确

可以尝试切换表格提取引擎（Camelot/pdfplumber）或调整提取参数。

## 许可证

MIT License
