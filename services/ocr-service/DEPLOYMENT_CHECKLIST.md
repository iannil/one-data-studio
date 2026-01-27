# OCR服务部署检查清单

## 部署前检查

### 1. 环境变量配置
```bash
# 必需的环境变量
export MYSQL_ROOT_PASSWORD=your_password
export MYSQL_PASSWORD=your_password
export OPENAI_API_KEY=sk-xxx  # 可选，用于AI增强提取
export OCR_ENGINE=paddleocr     # 默认OCR引擎
```

### 2. 依赖服务检查
```bash
# 检查MySQL是否运行
docker ps | grep mysql

# 检查Redis是否运行
docker ps | grep redis

# 检查MinIO是否运行（存储上传文件）
docker ps | grep minio
```

### 3. 网络配置检查
```bash
# 检查onedata-network是否存在
docker network ls | grep onedata

# 如果不存在，创建网络
docker network create onedata-network
```

## 部署步骤

### Step 1: 构建并启动OCR服务
```bash
cd /Users/iannil/Code/zproducts/one-data-studio
docker-compose -f deploy/local/docker-compose.yml up -d ocr-service
```

### Step 2: 查看服务日志
```bash
docker logs -f onedata-ocr-service
```

### Step 3: 健康检查
```bash
# 等待服务启动（约30秒）
sleep 30

# 检查健康状态
curl http://localhost:8007/health

# 预期输出: {"status":"healthy","service":"ocr-service"}
```

### Step 4: 加载默认模板
```bash
curl -X POST http://localhost:8007/api/v1/ocr/templates/load-defaults
```

### Step 5: 验证模板加载
```bash
curl http://localhost:8007/api/v1/ocr/templates | python3 -m json.tool
```

## 功能测试

### 测试1: 文档类型检测
```bash
curl -X POST http://localhost:8007/api/v1/ocr/detect-type \
  -F "file=@test_documents/sample_invoice.pdf"
```

### 测试2: 发票提取
```bash
curl -X POST http://localhost:8007/api/v1/ocr/tasks \
  -F "file=@test_documents/sample_invoice.pdf" \
  -F "extraction_type=invoice"
```

### 测试3: 合同提取（带表格）
```bash
curl -X POST http://localhost:8007/api/v1/ocr/tasks \
  -F "file=@test_documents/sample_contract.pdf" \
  -F "extraction_type=contract"
```

### 测试4: 获取增强结果
```bash
# 替换 TASK_ID 为实际的任务ID
curl http://localhost:8007/api/v1/ocr/tasks/TASK_ID/result/enhanced
```

### 测试5: 批量处理
```bash
curl -X POST http://localhost:8007/api/v1/ocr/tasks/batch \
  -F "files=@test_documents/doc1.pdf" \
  -F "files=@test_documents/doc2.pdf" \
  -F "extraction_type=invoice"
```

## 支持的文档类型

| 类型 | 值 | 表格支持 | 布局分析 | 跨字段校验 |
|------|-----|----------|----------|------------|
| 发票 | invoice | ✅ | ✅ | ✅ |
| 合同 | contract | ✅ | ✅ | ✅ |
| 采购订单 | purchase_order | ✅ | ✅ | ✅ |
| 送货单 | delivery_note | ✅ | ✅ | ✅ |
| 报价单 | quotation | ✅ | ✅ | ✅ |
| 收据 | receipt | ❌ | ✅ | ✅ |
| 报告 | report | ✅ | ✅ | ❌ |
| 通用文档 | general | ❌ | ❌ | ❌ |

## 跨字段校验规则

| 规则 | 描述 | 适用文档类型 |
|------|------|--------------|
| amount_sum_check | 金额合计校验 | contract, purchase_order, quotation |
| date_logic_check | 日期逻辑校验 | contract, delivery_note, quotation |
| payment_sum_check | 付款计划合计校验 | contract |
| tax_calculation_check | 税额计算校验 | invoice |
| total_amount_check | 总金额校验 | purchase_order, quotation, delivery_note |
| delivery_receive_check | 收货数量校验 | delivery_note |
| amount_check | 金额大小写校验 | receipt |

## API端点列表

| 端点 | 方法 | 描述 |
|------|------|------|
| /health | GET | 健康检查 |
| /api/v1/ocr/tasks | POST | 创建OCR任务 |
| /api/v1/ocr/tasks | GET | 获取任务列表 |
| /api/v1/ocr/tasks/{id} | GET | 获取任务详情 |
| /api/v1/ocr/tasks/{id}/result | GET | 获取提取结果 |
| /api/v1/ocr/tasks/{id}/result/enhanced | GET | 获取增强结果 |
| /api/v1/ocr/tasks/batch | POST | 批量处理 |
| /api/v1/ocr/detect-type | POST | 文档类型检测 |
| /api/v1/ocr/templates | POST | 创建模板 |
| /api/v1/ocr/templates | GET | 获取模板列表 |
| /api/v1/ocr/templates/{id} | GET | 获取模板详情 |
| /api/v1/ocr/templates/{id} | PUT | 更新模板 |
| /api/v1/ocr/templates/{id} | DELETE | 删除模板 |
| /api/v1/ocr/templates/types | GET | 获取文档类型 |
| /api/v1/ocr/templates/load-defaults | POST | 加载默认模板 |

## 故障排查

### 服务无法启动
```bash
# 查看详细日志
docker logs onedata-ocr-service --tail 100

# 检查端口占用
lsof -i :8007
```

### 数据库连接失败
```bash
# 检查MySQL服务状态
docker exec onedata-mysql mysql -uroot -p${MYSQL_PASSWORD} -e "SHOW DATABASES;"

# 检查数据库连接字符串
docker exec onedata-ocr-service env | grep DATABASE_URL
```

### OCR引擎初始化失败
```bash
# 进入容器检查PaddleOCR安装
docker exec -it onedata-ocr-service pip list | grep paddle

# 检查模型文件
docker exec onedata-ocr-service ls -la /root/.paddleocr/
```

### 内存不足
```bash
# 增加Docker内存限制（在docker-compose.yml中）
services:
  ocr-service:
    mem_limit: 4g
```

## 性能优化建议

1. **启用Redis缓存**：缓存已处理的文档结果
2. **配置任务队列**：使用Celery处理大批量任务
3. **调整并发数**：根据服务器配置调整`MAX_CONCURRENT_TASKS`
4. **使用GPU加速**：安装CUDA版本的PaddleOCR

## 监控指标

```bash
# 查看任务统计
curl http://localhost:8007/api/v1/ocr/tasks/statistics

# 查看服务状态
curl http://localhost:8007/api/v1/ocr/status
```

## 部署完成后验证

```bash
# 运行完整验证脚本
python3 services/ocr-service/scripts/verify_implementation.py
```

---

**部署日期**: ___________
**执行人**: ___________
**状态**: ✅ 通过 / ❌ 失败
**备注**: ___________
