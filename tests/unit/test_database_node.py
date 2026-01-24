"""
DatabaseNodeImpl 单元测试
tests/unit/test_database_node.py

测试数据库节点的 SQL 执行、安全防护、参数化查询等功能。
"""

import os
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock


# 设置测试环境
os.environ.setdefault('ENVIRONMENT', 'testing')


class TestDatabaseNodeInit:
    """测试数据库节点初始化"""

    def test_init_default_config(self):
        """默认配置初始化"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {})

        assert node.node_id == 'node_1'
        assert node.node_type == 'database'
        assert node.output_mode == 'rows'
        assert node.fetch_size == 100
        assert node.readonly is True

    def test_init_with_config(self):
        """自定义配置初始化"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        config = {
            'query': 'SELECT * FROM users',
            'connection': {'type': 'postgresql', 'host': 'localhost'},
            'output_mode': 'first',
            'fetch_size': 50,
            'readonly': False
        }

        node = DatabaseNodeImpl('node_1', config)

        assert node.query_template == 'SELECT * FROM users'
        assert node.connection_config['type'] == 'postgresql'
        assert node.output_mode == 'first'
        assert node.fetch_size == 50
        assert node.readonly is False


class TestSQLEscaping:
    """测试 SQL 值转义"""

    @pytest.fixture
    def node(self):
        """创建测试节点"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl
        return DatabaseNodeImpl('node_1', {})

    def test_escape_null(self, node):
        """None 转换为 NULL"""
        result = node._escape_sql_value(None)
        assert result == 'NULL'

    def test_escape_boolean_true(self, node):
        """True 转换为 TRUE"""
        result = node._escape_sql_value(True)
        assert result == 'TRUE'

    def test_escape_boolean_false(self, node):
        """False 转换为 FALSE"""
        result = node._escape_sql_value(False)
        assert result == 'FALSE'

    def test_escape_integer(self, node):
        """整数转换"""
        result = node._escape_sql_value(42)
        assert result == '42'

    def test_escape_float(self, node):
        """浮点数转换"""
        result = node._escape_sql_value(3.14)
        assert result == '3.14'

    def test_escape_string(self, node):
        """字符串转义"""
        result = node._escape_sql_value('hello')
        assert result == "'hello'"

    def test_escape_string_with_quotes(self, node):
        """含引号字符串转义"""
        result = node._escape_sql_value("it's a test")
        assert result == "'it''s a test'"

    def test_escape_list(self, node):
        """列表转换为 IN 子句"""
        result = node._escape_sql_value([1, 2, 3])
        assert result == '(1, 2, 3)'

    def test_escape_mixed_list(self, node):
        """混合类型列表"""
        result = node._escape_sql_value(['a', 1, True])
        assert "'a'" in result
        assert '1' in result
        assert 'TRUE' in result


class TestSQLInjectionPrevention:
    """测试 SQL 注入防护"""

    @pytest.fixture
    def node(self):
        """创建测试节点"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl
        return DatabaseNodeImpl('node_1', {})

    def test_reject_sql_comment(self, node):
        """拒绝 SQL 注释"""
        with pytest.raises(ValueError, match='dangerous SQL pattern'):
            node._escape_sql_value('value--comment')

    def test_reject_semicolon(self, node):
        """拒绝分号"""
        with pytest.raises(ValueError, match='dangerous SQL pattern'):
            node._escape_sql_value('value; DROP TABLE users')

    def test_reject_union(self, node):
        """拒绝 UNION 关键字"""
        with pytest.raises(ValueError, match='dangerous SQL pattern'):
            node._escape_sql_value('1 UNION SELECT * FROM passwords')

    def test_reject_drop(self, node):
        """拒绝 DROP 关键字"""
        with pytest.raises(ValueError, match='dangerous SQL pattern'):
            node._escape_sql_value('DROP TABLE users')

    def test_reject_delete(self, node):
        """拒绝 DELETE 关键字"""
        with pytest.raises(ValueError, match='dangerous SQL pattern'):
            node._escape_sql_value('DELETE FROM users')

    def test_reject_block_comment(self, node):
        """拒绝块注释"""
        with pytest.raises(ValueError, match='dangerous SQL pattern'):
            node._escape_sql_value('value /* comment */')

    def test_reject_or_1_equals_1(self, node):
        """拒绝 OR 1=1"""
        with pytest.raises(ValueError, match='dangerous SQL pattern'):
            node._escape_sql_value("' OR 1=1")


