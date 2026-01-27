# OCR服务API文档

## 基础信息

- **Base URL**: `http://localhost:8007`
- **API Prefix**: `/api/v1/ocr`
- **Content-Type**: `multipart/form-data` (文件上传), `application/json` (其他)

---

## 认证

目前开发模式下无需认证，生产环境需配置API密钥。

---

## API端点

### 1. 健康检查

#### GET `/`

检查服务运行状态

**响应示例:**
```json
{
  "service": "OCR文档识别服务",
  "version": "1.0.0",
  "status": "running",
  "timestamp": "2024-01-27T10:00:00"
}
```

#### GET `/health`

健康检查详情

**响应示例:**
```json
{
  "status": "healthy",
  "ocr_engine": true,
  "database": true,
  "redis": true
}
```

---

### 2. OCR任务管理

#### POST `/api/v1/ocr/tasks`

创建OCR任务

**参数:**
- `file` (file, required): 上传的文档文件
- `extraction_type` (string, optional): 提取类型，默认 `general`
  - 可选值: `invoice`, `contract`, `purchase_order`, `delivery_note`, `quotation`, `receipt`, `report`, `general`
- `template_id` (string, optional): 自定义模板ID
- `tenant_id` (string, optional): 租户ID，默认 `default`
- `user_id` (string, optional): 用户ID，默认 `system`

**响应示例:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "document_name": "invoice.pdf",
  "document_type": "pdf",
  "status": "pending",
  "progress": 0.0,
  "created_at": "2024-01-27T10:00:00"
}
```

#### GET `/api/v1/ocr/tasks`

获取OCR任务列表

**参数:**
- `status` (string, optional): 状态筛选
- `extraction_type` (string, optional): 提取类型筛选
- `page` (integer, optional): 页码，默认 1
- `page_size` (integer, optional): 每页数量，默认 20

**响应示例:**
```json
{
  "total": 100,
  "tasks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "document_name": "invoice.pdf",
      "document_type": "pdf",
      "status": "completed",
      "progress": 100.0,
      "created_at": "2024-01-27T10:00:00",
      "result_summary": {
        "pages_processed": 1,
        "tables_found": 2,
        "text_length": 1234,
        "fields_extracted": 15
      }
    }
  ]
}
```

#### GET `/api/v1/ocr/tasks/{task_id}`

获取OCR任务详情

#### GET `/api/v1/ocr/tasks/{task_id}/result`

获取OCR任务结果

**响应示例:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "structured_data": {
    "invoice_number": "12345678",
    "invoice_date": "2024-01-15",
    "total_amount": 11300.00
  },
  "raw_text": "识别的原始文本...",
  "tables": [
    {
      "id": "table-1",
      "table_index": 0,
      "page_number": 1,
      "headers": ["序号", "名称", "数量", "单价", "金额"],
      "rows": [
        ["1", "商品A", "10", "1000", "10000"]
      ],
      "confidence": 0.95
    }
  ],
  "confidence_score": 0.92,
  "validation_issues": []
}
```

#### GET `/api/v1/ocr/tasks/{task_id}/result/enhanced`

获取增强的OCR任务结果（含跨字段校验和布局分析）

**参数:**
- `include_validation` (boolean, optional): 是否包含校验结果，默认 true
- `include_layout` (boolean, optional): 是否包含布局信息，默认 true

