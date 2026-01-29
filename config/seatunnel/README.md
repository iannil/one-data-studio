# SeaTunnel CDC 配置目录

本目录包含 SeaTunnel CDC（Change Data Capture）任务的配置文件和示例。

## 配置说明

### 配置文件结构

每个 SeaTunnel 配置文件包含三个主要部分：

1. **env**: 环境配置
   - `job.mode`: 任务执行模式（STREAMING/BATCH）
   - `parallelism`: 并行度
   - `checkpoint.interval`: Checkpoint 间隔

2. **source**: 数据源配置
   - 支持多种 CDC 源（MySQL, PostgreSQL, MongoDB, Oracle 等）
   - 连接信息、表配置、CDC 参数

3. **transform**: 数据转换配置（可选）
   - 字段映射
   - 数据过滤
   - 数据丰富

4. **sink**: 目标配置
   - 支持多种目标（ClickHouse, MinIO, Kafka, Elasticsearch 等）
   - 连接信息、表配置、写入参数

## 配置示例

### MySQL CDC 到 MinIO

```bash
cp config/seatunnel/mysql_to_minio.conf.example config/seatunnel/my_job.conf
# 编辑 my_job.conf 修改数据库连接信息
```

### MySQL CDC 到 ClickHouse

```bash
cp config/seatunnel/mysql_to_clickhouse.conf.example config/seatunnel/my_ch_job.conf
# 编辑 my_ch_job.conf 修改数据库连接信息
```

### MySQL CDC 到 Kafka

```bash
cp config/seatunnel/mysql_to_kafka.conf.example config/seatunnel/my_kafka_job.conf
# 编辑 my_kafka_job.conf 修改数据库连接信息
```

## 提交任务

### 通过 API 提交

```bash
curl -X POST http://localhost:5801/hazelcast/rest/maps/submit-job \
  -H "Content-Type: application/json" \
  -d '{
    "jobName": "mysql_to_minio",
    "configFile": "/seatunnel/config/mysql_to_minio.conf"
  }'
```

### 通过 SeaTunnel 客户端提交

```bash
bin/seatunnel.sh --config config/seatunnel/mysql_to_minio.conf
```

## 支持的数据源

### CDC 源

| 源类型 | 连接器名称 | 说明 |
|--------|-----------|------|
| MySQL | MySQL-CDC | 基于 Binlog 的 CDC |
| PostgreSQL | PostgreSQL-CDC | 基于 WAL 的 CDC |
| MongoDB | MongoDB-CDC | 基于 Oplog 的 CDC |
| Oracle | Oracle-CDC | 基于 LogMiner 的 CDC |
| SQL Server | SQLServer-CDC | 基于 CDC 特性的 CDC |

### 目标

| 目标类型 | 连接器名称 | 说明 |
|--------|-----------|------|
| ClickHouse | ClickHouse | 列式数据库 |
| MinIO/S3 | AiO | 对象存储 |
| Kafka | Kafka | 消息队列 |
| Elasticsearch | Elasticsearch | 搜索引擎 |
| Hive | Hive | 数据仓库 |
| Iceberg | Iceberg | 数据湖表 |
| Hudi | Hudi | 数据湖表 |

## 最佳实践

1. **表名配置**: 使用 `database.table` 格式，支持正则表达式
2. **并行度**: 根据数据量调整，建议 2-4
3. **Checkpoint**: 默认 3 秒，可根据延迟要求调整
4. **错误处理**: 配置重试次数和超时时间
5. **监控**: 配置任务指标输出

## 故障排查

### 任务启动失败

- 检查配置文件语法
- 验证数据库连接信息
- 确认表名格式正确

### 数据同步延迟

- 检查网络带宽
- 增加 parallelism
- 调整批处理大小

### 数据丢失

- 检查 Checkpoint 配置
- 验证 WAL/Binlog 保留时间
- 确认目标存储可用性
