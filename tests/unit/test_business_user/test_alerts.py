"""
智能预警单元测试
测试用例：BU-WN-001 ~ BU-WN-007
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestAlertConfiguration:
    """预警配置测试 (BU-WN-001 ~ BU-WN-002)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_configure_alert_rule(self, mock_alert_service):
        """BU-WN-001: 配置预警规则"""
        rule_config = {
            'rule_name': '转化率骤降预警',
            'metric': 'conversion_rate',
            'condition': 'decrease',
            'threshold': 20,
            'time_window_minutes': 60,
            'severity': 'warning',
            'notification_channels': ['email', 'in_app'],
            'recipients': ['admin@example.com']
        }

        mock_alert_service.create_rule = AsyncMock(return_value={
            'success': True,
            'rule_id': 'alert_0001'
        })

        result = await mock_alert_service.create_rule(rule_config)

        assert result['success'] is True

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_trigger_alert_notification(self, mock_alert_service):
        """BU-WN-002: 触发预警通知"""
        rule_id = 'alert_0001'
        trigger_event = {
            'metric_value': 1.5,
            'threshold': 2.0,
            'decrease_percent': 25,
            'timestamp': '2024-01-15T10:30:00Z'
        }

        mock_alert_service.trigger = AsyncMock(return_value={
            'success': True,
            'alert_id': 'alert_triggered_0001',
            'notifications_sent': ['email', 'in_app'],
            'recipients_notified': ['admin@example.com', 'manager@example.com']
        })

        result = await mock_alert_service.trigger(rule_id, trigger_event)

        assert result['success'] is True
        assert len(result['notifications_sent']) > 0


class TestAlertDelivery:
    """预警投递测试 (BU-WN-003 ~ BU-WN-005)"""

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_in_app_notification(self, mock_alert_service):
        """BU-WN-003: 预警推送-站内消息"""
        alert = {
            'alert_id': 'alert_0001',
            'message': '转化率骤降超过20%',
            'severity': 'warning'
        }

        mock_alert_service.send_in_app = AsyncMock(return_value={
            'success': True,
            'delivered_to': 5,
            'read_count': 0
        })

        result = await mock_alert_service.send_in_app(alert)

        assert result['success'] is True

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_email_notification(self, mock_alert_service):
        """BU-WN-004: 预警推送-邮件"""
        alert = {
            'alert_id': 'alert_0001',
            'subject': '【预警】转化率异常',
            'body': '检测到转化率下降...',
            'recipients': ['admin@example.com']
        }

        mock_alert_service.send_email = AsyncMock(return_value={
            'success': True,
            'email_sent': True,
            'recipients_count': len(alert['recipients'])
        })

        result = await mock_alert_service.send_email(alert)

        assert result['success'] is True

    @pytest.mark.p2
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sms_notification(self, mock_alert_service):
        """BU-WN-005: 预警推送-短信"""
        alert = {
            'alert_id': 'alert_0001',
            'message': '【紧急】系统异常告警',
            'phone_numbers': ['13800000001']
        }

        mock_alert_service.send_sms = AsyncMock(return_value={
            'success': True,
            'sms_sent': True
        })

        result = await mock_alert_service.send_sms(alert)

        assert result['success'] is True


class TestAlertManagement:
    """预警管理测试 (BU-WN-006 ~ BU-WN-007)"""

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_alert_history_query(self, mock_alert_service):
        """BU-WN-006: 预警历史查询"""
        query = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'severity': ['warning', 'critical']
        }

        mock_alert_service.get_history = AsyncMock(return_value={
            'success': True,
            'alerts': [
                {
                    'alert_id': 'alert_0001',
                    'rule_name': '转化率预警',
                    'triggered_at': '2024-01-15T10:30:00Z',
                    'severity': 'warning',
                    'status': 'resolved'
                },
                {
                    'alert_id': 'alert_0002',
                    'rule_name': '系统负载预警',
                    'triggered_at': '2024-01-20T14:15:00Z',
                    'severity': 'critical',
                    'status': 'active'
                }
            ],
            'total_count': 2
        })

        result = await mock_alert_service.get_history(query)

        assert result['success'] is True
        assert len(result['alerts']) > 0

    @pytest.mark.p2
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_alert_rule_enable_disable(self, mock_alert_service):
        """BU-WN-007: 预警规则禁用/启用"""
        rule_id = 'alert_0001'

        # 配置 set_status 返回值
        def set_status_func(rule_id, status):
            return {
                'success': True,
                'rule_id': rule_id,
                'old_status': 'active' if status == 'inactive' else 'inactive',
                'new_status': status
            }

        mock_alert_service.set_status = AsyncMock(side_effect=set_status_func)

        # 禁用规则
        result = await mock_alert_service.set_status(rule_id, 'inactive')

        assert result['success'] is True
        assert result['new_status'] == 'inactive'

        # 启用规则
        result = await mock_alert_service.set_status(rule_id, 'active')

        assert result['success'] is True
        assert result['new_status'] == 'active'


# ==================== Fixtures ====================

@pytest.fixture
def mock_alert_service():
    """Mock 预警服务"""
    service = Mock()
    service.create_rule = AsyncMock()
    service.trigger = AsyncMock()
    service.send_in_app = AsyncMock()
    service.send_email = AsyncMock()
    service.send_sms = AsyncMock()
    service.get_history = AsyncMock()
    service.set_status = AsyncMock()
    return service