class TestQueryRendering:
    """测试查询渲染"""

    @pytest.fixture
    def node(self):
        """创建测试节点"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl
        return DatabaseNodeImpl('node_1', {'query': 'SELECT * FROM users WHERE id = {{user_id}}'})

    def test_render_simple_variable(self, node):
        """渲染简单变量"""
        context = {'user_id': 123}
        result = node._render_query('SELECT * FROM users WHERE id = {{user_id}}', context)

        assert '123' in result

    def test_render_nested_variable(self, node):
        """渲染嵌套变量"""
        context = {
            'node_a': {'output': 'test_value'}
        }
        result = node._render_query('SELECT * FROM data WHERE key = {{node_a.output}}', context)

        assert "'test_value'" in result

    def test_render_input_variable(self, node):
        """渲染输入变量"""
        context = {
            '_initial_input': {'query': 'SELECT 1'}
        }
        result = node._render_query('Query: {{inputs.query}}', context)

        assert "'SELECT 1'" in result or 'SELECT 1' in result


class TestGetQuery:
    """测试获取查询语句"""

    def test_get_query_from_template(self):
        """从模板获取查询"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'query': 'SELECT * FROM users'})
        result = node._get_query({})

        assert result == 'SELECT * FROM users'

    def test_get_query_from_context(self):
        """从上下文获取查询"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'query_from': 'generated_query'})
        context = {'generated_query': 'SELECT * FROM orders'}
        result = node._get_query(context)

        assert result == 'SELECT * FROM orders'

    def test_get_query_from_nested_context(self):
        """从嵌套上下文获取查询"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'query_from': 'node_a.query'})
        context = {'node_a': {'query': 'SELECT COUNT(*) FROM items'}}
        result = node._get_query(context)

        assert result == 'SELECT COUNT(*) FROM items'


class TestGetParameters:
    """测试获取参数"""

    def test_get_parameters_from_template(self):
        """从模板获取参数"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'parameters': [1, 'test', True]})
        result = node._get_parameters({})

        assert result == [1, 'test', True]

    def test_get_parameters_from_context(self):
        """从上下文获取参数"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'parameters_from': 'params'})
        context = {'params': [10, 20]}
        result = node._get_parameters(context)

        assert result == [10, 20]

    def test_get_parameters_with_variable_references(self):
        """带变量引用的参数"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'parameters': ['{{user_id}}', '{{name}}']})
        context = {'user_id': 42, 'name': 'Alice'}
        result = node._get_parameters(context)

        assert result == [42, 'Alice']


class TestFormatOutput:
    """测试输出格式化"""

    def test_format_output_rows(self):
        """rows 模式"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'output_mode': 'rows'})
        result = node._format_output({
            'rows': [{'id': 1}, {'id': 2}],
            'row_count': 2
        })

        assert result == [{'id': 1}, {'id': 2}]

    def test_format_output_first(self):
        """first 模式"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'output_mode': 'first'})
        result = node._format_output({
            'rows': [{'id': 1, 'name': 'Alice'}, {'id': 2}],
            'row_count': 2
        })

        assert result == {'id': 1, 'name': 'Alice'}

    def test_format_output_first_empty(self):
        """first 模式空结果"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'output_mode': 'first'})
        result = node._format_output({'rows': [], 'row_count': 0})

        assert result is None

    def test_format_output_value(self):
        """value 模式"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'output_mode': 'value'})
        result = node._format_output({
            'rows': [{'count': 42}],
            'row_count': 1
        })

        assert result == 42

    def test_format_output_count(self):
        """count 模式"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'output_mode': 'count'})
        result = node._format_output({
            'rows': [{'id': 1}, {'id': 2}, {'id': 3}],
            'row_count': 3
        })

        assert result == 3

    def test_format_output_affected(self):
        """affected 模式"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'output_mode': 'affected'})
        result = node._format_output({
            'rows': [],
            'row_count': 0,
            'affected_rows': 5
        })

        assert result == 5

    def test_format_output_exists(self):
        """exists 模式"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'output_mode': 'exists'})
        result = node._format_output({'rows': [{'id': 1}], 'row_count': 1})

        assert result is True

        result = node._format_output({'rows': [], 'row_count': 0})

        assert result is False


class TestNestedValueAccess:
    """测试嵌套值访问"""

    @pytest.fixture
    def node(self):
        """创建测试节点"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl
        return DatabaseNodeImpl('node_1', {})

    def test_get_nested_value_simple(self, node):
        """简单嵌套值"""
        data = {'a': {'b': {'c': 'value'}}}
        result = node._get_nested_value(data, ['a', 'b', 'c'])

        assert result == 'value'

    def test_get_nested_value_list_index(self, node):
        """列表索引访问"""
        data = {'items': [{'name': 'first'}, {'name': 'second'}]}
        result = node._get_nested_value(data, ['items', '1', 'name'])

        assert result == 'second'

    def test_get_nested_value_missing_key(self, node):
        """缺失键返回 None"""
        data = {'a': {'b': 1}}
        result = node._get_nested_value(data, ['a', 'c'])

        assert result is None

    def test_get_nested_value_index_out_of_range(self, node):
        """索引越界返回 None"""
        data = {'items': [1, 2]}
        result = node._get_nested_value(data, ['items', '5'])

        assert result is None


class TestValidation:
    """测试配置验证"""

    def test_validate_with_query_template(self):
        """有查询模板时验证通过"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'query': 'SELECT 1'})
        assert node.validate() is True

    def test_validate_with_query_from(self):
        """有 query_from 时验证通过"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {'query_from': 'ctx.query'})
        assert node.validate() is True

    def test_validate_without_query(self):
        """没有查询时验证失败"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {})
        assert node.validate() is False

    def test_validate_sets_default_db_type(self):
        """验证时设置默认数据库类型"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {
            'query': 'SELECT 1',
            'connection': {'type': 'invalid_db'}
        })
        node.validate()

        assert node.connection_config['type'] == 'sqlite'


class TestMockResult:
    """测试 Mock 结果"""

    def test_mock_result_select(self):
        """Mock SELECT 结果"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

            node = DatabaseNodeImpl('node_1', {})
            result = node._mock_result('SELECT * FROM users', [])

            assert result['mock'] is True
            assert len(result['rows']) == 2
            assert 'warning' in result

    def test_mock_result_insert(self):
        """Mock INSERT 结果"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

            node = DatabaseNodeImpl('node_1', {})
            result = node._mock_result('INSERT INTO users VALUES (1)', [])

            assert result['mock'] is True
            assert result['affected_rows'] == 1
            assert result['rows'] == []

    def test_mock_result_production_raises_error(self):
        """生产环境不返回 Mock"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

            node = DatabaseNodeImpl('node_1', {})

            with pytest.raises(RuntimeError, match='production environment'):
                node._mock_result('SELECT 1', [])


