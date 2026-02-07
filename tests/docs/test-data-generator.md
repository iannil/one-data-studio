# 测试数据生成指南

**文档版本**: 1.0
**创建日期**: 2024-02-07

## 一、概述

本文档描述测试数据的生成策略和方法，确保测试数据的完整性和一致性。

## 二、数据生成原则

### 2.1 唯一性

- 所有生成的数据必须保证唯一性
- 使用时间戳 + 随机数组合
- 避免使用硬编码的固定值

### 2.2 真实性

- 生成的数据应模拟真实场景
- 包含边界值和异常值
- 覆盖各种业务场景

### 2.3 可清理性

- 测试数据易于识别和清理
- 使用特定前缀（如 `test_`）
- 提供批量清理方法

## 三、用户数据生成

### 3.1 生成函数

```python
import uuid
from datetime import datetime, timedelta

def generate_test_user_data(role: str = None) -> dict:
    """生成测试用户数据"""
    timestamp = int(datetime.now().timestamp() * 1000)
    random_suffix = uuid.uuid4().hex[:8]

    user_data = {
        'username': f'test_{role or "user"}_{timestamp}',
        'email': f'test_{timestamp}@test.local',
        'display_name': f'测试用户{random_suffix}',
        'password': 'Test1234!',
        'phone': f'138{random_suffix[:8]}',
        'department': '数据工程部',
        'position': '测试岗位',
        'status': 'pending',
        'roles': [role] if role else ['business_user']
    }
    return user_data
```

### 3.2 角色特定数据

```python
# 系统管理员
generate_test_user_data('system_admin')

# 数据管理员
generate_test_user_data('data_admin')

# 数据工程师
generate_test_user_data('data_engineer')

# 算法工程师
generate_test_user_data('ai_engineer')

# AI 开发者
generate_test_user_data('ai_developer')

# 数据分析师
generate_test_user_data('data_analyst')

# 业务用户
generate_test_user_data('business_user')
```

## 四、数据源数据生成

### 4.1 MySQL 数据源

```python
def generate_mysql_datasource(suffix: str = None) -> dict:
    return {
        'name': f'测试MySQL{suffix}',
        'type': 'mysql',
        'host': f'mysql-test-{suffix}.example.com',
        'port': 3306,
        'database': f'test_db_{suffix}',
        'username': 'test_user',
        'password': 'test_password'
    }
```

### 4.2 PostgreSQL 数据源

```python
def generate_postgresql_datasource(suffix: str = None) -> dict:
    return {
        'name': f'测试PostgreSQL{suffix}',
        'type': 'postgresql',
        'host': f'pg-test-{suffix}.example.com',
        'port': 5432,
        'database': f'test_db_{suffix}',
        'username': 'test_user',
        'password': 'test_password'
    }
```

## 五、工作流数据生成

### 5.1 RAG 工作流

```python
def generate_rag_workflow() -> dict:
    workflow_id = f'wf_rag_{uuid.uuid4().hex[:8]}'
    return {
        'workflow_id': workflow_id,
        'name': f'测试RAG工作流{workflow_id}',
        'type': 'rag',
        'description': '知识库问答测试流程',
        'definition': {
            'nodes': [
                {'id': 'input', 'type': 'input', 'label': '用户输入'},
                {'id': 'retrieval', 'type': 'vector_retrieval', 'label': '向量检索'},
                {'id': 'llm', 'type': 'llm', 'label': 'LLM生成'},
                {'id': 'output', 'type': 'output', 'label': '输出'}
            ],
            'edges': [
                {'source': 'input', 'target': 'retrieval'},
                {'source': 'retrieval', 'target': 'llm'},
                {'source': 'llm', 'target': 'output'}
            ]
        }
    }
```

### 5.2 SQL 工作流

```python
def generate_sql_workflow() -> dict:
    workflow_id = f'wf_sql_{uuid.uuid4().hex[:8]}'
    return {
        'workflow_id': workflow_id,
        'name': f'测试SQL工作流{workflow_id}',
        'type': 'sql',
        'description': 'Text-to-SQL测试流程',
        'definition': {
            'nodes': [
                {'id': 'input', 'type': 'input'},
                {'id': 'schema', 'type': 'schema_fetch'},
                {'id': 'sql_gen', 'type': 'sql_generation'},
                {'id': 'output', 'type': 'output'}
            ],
            'edges': [
                {'source': 'input', 'target': 'schema'},
                {'source': 'schema', 'target': 'sql_gen'},
                {'source': 'sql_gen', 'target': 'output'}
            ]
        }
    }
```