**响应示例:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "structured_data": { /* ... */ },
  "tables": [ /* ... */ ],
  "confidence_score": 0.92,
  "validation_issues": [],
  "cross_field_validation": {
    "valid": true,
    "errors": [],
    "warnings": [
      {
        "rule": "amount_sum_check",
        "description": "金额合计校验",
        "expected": 10000.0,
        "actual": 10000.0
      }
    ]
  },
  "layout_info": {
    "signature_regions": [
      {
        "label": "party_a_signature",
        "page": 3
      }
    ],
    "seal_regions": [
      {
        "label": "official_seal",
        "page": 3
      }
    ],
    "has_signatures": true,
    "has_seals": true
  },
  "completeness": {
    "valid": true,
    "missing_required": [],
    "completeness_rate": 95.0
  }
}
```

#### POST `/api/v1/ocr/tasks/{task_id}/verify`

验证和校正OCR结果

**请求体:**
```json
{
  "corrections": {
    "total_amount": 11500.00
  },
  "verified_by": "user123"
}
```

#### DELETE `/api/v1/ocr/tasks/{task_id}`

删除OCR任务

---

### 3. 批量处理

#### POST `/api/v1/ocr/tasks/batch`

批量创建OCR任务

**参数:**
- `files` (file[], required): 多个文档文件
- `extraction_type` (string, optional): 提取类型
- `template_id` (string, optional): 模板ID

**响应示例:**
```json
{
  "batch_id": "batch-550e8400",
  "total_files": 3,
  "tasks": [
    "task-id-1",
    "task-id-2",
    "task-id-3"
  ],
  "status": "pending"
}
```

---

### 4. 文档类型识别

#### POST `/api/v1/ocr/detect-type`

自动识别文档类型

**参数:**
- `file` (file, required): 文档文件

**响应示例:**
```json
{
  "detected_type": "invoice",
  "confidence": 0.95,
  "suggested_templates": [
    "template-invoice-001"
  ],
  "metadata": {
    "file_name": "document.pdf",
    "file_size": 1234567,
    "page_count": 2,
    "text_length": 1234
  }
}
```

---

### 5. 模板管理

#### GET `/api/v1/ocr/templates`

获取模板列表

**参数:**
- `template_type` (string, optional): 模板类型筛选
- `category` (string, optional): 分类筛选
- `is_active` (boolean, optional): 是否只返回启用的模板
- `include_public` (boolean, optional): 是否包含公开模板

#### POST `/api/v1/ocr/templates`

创建提取模板

**请求体:**
```json
{
  "name": "自定义发票模板",
  "description": "特定格式的发票模板",
  "template_type": "invoice",
  "category": "financial",
  "extraction_rules": {
    "fields": [
      {
        "name": "发票号码",
        "key": "invoice_number",
        "required": true
      }
    ]
  }
}
```

#### GET `/api/v1/ocr/templates/{template_id}`

获取模板详情

#### PUT `/api/v1/ocr/templates/{template_id}`

更新模板

#### DELETE `/api/v1/ocr/templates/{template_id}`

删除模板

#### POST `/api/v1/ocr/templates/preview`

使用模板预览提取结果

**参数:**
- `file` (file, required): 文档文件
- `request` (string, required): JSON字符串，包含模板配置

**响应示例:**
```json
{
  "extracted_fields": {
    "invoice_number": "12345678"
  },
  "detected_tables": [
    {
      "index": 0,
      "headers": ["序号", "名称", "数量"],
      "rows": [["1", "商品A", "10"]],
      "row_count": 1
    }
  ],
  "validation_result": {},
  "confidence_score": 0.85
}
```

#### GET `/api/v1/ocr/templates/types`

获取支持的文档类型列表

**响应示例:**
```json
{
  "document_types": [
    {
      "type": "invoice",
      "name": "发票",
      "category": "financial",
      "supported_formats": ["pdf", "image"]
    },
    {
      "type": "contract",
      "name": "合同",
      "category": "legal",
      "supported_formats": ["pdf", "word"]
    }
  ]
}
```

#### POST `/api/v1/ocr/templates/load-defaults`

加载默认模板到数据库

---

## 错误响应

所有错误响应遵循以下格式：

```json
{
  "detail": "错误描述信息"
}
```

常见HTTP状态码：
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 请求数据验证失败
- `500 Internal Server Error`: 服务器内部错误

---

## WebSocket通知（可选）

任务状态变化时可通过WebSocket接收通知：

```
ws://localhost:8007/ws/ocr/tasks/{task_id}
```

消息格式：
```json
{
  "event": "status_changed",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45.0
}
```

---

## 速率限制

- 单文件上传: 100次/分钟
- 批量上传: 10次/分钟
- 其他API: 1000次/分钟

---

## 文件大小限制

- 单文件最大: 50MB
- 批量总大小: 200MB

---

## 支持的文件格式

| 类型 | 扩展名 | MIME类型 |
|------|--------|----------|
| PDF | `.pdf` | application/pdf |
| 图片 | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.webp` | image/* |
| Word | `.doc`, `.docx` | application/msword, application/vnd.openxmlformats-officedocument.wordprocessingml.document |
| Excel | `.xls`, `.xlsx` | application/vnd.ms-excel, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
