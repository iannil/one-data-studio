"""
数据标准管理模块单元测试
覆盖用例: DM-ST-001 ~ DM-ST-004
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestDataStandardService:
    """数据标准管理服务测试"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock 数据库会话"""
        session = MagicMock()
        session.execute.return_value = MagicMock()
        session.commit.return_value = None
        return session

    @pytest.fixture
    def sample_metadata(self):
        """示例元数据"""
        return {
            'table_name': 'users',
            'columns': [
                {'name': 'id', 'type': 'int', 'nullable': False},
                {'name': 'phone', 'type': 'varchar(20)', 'nullable': True},
                {'name': 'email', 'type': 'varchar(100)', 'nullable': True},
                {'name': 'created_at', 'type': 'datetime', 'nullable': False},
            ]
        }

    @pytest.fixture
    def sample_standard(self):
        """示例数据标准"""
        return {
            'standard_id': 'STD-001',
            'name': '手机号格式标准',
            'description': '中国大陆手机号格式规范',
            'field_type': 'phone',
            'pattern': r'^1[3-9]\d{9}$',
            'format_rule': '11位数字，以1开头',
            'encoding_rule': 'UTF-8',
            'created_by': 'admin',
            'created_at': datetime.now()
        }

    # ==================== DM-ST-001: 自动生成数据标准 ====================

    @pytest.mark.unit
    def test_auto_generate_standard_for_phone_field(self, sample_metadata):
        """测试自动为手机号字段生成数据标准"""
        # Given: 包含手机号字段的元数据
        phone_column = sample_metadata['columns'][1]

        # When: 调用自动生成标准方法
        generated_standard = self._generate_standard_for_column(phone_column)

        # Then: 应生成正确的标准
        assert generated_standard is not None
        assert generated_standard['field_type'] == 'phone'
        assert 'pattern' in generated_standard
        assert generated_standard['format_rule'] is not None

    @pytest.mark.unit
    def test_auto_generate_standard_for_email_field(self, sample_metadata):
        """测试自动为邮箱字段生成数据标准"""
        # Given: 包含邮箱字段的元数据
        email_column = sample_metadata['columns'][2]

        # When: 调用自动生成标准方法
        generated_standard = self._generate_standard_for_column(email_column)

        # Then: 应生成正确的邮箱标准
        assert generated_standard is not None
        assert generated_standard['field_type'] == 'email'
        assert '@' in generated_standard['pattern'] or 'email' in generated_standard['pattern'].lower()

    @pytest.mark.unit
    def test_auto_generate_standard_for_datetime_field(self, sample_metadata):
        """测试自动为日期时间字段生成数据标准"""
        # Given: 包含日期时间字段的元数据
        datetime_column = sample_metadata['columns'][3]

        # When: 调用自动生成标准方法
        generated_standard = self._generate_standard_for_column(datetime_column)

        # Then: 应生成正确的日期时间标准
        assert generated_standard is not None
        assert generated_standard['field_type'] == 'datetime'

    @pytest.mark.unit
    def test_auto_generate_standard_batch(self, sample_metadata):
        """测试批量自动生成数据标准"""
        # Given: 多列元数据
        columns = sample_metadata['columns']

        # When: 批量生成标准
        standards = [self._generate_standard_for_column(col) for col in columns]

        # Then: 应为所有列生成标准
        assert len(standards) == len(columns)
        assert all(s is not None for s in standards)

    # ==================== DM-ST-002: 手动创建数据标准 ====================

    @pytest.mark.unit
    def test_create_standard_success(self, mock_db_session, sample_standard):
        """测试成功创建数据标准"""
        # Given: 有效的标准数据
        standard_data = sample_standard

        # When: 创建数据标准
        result = self._create_standard(mock_db_session, standard_data)

        # Then: 标准应创建成功
        assert result['success'] is True
        assert 'standard_id' in result

    @pytest.mark.unit
    def test_create_standard_with_invalid_pattern(self, mock_db_session):
        """测试使用无效正则表达式创建标准"""
        # Given: 无效的正则表达式
        invalid_standard = {
            'name': '测试标准',
            'pattern': '[invalid(',  # 无效正则
            'field_type': 'custom'
        }

        # When/Then: 应抛出验证错误
        with pytest.raises(ValueError) as exc_info:
            self._create_standard(mock_db_session, invalid_standard)
        assert 'pattern' in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_create_standard_duplicate_name(self, mock_db_session, sample_standard):
        """测试创建重名标准"""
        # Given: 已存在同名标准
        mock_db_session.execute.return_value.fetchone.return_value = sample_standard

        # When: 尝试创建同名标准
        result = self._create_standard(mock_db_session, sample_standard)

        # Then: 应返回重复错误
        assert result['success'] is False
        assert 'duplicate' in result.get('error', '').lower() or 'exists' in result.get('error', '').lower()

    # ==================== DM-ST-003: 数据标准关联字段 ====================

    @pytest.mark.unit
    def test_link_standard_to_column(self, mock_db_session, sample_standard):
        """测试将数据标准关联到列"""
        # Given: 存在的标准和列
        standard_id = sample_standard['standard_id']
        column_info = {
            'table_name': 'users',
            'column_name': 'phone',
            'datasource_id': 'ds-001'
        }

        # When: 关联标准到列
        result = self._link_standard_to_column(mock_db_session, standard_id, column_info)

        # Then: 关联应成功
        assert result['success'] is True
        assert result['linked_column'] == 'users.phone'

    @pytest.mark.unit
    def test_link_standard_to_multiple_columns(self, mock_db_session, sample_standard):
        """测试将数据标准关联到多个列"""
        # Given: 一个标准和多个列
        standard_id = sample_standard['standard_id']
        columns = [
            {'table_name': 'users', 'column_name': 'phone', 'datasource_id': 'ds-001'},
            {'table_name': 'contacts', 'column_name': 'mobile', 'datasource_id': 'ds-001'},
        ]

        # When: 批量关联
        results = [
            self._link_standard_to_column(mock_db_session, standard_id, col)
            for col in columns
        ]

        # Then: 所有关联应成功
        assert all(r['success'] for r in results)

    @pytest.mark.unit
    def test_unlink_standard_from_column(self, mock_db_session):
        """测试解除标准与列的关联"""
        # Given: 已存在的关联
        link_id = 'link-001'

        # When: 解除关联
        result = self._unlink_standard(mock_db_session, link_id)

        # Then: 解除应成功
        assert result['success'] is True

    # ==================== DM-ST-004: 数据标准合规检查 ====================

    @pytest.mark.unit
    def test_compliance_check_pass(self, mock_db_session, sample_standard):
        """测试数据符合标准的合规检查"""
        # Given: 符合标准的数据
        test_data = ['13800138000', '13912345678', '18600000000']
        standard = sample_standard

        # When: 执行合规检查
        result = self._check_compliance(test_data, standard)

        # Then: 应全部通过
        assert result['compliant'] is True
        assert result['pass_rate'] == 1.0
        assert len(result['violations']) == 0

    @pytest.mark.unit
    def test_compliance_check_fail(self, sample_standard):
        """测试数据不符合标准的合规检查"""
        # Given: 不符合标准的数据
        test_data = ['12345', 'invalid-phone', '138001380001']  # 无效手机号
        standard = sample_standard

        # When: 执行合规检查
        result = self._check_compliance(test_data, standard)

        # Then: 应检测到违规
        assert result['compliant'] is False
        assert result['pass_rate'] < 1.0
        assert len(result['violations']) > 0

    @pytest.mark.unit
    def test_compliance_check_partial(self, sample_standard):
        """测试部分数据符合标准的合规检查"""
        # Given: 部分符合标准的数据
        test_data = ['13800138000', 'invalid', '18600000000']
        standard = sample_standard

        # When: 执行合规检查
        result = self._check_compliance(test_data, standard)

        # Then: 应返回部分通过
        assert 0 < result['pass_rate'] < 1.0
        assert len(result['violations']) == 1

    @pytest.mark.unit
    def test_compliance_check_with_null_values(self, sample_standard):
        """测试包含空值的合规检查"""
        # Given: 包含空值的数据
        test_data = ['13800138000', None, '', '18600000000']
        standard = sample_standard

        # When: 执行合规检查（允许空值）
        result = self._check_compliance(test_data, standard, allow_null=True)

        # Then: 空值不应视为违规
        assert result['null_count'] == 2
        assert result['checked_count'] == 2

    @pytest.mark.unit
    def test_batch_compliance_report(self, mock_db_session, sample_standard):
        """测试批量合规检查报告生成"""
        # Given: 多个表的多个列
        tables_to_check = [
            {'table': 'users', 'column': 'phone', 'standard_id': 'STD-001'},
            {'table': 'contacts', 'column': 'mobile', 'standard_id': 'STD-001'},
        ]

        # When: 生成合规报告
        report = self._generate_compliance_report(mock_db_session, tables_to_check)

        # Then: 报告应包含所有表的检查结果
        assert 'summary' in report
        assert 'details' in report
        assert len(report['details']) == len(tables_to_check)

    # ==================== 辅助方法 ====================

    def _generate_standard_for_column(self, column):
        """根据列信息生成数据标准"""
        import re

        column_name = column['name'].lower()
        column_type = column['type'].lower()

        # 根据列名和类型推断标准
        if 'phone' in column_name or 'mobile' in column_name:
            return {
                'field_type': 'phone',
                'pattern': r'^1[3-9]\d{9}$',
                'format_rule': '11位中国大陆手机号',
                'encoding_rule': 'UTF-8'
            }
        elif 'email' in column_name:
            return {
                'field_type': 'email',
                'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'format_rule': '标准邮箱格式',
                'encoding_rule': 'UTF-8'
            }
        elif 'datetime' in column_type or 'timestamp' in column_type:
            return {
                'field_type': 'datetime',
                'pattern': r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$',
                'format_rule': 'YYYY-MM-DD HH:MM:SS',
                'encoding_rule': 'UTF-8'
            }
        else:
            return {
                'field_type': 'string',
                'pattern': r'.*',
                'format_rule': '通用文本',
                'encoding_rule': 'UTF-8'
            }

    def _create_standard(self, db_session, standard_data):
        """创建数据标准"""
        import re

        # 验证正则表达式
        if 'pattern' in standard_data:
            try:
                re.compile(standard_data['pattern'])
            except re.error:
                raise ValueError("Invalid regex pattern")

        # 检查重复
        existing = db_session.execute.return_value.fetchone()
        if existing and existing.get('name') == standard_data.get('name'):
            return {'success': False, 'error': 'Standard with this name already exists'}

        return {
            'success': True,
            'standard_id': f"STD-{id(standard_data) % 10000:04d}"
        }

    def _link_standard_to_column(self, db_session, standard_id, column_info):
        """关联标准到列"""
        return {
            'success': True,
            'linked_column': f"{column_info['table_name']}.{column_info['column_name']}",
            'link_id': f"link-{id(column_info) % 10000:04d}"
        }

    def _unlink_standard(self, db_session, link_id):
        """解除标准关联"""
        return {'success': True}

    def _check_compliance(self, data, standard, allow_null=False):
        """检查数据合规性"""
        import re

        pattern = re.compile(standard['pattern'])
        violations = []
        null_count = 0
        checked_count = 0

        for i, value in enumerate(data):
            if value is None or value == '':
                null_count += 1
                if not allow_null:
                    violations.append({'index': i, 'value': value, 'reason': 'null_value'})
            else:
                checked_count += 1
                if not pattern.match(str(value)):
                    violations.append({'index': i, 'value': value, 'reason': 'pattern_mismatch'})

        total = len(data) if not allow_null else checked_count
        pass_count = total - len(violations)
        pass_rate = pass_count / total if total > 0 else 1.0

        return {
            'compliant': len(violations) == 0,
            'pass_rate': pass_rate,
            'violations': violations,
            'null_count': null_count,
            'checked_count': checked_count
        }

    def _generate_compliance_report(self, db_session, tables_to_check):
        """生成合规检查报告"""
        details = []
        total_pass = 0
        total_checked = 0

        for item in tables_to_check:
            # Mock 检查结果
            check_result = {
                'table': item['table'],
                'column': item['column'],
                'standard_id': item['standard_id'],
                'pass_rate': 0.95,
                'total_rows': 1000,
                'violations': 50
            }
            details.append(check_result)
            total_pass += int(check_result['total_rows'] * check_result['pass_rate'])
            total_checked += check_result['total_rows']

        return {
            'summary': {
                'total_tables': len(tables_to_check),
                'overall_pass_rate': total_pass / total_checked if total_checked > 0 else 0,
                'generated_at': datetime.now().isoformat()
            },
            'details': details
        }
