# OCR服务监控配置

本文档介绍如何使用Prometheus和Grafana监控OCR服务。

## 快速开始

### 1. 启动监控服务

使用Docker Compose启动完整的监控栈：

```bash
cd /path/to/one-data-studio/services/ocr-service/monitoring
docker-compose up -d
```

这将启动：
- Prometheus (http://localhost:9090)
- Grafana (http://localhost:3000)
- AlertManager (http://localhost:9093)

### 2. 导入Grafana仪表板

1. 访问 http://localhost:3000
2. 默认登录: admin/admin
3. 添加Prometheus数据源: http://prometheus:9090
4. 导入仪表板: 使用 `grafana-dashboard.json`

## 可用指标

### 任务指标

| 指标名称 | 类型 | 描述 |
|---------|------|------|
| `tasks_total` | counter | 总任务数 |
| `tasks_completed` | counter | 完成任务数 |
| `tasks_failed` | counter | 失败任务数 |
| `task_processing_seconds` | histogram | 任务处理时间 |

### 提取指标

| 指标名称 | 类型 | 描述 |
|---------|------|------|
| `extraction_confidence` | gauge | 提取准确率 |
| `extraction_fields_count` | gauge | 提取字段数 |
| `extraction_tables_count` | gauge | 提取表格数 |

### 验证指标

| 指标名称 | 类型 | 描述 |
|---------|------|------|
| `validation_total` | counter | 验证总数 |
| `validation_errors_total` | counter | 验证错误数 |
| `validation_warnings_total` | counter | 验证警告数 |

### 系统指标

| 指标名称 | 类型 | 描述 |
|---------|------|------|
| `ocr_service_uptime_seconds` | gauge | 服务运行时间 |
| `system_memory_usage_percent` | gauge | 内存使用率 |
| `system_cpu_usage_percent` | gauge | CPU使用率 |
| `system_queue_size` | gauge | 任务队列长度 |

## 告警规则

已配置的告警规则：

| 告警名称 | 严重级别 | 触发条件 |
|---------|----------|----------|
| OCRServiceDown | critical | 服务不可用超过1分钟 |
| HighTaskFailureRate | warning | 失败率超过10% |
| HighProcessingTime | warning | P95处理时间超过30秒 |
| QueueBacklog | warning | 队列积压超过100个任务 |
| LowExtractionConfidence | warning | 平均准确率低于80% |
| HighMemoryUsage | warning | 内存使用率超过85% |

## 配置文件

| 文件 | 描述 |
|------|------|
| `prometheus.yml` | Prometheus抓取配置 |
| `alerts.yml` | 告警规则定义 |
| `grafana-dashboard.json` | Grafana仪表板配置 |
| `docker-compose.yml` | 监控服务编排 |

## 自定义监控

### 添加自定义指标

在代码中使用metrics模块：

```python
from services.metrics import metrics

# 计数器
metrics.inc("custom_counter", labels={"type": "custom"})

# 仪表盘
metrics.set("custom_gauge", 42.0)

# 直方图
metrics.observe("custom_duration", 1.5)

# 计时装饰器
@metrics.timing("function_duration")
def my_function():
    pass
```

### 查询Prometheus

```bash
# 查询当前QPS
curl 'http://localhost:9090/api/v1/query?query=rate(tasks_completed_total[5m])'

# 查询P95延迟
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95, rate(task_processing_seconds_bucket[5m]))'
```

## 故障排查

### Prometheus无法抓取指标

1. 检查OCR服务是否运行：
   ```bash
   curl http://localhost:8007/metrics
   ```

2. 检查Prometheus配置中的目标地址

3. 查看Prometheus日志：
   ```bash
   docker logs prometheus
   ```

### Grafana无法显示数据

1. 确认Prometheus数据源配置正确

2. 测试查询：
   - 在Grafana中点击 "Explore"
   - 输入查询: `up{job="ocr-service"}`

3. 检查时间范围是否正确

## 最佳实践

1. **调整抓取间隔**: 根据业务需求调整scrape_interval
2. **设置数据保留**: 在prometheus.yml中配置retention时间
3. **优化告警**: 根据实际情况调整告警阈值
4. **定期检查**: 定期检查告警规则的有效性

## 相关链接

- Prometheus文档: https://prometheus.io/docs/
- Grafana文档: https://grafana.com/docs/
- PromQL查询: https://prometheus.io/docs/prometheus/latest/querying/basics/
