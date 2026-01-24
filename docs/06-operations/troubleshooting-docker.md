# 故障处理手册

> **适用场景**: Docker Compose 本地开发环境
>
> 如果您使用 Kubernetes 部署，请参考 [troubleshooting-k8s.md](../05-development/troubleshooting-k8s.md)

ONE-DATA-STUDIO 运维故障处理指南

## 目录

- [诊断流程](#诊断流程)
- [常见故障](#常见故障)
- [性能问题](#性能问题)
- [安全事件](#安全事件)
- [数据恢复](#数据恢复)

---

## 诊断流程

### 第一步: 确认故障范围

```bash
# 1. 检查所有服务状态
docker-compose ps

# 2. 检查资源使用情况
docker stats

# 3. 检查日志错误
docker-compose logs --tail=100 | grep -i error
```

### 第二步: 收集诊断信息

```bash
# 创建诊断报告
./deploy/scripts/diagnose.sh > diagnosis-$(date +%Y%m%d-%H%M%S).log
```

诊断报告包含:
- 服务状态
- 资源使用情况
- 最近错误日志
- 网络连接状态
- 数据库连接状态

---

## 常见故障

### API 服务问题

#### 故障: API 返回 500 错误

**可能原因**:
- 数据库连接失败
- 配置错误
- 代码异常

**诊断命令**:
```bash
# 查看 API 日志
docker-compose logs -f alldata-api --tail=100
docker-compose logs -f bisheng-api --tail=100

# 检查数据库连接
docker-compose exec alldata-api python -c "
from database import engine
with engine.connect() as conn:
    print(conn.execute('SELECT 1').scalar())
"
```

**解决方案**:
1. 检查数据库连接配置
2. 验证数据库服务状态
3. 检查环境变量配置
4. 重启服务: `docker-compose restart alldata-api`

#### 故障: API 响应缓慢

**可能原因**:
- 数据库查询慢
- 缓存未生效
- 资源不足

**诊断命令**:
```bash
# 检查数据库慢查询
docker-compose exec mysql mysql -e "SHOW PROCESSLIST;" | grep -v Sleep

# 检查 Redis 连接
docker-compose exec redis redis-cli ping

# 检查资源使用
docker stats --no-stream
```

**解决方案**:
1. 优化慢查询
2. 检查 Redis 缓存配置
3. 增加资源限制
4. 启用查询缓存

### 数据库问题

#### 故障: 数据库连接失败

**症状**:
```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server")
```

**诊断步骤**:
```bash
# 1. 检查 MySQL 状态
docker-compose ps mysql

# 2. 检查 MySQL 日志
docker-compose logs mysql --tail=100

# 3. 测试连接
docker-compose exec mysql mysql -u root -p

# 4. 检查网络
docker-compose exec alldata-api ping mysql
```

**解决方案**:
1. 确认 MySQL 正在运行
2. 验证密码配置
3. 检查网络连接
4. 重启数据库: `docker-compose restart mysql`

#### 故障: 数据库磁盘空间不足

**症状**:
```
ERROR 1114 (HY000): The table is full
```

**诊断命令**:
```bash
# 检查磁盘使用
docker-compose exec mysql df -h

# 检查数据库大小
docker-compose exec mysql mysql -e "
SELECT table_schema,
       ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.tables
GROUP BY table_schema;
"
```

**解决方案**:
1. 清理旧数据
2. 扩容磁盘
3. 启用数据归档

### 向量数据库问题

#### 故障: Milvus 连接失败

**症状**:
```
pymilvus.exceptions MilvusException: <MilvusException: (code=1, Failed to connect to server
```

**诊断步骤**:
```bash
# 1. 检查 Milvus 状态
docker-compose ps milvus-standalone
docker-compose ps milvus-etcd
docker-compose ps milvus-minio

# 2. 检查 Milvus 日志
docker-compose logs milvus-standalone --tail=100

# 3. 检查集合状态
docker-compose exec bisheng-api python -c "
from services import VectorStore
vs = VectorStore()
print(vs.list_collections())
"
```

**解决方案**:
1. 确保 Milvus 组件都正常运行
2. 重启 Milvus: `docker-compose restart milvus-standalone`
3. 检查配置中的 host 和 port

### 前端问题

#### 故障: 页面加载失败

**症状**:
- 浏览器显示 404 错误
- 资源加载失败

**诊断步骤**:
```bash
# 1. 检查 Web 服务状态
docker-compose ps web

# 2. 检查 Nginx 配置
docker-compose exec web nginx -t

# 3. 检查静态文件
docker-compose exec web ls -la /app/dist/
```

**解决方案**:
1. 重新构建前端: `docker-compose build web`
2. 重启 Web 服务: `docker-compose restart web`
3. 检查 Nginx 配置

#### 故障: API 跨域错误

**症状**:
浏览器控制台显示 CORS 错误

**诊断步骤**:
```bash
# 检查 API 响应头
curl -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8080/api/v1/health -v
```

**解决方案**:
1. 确认 Vite 代理配置正确
2. 检查 API CORS 设置
3. 使用反向代理处理 CORS

---

## 性能问题

### 高 CPU 使用

**诊断命令**:
```bash
# 查看容器 CPU 使用
docker stats --no-stream | sort -k3 -hr

# 查看进程 CPU 使用
docker-compose exec alldata-api top -b -n 1
```

**常见原因与解决方案**:
1. **向量检索**: 调整 Milvus 索引参数
2. **LLM 调用**: 启用流式响应
3. **日志处理**: 降低日志级别

### 高内存使用

**诊断命令**:
```bash
# 查看容器内存使用
docker stats --no-stream | sort -k4 -hr

# 检查内存泄漏
docker-compose exec alldata-api python -c "
import tracemalloc
tracemalloc.start()
# ... 运行操作 ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"
```

**解决方案**:
1. 调整数据库连接池大小
2. 配置适当的缓存大小
3. 重启服务释放内存

### 磁盘 I/O 高

**诊断命令**:
```bash
# 查看 I/O 状态
iotop -o

# 检查磁盘写入
docker-compose exec mysql mysql -e "
SHOW VARIABLES LIKE 'innodb_flush_log_at_trx_commit';
"
```

**解决方案**:
1. 使用 SSD 存储
2. 调整数据库刷盘策略
3. 分离日志存储

---

## 安全事件

### 疑似入侵

**症状**:
- 异常登录记录
- 未知进程运行
- 异常网络连接

**应急响应**:
```bash
# 1. 隔离受影响系统
docker-compose stop

# 2. 保存现场数据
docker-compose logs > incident-$(date +%Y%m%d).log
docker exec $(docker ps -q) cat /var/log/auth.log > auth.log

# 3. 检查最近变更
git log --since="2 days ago" --oneline

# 4. 检查环境变量
docker-compose config | grep -v "password\|key\|secret"
```

### 数据泄露

**应急步骤**:
1. 立即暂停受影响服务
2. 更改所有密钥密码
3. 审计访问日志
4. 通知相关方

### 密钥轮换

```bash
# 1. 生成新密钥
NEW_KEY=$(openssl rand -hex 32)

# 2. 更新配置
sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$NEW_KEY/" deploy/.env

# 3. 重启服务
docker-compose restart alldata-api bisheng-api

# 4. 验证服务状态
curl http://localhost:8080/api/v1/health
```

---

## 数据恢复

### MySQL 数据恢复

```bash
# 1. 停止应用服务
docker-compose stop alldata-api bisheng-api

# 2. 恢复数据库
docker-compose exec -T mysql mysql -u root -p"${MYSQL_PASSWORD}" \
  < backup_20240101.sql

# 3. 验证数据
docker-compose exec mysql mysql -u root -p"${MYSQL_PASSWORD}" \
  -e "USE one_data_bisheng; SHOW TABLES;"

# 4. 重启服务
docker-compose start alldata-api bisheng-api
```

### 向量数据恢复

```bash
# 1. 从备份恢复集合
docker-compose exec bisheng-api python -c "
from services import VectorStore
vs = VectorStore()
# 需要预先准备好的向量数据备份
vs.insert('collection_name', texts, embeddings, metadata_list)
"

# 2. 验证恢复
docker-compose exec bisheng-api python -c "
from services import VectorStore
vs = VectorStore()
print('Collections:', vs.list_collections())
"
```

---

## 联系支持

如果问题无法解决，请收集以下信息联系支持团队:

1. 诊断报告
2. 相关日志
3. 配置文件（敏感信息已脱敏）
4. 复现步骤

支持渠道:
- Email: support@one-data.example.com
- GitHub Issues: https://github.com/your-org/one-data-studio/issues