## 六、BI 数据生成

### 6.1 仪表板数据

```python
def generate_dashboard() -> dict:
    dashboard_id = f'dash_{uuid.uuid4().hex[:8]}'
    return {
        'dashboard_id': dashboard_id,
        'name': f'测试仪表板{dashboard_id}',
        'description': '自动化测试仪表板',
        'theme': 'light',
        'layout': {'columns': 2, 'rows': 2},
        'auto_refresh': False,
        'is_public': False
    }
```

### 6.2 图表数据

```python
def generate_chart(dashboard_id: str, chart_type: str = 'line') -> dict:
    chart_id = f'chart_{uuid.uuid4().hex[:8]}'
    return {
        'chart_id': chart_id,
        'name': f'测试图表{chart_id}',
        'dashboard_id': dashboard_id,
        'chart_type': chart_type,
        'sql_query': f'SELECT date, value FROM test_table WHERE chart_id = "{chart_id}"',
        'config': {},
        'cache_enabled': True,
        'cache_ttl': 300
    }
```

## 七、指标数据生成

### 7.1 业务指标

```python
def generate_business_metric() -> dict:
    metric_id = f'metric_{uuid.uuid4().hex[:8]}'
    return {
        'metric_id': metric_id,
        'name': f'测试指标{metric_id}',
        'code': f'TEST_METRIC_{metric_id.upper()}',
        'description': '自动化测试指标',
        'category': 'business',
        'calculation_sql': 'SELECT COUNT(*) FROM test_table',
        'aggregation': 'daily',
        'unit': '个'
    }
```

## 八、知识库数据生成

### 8.1 知识库

```python
def generate_knowledge_base() -> dict:
    kb_id = f'kb_{uuid.uuid4().hex[:8]}'
    return {
        'kb_id': kb_id,
        'name': f'测试知识库{kb_id}',
        'description': '自动化测试知识库',
        'embedding_model': 'text-embedding-ada-002',
        'dimension': 1536,
        'metric_type': 'cosine'
    }
```

## 九、测试数据清理

### 9.1 按前缀清理

```python
def cleanup_test_data_by_prefix(prefix: str = 'test_'):
    """清理指定前缀的测试数据"""
    # 清理用户
    users = db.query(User).filter(User.username.like(f'{prefix}%')).all()
    for user in users:
        db.delete(user)

    # 清理工作流
    workflows = db.query(Workflow).filter(Workflow.name.like(f'%测试%')).all()
    for wf in workflows:
        db.delete(wf)

    db.commit()
```

### 9.2 按日期清理

```python
def cleanup_test_data_by_date(date: datetime):
    """清理指定日期的测试数据"""
    # 清理该日期创建的所有测试数据
    users = db.query(User).filter(
        User.created_at >= date,
        User.created_at < date + timedelta(days=1)
    ).all()
    for user in users:
        db.delete(user)

    db.commit()
```

## 十、测试数据管理

### 10.1 Fixture 管理

```python
@pytest.fixture
def test_user(db_session):
    """创建测试用户 Fixture"""
    user = User(**generate_test_user_data('data_engineer'))
    db_session.add(user)
    db_session.flush()

    yield user

    db_session.rollback()
```

### 10.2 批量 Fixture

```python
@pytest.fixture
def test_users(db_session):
    """批量创建测试用户 Fixture"""
    users = []
    for role in ['data_admin', 'data_engineer', 'ai_developer']:
        user = User(**generate_test_user_data(role))
        db_session.add(user)
        users.append(user)

    db_session.flush()

    yield users

    db_session.rollback()
```

## 十一、Mock 数据

### 11.1 API Mock

```typescript
// Mock 工作流列表 API
page.route('**/api/v1/agent/workflows', async (route) => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 0,
      data: {
        workflows: [
          {
            workflow_id: 'wf_001',
            name: '测试工作流',
            type: 'rag',
            status: 'stopped'
          }
        ],
        total: 1
      }
    })
  });
});
```

### 11.2 数据 Mock

```python
@pytest.fixture
def mock_workflow_data():
    """Mock 工作流数据"""
    return {
        'workflow_id': 'wf_mock_001',
        'name': 'Mock工作流',
        'type': 'rag',
        'status': 'stopped',
        'definition': {
            'nodes': [
                {'id': 'input', 'type': 'input'},
                {'id': 'output', 'type': 'output'}
            ],
            'edges': [
                {'source': 'input', 'target': 'output'}
            ]
        }
    }
```