class TestExecuteQuery:
    """测试查询执行"""

    @pytest.fixture
    def node(self):
        """创建测试节点"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl
        return DatabaseNodeImpl('node_1', {
            'query': 'SELECT * FROM users',
            'connection': {'type': 'sqlite', 'path': ':memory:'}
        })

    @pytest.mark.asyncio
    async def test_execute_sqlite_select(self, node):
        """执行 SQLite SELECT"""
        # 创建临时表并查询
        node.query_template = '''
            CREATE TABLE IF NOT EXISTS test (id INTEGER, name TEXT);
        '''

        # 使用真实的 SQLite
        result = await node._execute_sqlite(
            'SELECT 1 as value',
            []
        )

        assert result['rows'] == [{'value': 1}]
        assert result['row_count'] == 1

    @pytest.mark.asyncio
    async def test_execute_unsupported_db_type(self, node):
        """不支持的数据库类型"""
        node.connection_config['type'] = 'oracle'

        with pytest.raises(ValueError, match='Unsupported database type'):
            await node._execute_query('SELECT 1', [])

    @pytest.mark.asyncio
    async def test_execute_postgresql_without_driver(self, node):
        """没有 PostgreSQL 驱动时返回 Mock"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            node.connection_config = {
                'type': 'postgresql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }

            # 模拟 asyncpg 导入失败
            with patch.dict('sys.modules', {'asyncpg': None}):
                result = await node._execute_postgresql('SELECT 1', [])

                assert result['mock'] is True

    @pytest.mark.asyncio
    async def test_execute_mysql_without_driver(self, node):
        """没有 MySQL 驱动时返回 Mock"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            node.connection_config = {
                'type': 'mysql',
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }

            # 模拟 aiomysql 导入失败
            with patch.dict('sys.modules', {'aiomysql': None}):
                result = await node._execute_mysql('SELECT 1', [])

                assert result['mock'] is True


class TestExecuteNode:
    """测试节点执行"""

    @pytest.mark.asyncio
    async def test_execute_no_query(self):
        """没有查询时返回错误"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {})
        result = await node.execute({})

        assert result['node_1']['error'] == 'No query specified'
        assert result['node_1']['output'] is None

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """成功执行"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {
            'query': 'SELECT 1 as value',
            'connection': {'type': 'sqlite', 'path': ':memory:'}
        })

        result = await node.execute({})

        assert result['node_1']['success'] is True
        assert result['node_1']['rows'] == [{'value': 1}]

    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """执行错误"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {
            'query': 'SELECT * FROM nonexistent_table',
            'connection': {'type': 'sqlite', 'path': ':memory:'}
        })

        result = await node.execute({})

        assert result['node_1']['success'] is False
        assert 'error' in result['node_1']


class TestCredentialValidation:
    """测试凭据验证"""

    @pytest.mark.asyncio
    async def test_postgresql_missing_database(self):
        """PostgreSQL 缺少数据库名称"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {
            'query': 'SELECT 1',
            'connection': {
                'type': 'postgresql',
                'username': 'user',
                'password': 'pass'
                # 缺少 database
            }
        })

        # 模拟 asyncpg 可用
        mock_asyncpg = MagicMock()
        with patch.dict('sys.modules', {'asyncpg': mock_asyncpg}):
            with pytest.raises(ValueError, match='database name is required'):
                await node._execute_postgresql('SELECT 1', [])

    @pytest.mark.asyncio
    async def test_mysql_missing_username(self):
        """MySQL 缺少用户名"""
        from services.bisheng_api.engine.extension_nodes.database import DatabaseNodeImpl

        node = DatabaseNodeImpl('node_1', {
            'query': 'SELECT 1',
            'connection': {
                'type': 'mysql',
                'database': 'test',
                'password': 'pass'
                # 缺少 username
            }
        })

        mock_aiomysql = MagicMock()
        with patch.dict('sys.modules', {'aiomysql': mock_aiomysql}):
            with pytest.raises(ValueError, match='username is required'):
                await node._execute_mysql('SELECT 1', [])
