# OCR服务快速开始指南

## 5分钟快速启动

### 1. 启动服务（首次运行需要下载模型，约2-3分钟）

```bash
# 进入项目目录
cd /Users/iannil/Code/zproducts/one-data-studio

# 启动OCR服务
docker-compose -f deploy/local/docker-compose.yml up -d ocr-service

# 等待服务就绪
docker logs -f onedata-ocr-service
```

看到 `Application startup complete` 表示服务启动成功。

### 2. 加载默认模板

```bash
curl -X POST http://localhost:8007/api/v1/ocr/templates/load-defaults
```

### 3. 测试文档上传

```bash
# 上传一个PDF文档进行OCR识别
curl -X POST http://localhost:8007/api/v1/ocr/tasks \
  -F "file=@path/to/your/document.pdf" \
  -F "extraction_type=auto"
```

### 4. 查看识别结果

```bash
# 获取任务ID后，查看结果
curl http://localhost:8007/api/v1/ocr/tasks/{task_id}/result/enhanced
```

---

## 前端使用

### 1. 启动前端服务

```bash
cd web
npm install
npm run dev
```

### 2. 访问OCR页面

打开浏览器访问: `http://localhost:5173/alldata/ocr`

### 3. 上传文档

1. 选择文档类型（或自动检测）
2. 拖拽或点击上传文件
3. 等待处理完成
4. 查看提取结果

---

## Python客户端示例

```python
import requests
import json

OCR_API_URL = "http://localhost:8007/api/v1/ocr"

# 上传文档进行OCR识别
def extract_document(file_path, document_type="auto"):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'extraction_type': document_type}
        response = requests.post(f"{OCR_API_URL}/tasks", files=files, data=data)

    if response.status_code == 200:
        task_id = response.json()['task_id']
        return get_result(task_id)
    else:
        print(f"Error: {response.text}")
        return None

# 获取识别结果
def get_result(task_id):
    response = requests.get(f"{OCR_API_URL}/tasks/{task_id}/result/enhanced")
    return response.json()

# 使用示例
result = extract_document("sample_invoice.pdf", "invoice")
print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## cURL示例

### 发票识别

```bash
# 创建任务
curl -X POST http://localhost:8007/api/v1/ocr/tasks \
  -F "file=@invoice.pdf" \
  -F "extraction_type=invoice" \
  | jq '.task_id'

# 获取结果
curl http://localhost:8007/api/v1/ocr/tasks/{task_id}/result/enhanced | jq
```

### 合同识别

```bash
curl -X POST http://localhost:8007/api/v1/ocr/tasks \
  -F "file=@contract.pdf" \
  -F "extraction_type=contract"
```

### 批量处理

```bash
curl -X POST http://localhost:8007/api/v1/ocr/tasks/batch \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@doc3.pdf" \
  -F "extraction_type=auto"
```

---

## 返回结果示例

```json
{
  "task_id": "abc-123-def-456",
  "document_type": "invoice",
  "status": "completed",
  "structured_data": {
    "invoice_number": "12345678",
    "invoice_date": "2024-01-15",
    "buyer_name": "XX公司",
    "seller_name": "YY供应商",
    "total_amount": 15000.00,
    "tax_amount": 1950.00
  },
  "tables": [
    {
      "id": "table_1",
      "page_number": 1,
      "headers": ["序号", "商品名称", "数量", "单价", "金额"],
      "rows": [
        ["1", "商品A", "10", "500.00", "5000.00"],
        ["2", "商品B", "20", "500.00", "10000.00"]
      ],
      "confidence": 0.95
    }
  ],
  "confidence_score": 0.92,
  "cross_field_validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  },
  "layout_info": {
    "has_signatures": false,
    "has_seals": true,
    "seal_regions": [
      {"label": "invoice_seal", "page": 1}
    ]
  },
  "completeness": {
    "valid": true,
    "completeness_rate": 100,
    "missing_required": []
  }
}
```

---

## 常见问题

### Q: 服务启动很慢？
A: 首次启动需要下载PaddleOCR模型文件（约100MB），后续启动会使用缓存。

### Q: 中文识别不准确？
A: 确保使用的是`paddleocr`引擎，它对中文支持最好。可以尝试提高图像分辨率。

### Q: 如何自定义提取字段？
A: 通过`/api/v1/ocr/templates`端点创建自定义模板，定义需要的字段和提取规则。

### Q: 支持哪些文件格式？
A: PDF、JPG、PNG、BMP、TIFF、DOCX、XLSX

### Q: 处理大文件超时怎么办？
A: 可以通过后台任务处理，先获取task_id，然后轮询检查结果。

---

## 下一步

- 阅读完整API文档: [API.md](./API.md)
- 查看部署清单: [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
- 了解实施详情: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
