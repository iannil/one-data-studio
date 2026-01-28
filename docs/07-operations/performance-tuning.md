# 性能调优指南

ONE-DATA-STUDIO 性能优化建议

## 目录

- [数据库优化](#数据库优化)
- [缓存优化](#缓存优化)
- [向量检索优化](#向量检索优化)
- [前端优化](#前端优化)
- [网络优化](#网络优化)

---

## 数据库优化

### 连接池配置

根据服务负载调整数据库连接池大小：

```python
# services/shared/config.py

@dataclass
class DatabaseConfig:
    # 基础配置
    pool_size: int = field(default_factory=lambda: int(os.getenv('DB_POOL_SIZE', '20')))
    max_overflow: int = field(default_factory=lambda: int(os.getenv('DB_MAX_OVERFLOW', '40')))
    pool_timeout: int = field(default_factory=lambda: int(os.getenv('DB_POOL_TIMEOUT', '30')))
    pool_recycle: int = field(default_factory=lambda: int(os.getenv('DB_POOL_RECYCLE', '3600')))
    pool_pre_ping: bool = True  # 启用连接健康检查
```

**推荐配置**:

| 负载级别 | pool_size | max_overflow |
|----------|-----------|--------------|
| 低 (QPS < 100) | 10 | 20 |
| 中 (QPS 100-1000) | 20 | 40 |
| 高 (QPS > 1000) | 50 | 100 |

### 查询优化

#### 1. 添加适当索引

```sql
-- 工作流表索引
CREATE INDEX idx_workflows_created_at ON workflows(created_at DESC);
CREATE INDEX idx_workflows_created_by ON workflows(created_by);
CREATE INDEX idx_workflows_status ON workflows(status);

-- 执行记录索引
CREATE INDEX idx_executions_workflow ON workflow_executions(workflow_id, created_at DESC);
CREATE INDEX idx_executions_status ON workflow_executions(status);

-- 会话索引
CREATE INDEX idx_conversations_user ON conversations(user_id, updated_at DESC);
```

#### 2. 使用查询优化

```python
# 使用 joinedload 预加载关联数据
from sqlalchemy.orm import joinedload

def get_workflow_with_execution(id: str):
    return db.query(Workflow)\
        .options(joinedload(Workflow.executions))\
        .filter(Workflow.workflow_id == id)\
        .first()

# 只选择需要的列
def get_workflow_list(limit: int):
    return db.query(
        Workflow.workflow_id,
        Workflow.name,
        Workflow.status,
        Workflow.created_at
    ).limit(limit).all()
```

### MySQL 配置优化

```ini
# my.cnf

[mysqld]
# InnoDB 缓冲池大小（建议为物理内存的 50-70%）
innodb_buffer_pool_size = 4G

# InnoDB 日志文件大小
innodb_log_file_size = 512M

# InnoDB 刷盘策略（性能优先设为 2）
innodb_flush_log_at_trx_commit = 2

# 最大连接数
max_connections = 500

# 查询缓存（MySQL 5.7 及以下）
query_cache_type = 1
query_cache_size = 256M

# 慢查询日志
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
```

---

## 缓存优化

### Redis 缓存策略

```python
# 缓存层级配置

@dataclass
class RedisConfig:
    # 元数据缓存（变化较少，长 TTL）
    metadata_ttl: int = 3600  # 1 小时

    # 模型列表缓存（中等变化）
    model_list_ttl: int = 600  # 10 分钟

    # 工作流缓存（经常变化）
    workflow_ttl: int = 180  # 3 分钟

    # 搜索结果缓存（短 TTL）
    search_result_ttl: int = 60  # 1 分钟
```

### 缓存使用建议

#### 1. 缓存热点数据

```python
from services.shared.cache import cached

@cached(ttl=300, key_prefix='datasets')
def list_datasets():
    # 数据集列表变化较少
    return db.query(Dataset).all()
```

#### 2. 缓存计算结果

```python
@cached(ttl=600, key_prefix='schema')
def get_table_schema(database: str, table: str):
    # Schema 解析计算量大
    return parse_schema(database, table)
```

#### 3. 使用缓存穿透保护

```python
from services.shared.cache import cached

@cached(ttl=60, key_prefix='search', allow_null=True)
def vector_search(query: str, top_k: int):
    # 即使结果为空也缓存，避免穿透
    return vector_store.search(query, top_k)
```

---

## 向量检索优化

### Milvus 索引配置

```python
# 根据数据量选择合适的索引

def get_index_config(collection_size: int) -> dict:
    """根据集合大小返回最优索引配置"""
    if collection_size < 10000:
        # 小数据量：使用 FLAT 精确搜索
        return {
            'index_type': 'FLAT',
            'metric_type': 'L2',
            'params': {}
        }
    elif collection_size < 100000:
        # 中等数据量：IVF_FLAT
        return {
            'index_type': 'IVF_FLAT',
            'metric_type': 'L2',
            'params': {'nlist': 128}
        }
    else:
        # 大数据量：IVF_PQ
        return {
            'index_type': 'IVF_PQ',
            'metric_type': 'L2',
            'params': {'nlist': 256, 'm': 16}
        }
```

### 检索参数调优

```python
def optimize_search_params(collection_size: int, top_k: int) -> dict:
    """根据集合大小优化搜索参数"""
    nprobe = max(1, int(collection_size / 1000))  # 搜索分片数
    nprobe = min(nprobe, 128)  # 限制最大值

    return {
        'top_k': min(top_k, 100),  # 限制返回数量
        'nprobe': nprobe,
        'search_params': {'nprobe': nprobe}
    }
```

---

## 前端优化

### React Query 配置

```typescript
// web/src/services/queryClient.ts

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 根据数据类型设置不同的缓存时间
      staleTime: (query) => {
        if (query.queryKey[0] === 'cube' && query.queryKey[1] === 'models') {
          return 15 * 60 * 1000;  // 模型列表：15 分钟
        }
        if (query.queryKey[0] === 'auth' && query.queryKey[1] === 'permissions') {
          return 10 * 60 * 1000;  // 权限：10 分钟
        }
        return 5 * 60 * 1000;  // 默认：5 分钟
      },
      // 失败重试策略
      retry: (failureCount, error) => {
        // 4xx 错误不重试
        if (error?.status >= 400 && error?.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});
```

### 代码分割

```typescript
// web/src/App.tsx

import { lazy, Suspense } from 'react';
import { Loading } from './components/common/Loading';

// 路由级别的代码分割
const WorkflowsPage = lazy(() => import('./pages/workflows/WorkflowsPage'));
const WorkflowEditorPage = lazy(() => import('./pages/workflows/WorkflowEditorPage'));
const ChatPage = lazy(() => import('./pages/chat/ChatPage'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/workflows" element={<WorkflowsPage />} />
        <Route path="/workflows/:id/edit" element={<WorkflowEditorPage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </Suspense>
  );
}
```

### 资源优化

```typescript
// vite.config.ts 图片优化配置

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          const name = assetInfo.name || '';
          // 图片文件单独打包
          if (/\.(png|jpe?g|gif|svg|webp)$/i.test(name)) {
            return 'assets/images/[name]-[hash][extname]';
          }
          return 'assets/[name]-[hash][extname]';
        },
      },
    },
  },
});
```

---

## 网络优化

### 请求合并

```typescript
// 使用批量接口减少请求次数

// ❌ 不推荐：多次请求
for (const id of ids) {
  await getWorkflow(id);
}

// ✅ 推荐：批量请求
const workflows = await getWorkflows({ ids });
```

### 启用压缩

```nginx
# nginx.conf

gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types
    application/json
    application/javascript
    text/css
    text/javascript
    text/xml
    text/html;

brotli on;
brotli_types
    application/json
    application/javascript
    text/css
    text/xml
    text/html;
```

### CDN 配置

```typescript
// 配置静态资源 CDN

const CDN_URL = import.meta.env.VITE_CDN_URL || '';

function getAssetUrl(path: string): string {
  return CDN_URL ? `${CDN_URL}${path}` : path;
}

// 图片使用 CDN
<img src={getAssetUrl('/images/logo.png')} alt="Logo" />
```

---

## 监控与分析

### 性能监控指标

| 指标 | 目标值 | 告警阈值 |
|------|--------|----------|
| API P50 延迟 | < 100ms | > 200ms |
| API P99 延迟 | < 500ms | > 1000ms |
| 错误率 | < 0.1% | > 1% |
| 数据库连接池使用率 | < 80% | > 90% |
| Redis 命中率 | > 90% | < 80% |

### 性能分析工具

```bash
# Python 性能分析
docker-compose exec alldata-api python -m cProfile -o profile.stats your_script.py
docker-compose exec alldata-api python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"

# Flask 延时分析
docker-compose exec alldata-api python -c "
from werkzeug.middleware.profiler import ProfilerMiddleware
# 在 Flask 应用中添加 ProfilerMiddleware
"
```

---

## 性能测试

### 压力测试示例

```python
# 使用 locust 进行压力测试

from locust import HttpUser, task, between

class OneDataUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_workflows(self):
        self.client.get("/api/v1/workflows")

    @task(1)
    def get_workflow(self):
        self.client.get("/api/v1/workflows/wf-1")

    @task(1)
    def chat(self):
        self.client.post("/api/v1/chat", json={
            "message": "测试消息",
            "model": "gpt-4o-mini"
        })
```

### 运行压力测试

```bash
# 安装 locust
pip install locust

# 运行测试
locust -f locustfile.py --host=http://localhost:8081 --users=100 --spawn-rate=10
```

---

## 优化检查清单

### 部署前检查

- [ ] 数据库索引已创建
- [ ] Redis 缓存已启用
- [ ] 连接池大小已调整
- [ ] 日志级别已设置（生产环境 INFO）
- [ ] 前端资源已压缩
- [ ] CDN 已配置（如适用）

### 部署后验证

- [ ] API P50 延迟 < 100ms
- [ ] API P99 延迟 < 500ms
- [ ] 错误率 < 0.1%
- [ ] 数据库慢查询 < 1/s
- [ ] Redis 命中率 > 90%
- [ ] 内存使用率 < 80%
