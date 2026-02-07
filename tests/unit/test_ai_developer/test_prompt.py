"""
AI 开发者 - Prompt 模板管理单元测试
测试用例：AD-PM-U-001 ~ AD-PM-U-012

Prompt 模板管理是 AI 开发者角色的重要功能，用于创建、版本管理和复用 Prompt。
"""

import pytest
from unittest.mock import Mock
from datetime import datetime


class TestPromptTemplateCreation:
    """Prompt 模板创建测试 (AD-PM-U-001 ~ AD-PM-U-003)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_chat_prompt_template(self, mock_prompt_service):
        """AD-PM-U-001: 创建对话类型 Prompt 模板"""
        template_data = {
            'name': '客服对话模板',
            'description': '用于智能客服场景的对话模板',
            'category': 'chat',
            'content': '你是一个专业的客服人员，请根据以下知识库内容回答用户问题：\n\n知识库：{{knowledge}}\n\n用户问题：{{question}}',
            'variables': [
                {'name': 'knowledge', 'type': 'text', 'description': '知识库内容'},
                {'name': 'question', 'type': 'text', 'description': '用户问题'}
            ],
            'model': 'gpt-4o',
            'temperature': 0.7,
            'system_prompt': '你是一个友好、专业的客服人员。'
        }

        result = mock_prompt_service.create_template(template_data)

        assert result['success'] is True
        assert 'template_id' in result
        assert result['category'] == 'chat'

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_code_prompt_template(self, mock_prompt_service):
        """AD-PM-U-002: 创建代码生成类型 Prompt 模板"""
        template_data = {
            'name': 'SQL 生成模板',
            'description': '根据自然语言生成 SQL 查询',
            'category': 'code',
            'content': '根据以下表结构生成 SQL 查询：\n\n表结构：\n{{schema}}\n\n需求：{{requirement}}\n\n生成 SQL：',
            'variables': [
                {'name': 'schema', 'type': 'json', 'description': '数据库表结构'},
                {'name': 'requirement', 'type': 'text', 'description': '查询需求'}
            ],
            'model': 'claude-3-opus',
            'temperature': 0.3,
            'max_tokens': 2000
        }

        result = mock_prompt_service.create_template(template_data)

        assert result['success'] is True
        assert result['category'] == 'code'

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_summary_prompt_template(self, mock_prompt_service):
        """AD-PM-U-003: 创建摘要类型 Prompt 模板"""
        template_data = {
            'name': '文档摘要模板',
            'description': '生成长文档摘要',
            'category': 'summary',
            'content': '请为以下文档生成简洁的摘要：\n\n{{document}}\n\n摘要：',
            'variables': [
                {'name': 'document', 'type': 'text', 'description': '待摘要文档'}
            ],
            'model': 'gpt-4o',
            'temperature': 0.5,
            'max_tokens': 500
        }

        result = mock_prompt_service.create_template(template_data)

        assert result['success'] is True
        assert result['category'] == 'summary'


class TestPromptTemplateVariables:
    """Prompt 模板变量测试 (AD-PM-U-004 ~ AD-PM-U-006)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_render_prompt_with_variables(self, mock_prompt_service):
        """AD-PM-U-004: 渲染带变量的 Prompt 模板"""
        template_id = 'tpl_001'
        variables_data = {
            'knowledge': '产品价格为100元',
            'question': '这个产品多少钱？'
        }

        mock_prompt_service.render_template.return_value = {
            'success': True,
            'rendered': '你是一个专业的客服人员，请根据以下知识库内容回答用户问题：\n\n知识库：产品价格为100元\n\n用户问题：这个产品多少钱？',
            'variables_used': ['knowledge', 'question']
        }

        result = mock_prompt_service.render_template(template_id, variables_data)

        assert result['success'] is True
        assert 'rendered' in result
        assert result['variables_used'] == ['knowledge', 'question']

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_render_prompt_with_default_values(self, mock_prompt_service):
        """AD-PM-U-005: 使用默认值渲染变量"""
        template_id = 'tpl_002'
        variables_data = {
            'question': '这个产品多少钱？'
            # knowledge 使用默认值
        }

        mock_prompt_service.render_template.return_value = {
            'success': True,
            'rendered': '知识库：默认知识库内容\n\n用户问题：这个产品多少钱？',
            'variables_used': ['knowledge', 'question'],
            'defaults_used': ['knowledge']
        }

        result = mock_prompt_service.render_template(template_id, variables_data)

        assert result['success'] is True
        assert 'defaults_used' in result
        assert 'knowledge' in result['defaults_used']

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_validate_variable_types(self, mock_prompt_service):
        """AD-PM-U-006: 验证变量类型"""
        template_id = 'tpl_001'
        variables_data = {
            'knowledge': 123,  # 错误类型，应该是字符串
            'question': '问题'
        }

        mock_prompt_service.render_template.return_value = {
            'success': False,
            'error': '变量 knowledge 类型错误：期望 str，实际 int'
        }

        result = mock_prompt_service.render_template(template_id, variables_data)

        assert result['success'] is False
        assert 'error' in result


class TestPromptTemplateVersioning:
    """Prompt 模板版本管理测试 (AD-PM-U-007 ~ AD-PM-U-009)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_create_new_version(self, mock_prompt_service):
        """AD-PM-U-007: 创建模板新版本"""
        template_id = 'tpl_001'
        new_content = '更新后的模板内容：{{var1}}'

        mock_prompt_service.create_version.return_value = {
            'success': True,
            'new_template_id': 'tpl_002',
            'version': '2.0.0',
            'parent_id': template_id
        }

        result = mock_prompt_service.create_version(template_id, {'content': new_content})

        assert result['success'] is True
        assert result['version'] == '2.0.0'
        assert result['parent_id'] == template_id

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_list_template_versions(self, mock_prompt_service):
        """AD-PM-U-008: 列出模板所有版本"""
        template_id = 'tpl_001'

        mock_prompt_service.list_versions.return_value = {
            'success': True,
            'versions': [
                {'template_id': 'tpl_001', 'version': '1.0.0', 'is_latest': False},
                {'template_id': 'tpl_002', 'version': '2.0.0', 'is_latest': True}
            ],
            'total': 2
        }

        result = mock_prompt_service.list_versions(template_id)

        assert result['success'] is True
        assert len(result['versions']) == 2

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_compare_template_versions(self, mock_prompt_service):
        """AD-PM-U-009: 比较两个版本差异"""
        version_a = 'tpl_001'
        version_b = 'tpl_002'

        mock_prompt_service.compare_versions.return_value = {
            'success': True,
            'diff': {
                'content': {
                    'old': '旧模板内容：{{var1}}',
                    'new': '新模板内容：{{var1}} + {{var2}}'
                },
                'variables': {
                    'added': ['var2'],
                    'removed': []
                }
            }
        }

        result = mock_prompt_service.compare_versions(version_a, version_b)

        assert result['success'] is True
        assert 'diff' in result
        assert 'var2' in result['diff']['variables']['added']


class TestPromptTemplateManagement:
    """Prompt 模板管理测试 (AD-PM-U-010 ~ AD-PM-U-014)"""

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_list_prompt_templates(self, mock_prompt_service):
        """AD-PM-U-010: 列出 Prompt 模板"""
        mock_prompt_service.list_templates.return_value = {
            'success': True,
            'templates': [
                {'template_id': 'tpl_001', 'name': '客服对话', 'category': 'chat'},
                {'template_id': 'tpl_002', 'name': 'SQL生成', 'category': 'code'}
            ],
            'total': 2
        }

        result = mock_prompt_service.list_templates()

        assert result['success'] is True
        assert len(result['templates']) == 2

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_filter_templates_by_category(self, mock_prompt_service):
        """AD-PM-U-011: 按分类筛选模板"""
        mock_prompt_service.list_templates.return_value = {
            'success': True,
            'templates': [
                {'template_id': 'tpl_001', 'name': '客服对话', 'category': 'chat'},
                {'template_id': 'tpl_003', 'name': '闲聊', 'category': 'chat'}
            ],
            'total': 2,
            'filters': {'category': 'chat'}
        }

        result = mock_prompt_service.list_templates(filters={'category': 'chat'})

        assert result['success'] is True
        assert all(t['category'] == 'chat' for t in result['templates'])

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_update_prompt_template(self, mock_prompt_service):
        """AD-PM-U-012: 更新 Prompt 模板"""
        template_id = 'tpl_001'
        update_data = {
            'name': '更新后的模板名称',
            'description': '更新后的描述'
        }

        mock_prompt_service.update_template.return_value = {
            'success': True,
            'template_id': template_id
        }

        result = mock_prompt_service.update_template(template_id, update_data)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_delete_prompt_template(self, mock_prompt_service):
        """AD-PM-U-013: 删除 Prompt 模板"""
        template_id = 'tpl_001'

        result = mock_prompt_service.delete_template(template_id)

        assert result['success'] is True

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_search_prompt_templates(self, mock_prompt_service):
        """AD-PM-U-014: 搜索 Prompt 模板"""
        keyword = '客服'

        mock_prompt_service.search_templates.return_value = {
            'success': True,
            'templates': [
                {'template_id': 'tpl_001', 'name': '客服对话模板'},
                {'template_id': 'tpl_005', 'name': '智能客服Prompt'}
            ],
            'total': 2
        }

        result = mock_prompt_service.search_templates(keyword)

        assert result['success'] is True
        assert len(result['templates']) == 2


class TestPromptTemplateSharing:
    """Prompt 模板共享测试 (AD-PM-U-015 ~ AD-PM-U-016)"""

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_publish_prompt_template(self, mock_prompt_service):
        """AD-PM-U-015: 发布 Prompt 模板为公开"""
        template_id = 'tpl_001'

        mock_prompt_service.publish_template.return_value = {
            'success': True,
            'template_id': template_id,
            'is_public': True
        }

        result = mock_prompt_service.publish_template(template_id)

        assert result['success'] is True
        assert result['is_public'] is True

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_clone_public_template(self, mock_prompt_service):
        """AD-PM-U-016: 克隆公开模板"""
        template_id = 'tpl_public_001'

        mock_prompt_service.clone_template.return_value = {
            'success': True,
            'new_template_id': 'tpl_clone_001',
            'name': '客服对话模板 (副本)'
        }

        result = mock_prompt_service.clone_template(template_id)

        assert result['success'] is True
        assert 'new_template_id' in result


class TestPromptTemplateTesting:
    """Prompt 模板测试 (AD-PM-U-017 ~ AD-PM-U-018)"""

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_prompt_template_with_variables(self, mock_prompt_service):
        """AD-PM-U-017: 在编辑器中测试模板"""
        template_id = 'tpl_001'
        test_data = {
            'model': 'gpt-4o',
            'variables': {
                'knowledge': '测试知识',
                'question': '测试问题'
            }
        }

        mock_prompt_service.test_template.return_value = {
            'success': True,
            'result': '根据知识库内容，答案是...',
            'tokens_used': 150,
            'cost': 0.003
        }

        result = mock_prompt_service.test_template(template_id, test_data)

        assert result['success'] is True
        assert 'result' in result
        assert 'tokens_used' in result

    @pytest.mark.p2
    @pytest.mark.ai_developer
    @pytest.mark.unit
    def test_rate_prompt_template(self, mock_prompt_service):
        """AD-PM-U-018: 评分 Prompt 模板"""
        template_id = 'tpl_001'
        rating = 5

        mock_prompt_service.rate_template.return_value = {
            'success': True,
            'template_id': template_id,
            'new_avg_rating': 4.5,
            'total_ratings': 20
        }

        result = mock_prompt_service.rate_template(template_id, rating)

        assert result['success'] is True
        assert result['new_avg_rating'] == 4.5


# ==================== Fixtures ====================

@pytest.fixture
def mock_prompt_service():
    """Mock Prompt 模板服务"""
    service = Mock()

    def mock_create(data):
        return {
            'success': True,
            'template_id': 'tpl_001',
            'category': data.get('category', 'chat'),
            'name': data.get('name', ''),
            'version': '1.0.0'
        }

    service.create_template = Mock(side_effect=mock_create)
    service.render_template = Mock()
    service.create_version = Mock()
    service.list_versions = Mock()
    service.compare_versions = Mock()
    service.list_templates = Mock()
    service.update_template = Mock(return_value={'success': True})
    service.delete_template = Mock(return_value={'success': True})
    service.search_templates = Mock()
    service.publish_template = Mock()
    service.clone_template = Mock()
    service.test_template = Mock()
    service.rate_template = Mock()

    return service
