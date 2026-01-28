"""
智能预警模块单元测试
覆盖用例: BU-WN-001 ~ BU-WN-007
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import List, Dict, Any


class TestSmartAlertService:
    """智能预警服务测试"""

    @pytest.fixture
    def sample_alert_rule(self):
        """示例预警规则"""
        return {
            'rule_id': 'RULE-001',
            'name': '转化率骤降预警',
            'metric': 'conversion_rate',
            'condition': 'drop_percentage',
            'threshold': 20,
            'time_window': 3600,  # 1小时
            'severity': 'critical',
            'notification_channels': ['email', 'sms', 'in_app'],
            'recipients': ['admin@example.com', '+8613800138000'],
            'enabled': True,
            'created_by': 'admin',
            'created_at': datetime.now()
        }

    @pytest.fixture
    def sample_metrics(self):
        """示例监控指标"""
        base_time = datetime.now()
        return {
            'metric_name': 'conversion_rate',
            'values': [
                {'timestamp': base_time - timedelta(hours=3), 'value': 5.2},
                {'timestamp': base_time - timedelta(hours=2), 'value': 5.0},
                {'timestamp': base_time - timedelta(hours=1), 'value': 4.8},
                {'timestamp': base_time, 'value': 3.5},  # 突然下降
            ]
        }

    @pytest.fixture
    def alert_service(self):
        """预警服务实例"""
        return SmartAlertService()

    @pytest.fixture
    def mock_notification_service(self):
        """Mock 通知服务"""
        service = MagicMock()
        service.send_email = AsyncMock(return_value=True)
        service.send_sms = AsyncMock(return_value=True)
        service.send_in_app = AsyncMock(return_value=True)
        return service

    # ==================== BU-WN-001: 配置预警规则 ====================

    @pytest.mark.unit
    def test_create_alert_rule_success(self, alert_service, sample_alert_rule):
        """测试成功创建预警规则"""
        # Given: 有效的规则配置
        rule_config = sample_alert_rule

        # When: 创建规则
        result = alert_service.create_rule(rule_config)

        # Then: 规则应创建成功
        assert result['success'] is True
        assert 'rule_id' in result
        assert result['rule']['enabled'] is True

    @pytest.mark.unit
    def test_create_alert_rule_with_threshold(self, alert_service):
        """测试创建带阈值的预警规则"""
        # Given: 阈值配置
        rule_config = {
            'name': '销售额阈值预警',
            'metric': 'daily_sales',
            'condition': 'below_threshold',
            'threshold': 10000,
            'severity': 'warning',
            'notification_channels': ['email']
        }

        # When: 创建规则
        result = alert_service.create_rule(rule_config)

        # Then: 应正确配置阈值
        assert result['success'] is True
        assert result['rule']['threshold'] == 10000
        assert result['rule']['condition'] == 'below_threshold'

    @pytest.mark.unit
    def test_create_alert_rule_with_multiple_conditions(self, alert_service):
        """测试创建多条件预警规则"""
        # Given: 多条件配置
        rule_config = {
            'name': '复合预警',
            'conditions': [
                {'metric': 'cpu_usage', 'operator': '>', 'value': 80},
                {'metric': 'memory_usage', 'operator': '>', 'value': 90}
            ],
            'logic': 'OR',  # 满足任一条件即触发
            'severity': 'critical',
            'notification_channels': ['email', 'sms']
        }

        # When: 创建规则
        result = alert_service.create_rule(rule_config)

        # Then: 应支持多条件
        assert result['success'] is True
        assert len(result['rule'].get('conditions', [])) == 2

    @pytest.mark.unit
    def test_validate_alert_rule_invalid_threshold(self, alert_service):
        """测试无效阈值验证"""
        # Given: 无效阈值
        rule_config = {
            'name': '无效规则',
            'metric': 'rate',
            'condition': 'drop_percentage',
            'threshold': -10,  # 无效：负数百分比
            'severity': 'warning'
        }

        # When/Then: 应验证失败
        with pytest.raises(ValueError) as exc_info:
            alert_service.create_rule(rule_config)
        assert 'threshold' in str(exc_info.value).lower()

    # ==================== BU-WN-002: 触发预警通知 ====================

    @pytest.mark.unit
    def test_trigger_alert_on_threshold_breach(self, alert_service, sample_alert_rule, sample_metrics):
        """测试阈值突破触发预警"""
        # Given: 规则和指标数据
        alert_service.create_rule(sample_alert_rule)
        metrics = sample_metrics

        # When: 评估指标
        result = alert_service.evaluate_metrics(
            rule_id=sample_alert_rule['rule_id'],
            metrics=metrics['values']
        )

        # Then: 应触发预警（转化率下降超过20%）
        assert result['triggered'] is True
        assert result['severity'] == 'critical'
        assert 'drop_percentage' in result or 'change' in result

    @pytest.mark.unit
    def test_no_alert_when_within_threshold(self, alert_service, sample_alert_rule):
        """测试阈值内不触发预警"""
        # Given: 规则和正常指标
        alert_service.create_rule(sample_alert_rule)
        normal_metrics = [
            {'timestamp': datetime.now() - timedelta(hours=1), 'value': 5.0},
            {'timestamp': datetime.now(), 'value': 4.8},  # 仅下降 4%
        ]

        # When: 评估指标
        result = alert_service.evaluate_metrics(
            rule_id=sample_alert_rule['rule_id'],
            metrics=normal_metrics
        )

        # Then: 不应触发预警
        assert result['triggered'] is False

    @pytest.mark.unit
    def test_alert_cooldown_period(self, alert_service, sample_alert_rule, sample_metrics):
        """测试预警冷却期"""
        # Given: 规则配置冷却期
        sample_alert_rule['cooldown_minutes'] = 30
        alert_service.create_rule(sample_alert_rule)

        # When: 连续两次触发
        first_result = alert_service.evaluate_metrics(
            rule_id=sample_alert_rule['rule_id'],
            metrics=sample_metrics['values']
        )
        second_result = alert_service.evaluate_metrics(
            rule_id=sample_alert_rule['rule_id'],
            metrics=sample_metrics['values']
        )

        # Then: 第二次应在冷却期内
        assert first_result['triggered'] is True
        assert second_result.get('in_cooldown', False) is True or second_result['triggered'] is False

    # ==================== BU-WN-003 ~ BU-WN-005: 预警推送渠道 ====================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_in_app_notification(self, alert_service, mock_notification_service):
        """测试站内消息推送"""
        # Given: 预警信息
        alert = {
            'alert_id': 'ALERT-001',
            'rule_id': 'RULE-001',
            'title': '转化率下降预警',
            'message': '转化率在过去1小时内下降了25%',
            'severity': 'critical',
            'timestamp': datetime.now()
        }
        alert_service.notification_service = mock_notification_service

        # When: 发送站内消息
        result = await alert_service.send_notification(alert, channel='in_app', recipient='user_001')

        # Then: 应成功发送
        assert result['success'] is True
        mock_notification_service.send_in_app.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_email_notification(self, alert_service, mock_notification_service):
        """测试邮件预警推送"""
        # Given: 预警信息
        alert = {
            'alert_id': 'ALERT-001',
            'title': '销售额预警',
            'message': '日销售额低于阈值',
            'severity': 'warning'
        }
        alert_service.notification_service = mock_notification_service

        # When: 发送邮件
        result = await alert_service.send_notification(
            alert, channel='email', recipient='admin@example.com'
        )

        # Then: 应成功发送
        assert result['success'] is True
        mock_notification_service.send_email.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_sms_notification(self, alert_service, mock_notification_service):
        """测试短信预警推送"""
        # Given: 紧急预警
        alert = {
            'alert_id': 'ALERT-001',
            'title': '系统故障',
            'message': '服务不可用',
            'severity': 'critical'
        }
        alert_service.notification_service = mock_notification_service

        # When: 发送短信
        result = await alert_service.send_notification(
            alert, channel='sms', recipient='+8613800138000'
        )

        # Then: 应成功发送
        assert result['success'] is True
        mock_notification_service.send_sms.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multi_channel_notification(self, alert_service, mock_notification_service, sample_alert_rule):
        """测试多渠道推送"""
        # Given: 配置多渠道的规则
        alert_service.notification_service = mock_notification_service
        alert = {
            'alert_id': 'ALERT-001',
            'rule_id': sample_alert_rule['rule_id'],
            'title': '综合预警',
            'message': '多指标异常',
            'severity': 'critical'
        }

        # When: 发送到所有配置的渠道
        results = await alert_service.send_to_all_channels(
            alert,
            channels=['email', 'sms', 'in_app'],
            recipients={
                'email': ['admin@example.com'],
                'sms': ['+8613800138000'],
                'in_app': ['user_001']
            }
        )

        # Then: 所有渠道应都发送
        assert len(results) == 3
        assert all(r['success'] for r in results)

    # ==================== BU-WN-006: 预警历史查询 ====================

    @pytest.mark.unit
    def test_query_alert_history(self, alert_service):
        """测试查询预警历史"""
        # Given: 存在历史预警记录
        alert_service.alert_history = [
            {'alert_id': 'A001', 'timestamp': datetime.now() - timedelta(days=1), 'severity': 'warning'},
            {'alert_id': 'A002', 'timestamp': datetime.now() - timedelta(hours=12), 'severity': 'critical'},
            {'alert_id': 'A003', 'timestamp': datetime.now() - timedelta(hours=1), 'severity': 'warning'},
        ]

        # When: 查询历史
        result = alert_service.query_history(
            start_time=datetime.now() - timedelta(days=7),
            end_time=datetime.now()
        )

        # Then: 应返回历史记录
        assert 'alerts' in result
        assert len(result['alerts']) == 3

    @pytest.mark.unit
    def test_query_alert_history_by_severity(self, alert_service):
        """测试按严重级别查询预警历史"""
        # Given: 不同严重级别的预警
        alert_service.alert_history = [
            {'alert_id': 'A001', 'severity': 'warning'},
            {'alert_id': 'A002', 'severity': 'critical'},
            {'alert_id': 'A003', 'severity': 'warning'},
            {'alert_id': 'A004', 'severity': 'info'},
        ]

        # When: 按严重级别筛选
        result = alert_service.query_history(severity='critical')

        # Then: 应只返回对应级别
        assert len(result['alerts']) == 1
        assert result['alerts'][0]['severity'] == 'critical'

    @pytest.mark.unit
    def test_query_alert_history_pagination(self, alert_service):
        """测试预警历史分页"""
        # Given: 大量预警记录
        alert_service.alert_history = [
            {'alert_id': f'A{i:03d}', 'severity': 'warning'}
            for i in range(50)
        ]

        # When: 分页查询
        page1 = alert_service.query_history(page=1, page_size=10)
        page2 = alert_service.query_history(page=2, page_size=10)

        # Then: 应正确分页
        assert len(page1['alerts']) == 10
        assert len(page2['alerts']) == 10
        assert page1['alerts'][0]['alert_id'] != page2['alerts'][0]['alert_id']

    @pytest.mark.unit
    def test_alert_statistics(self, alert_service):
        """测试预警统计"""
        # Given: 预警历史
        alert_service.alert_history = [
            {'severity': 'critical', 'rule_id': 'R1'},
            {'severity': 'warning', 'rule_id': 'R1'},
            {'severity': 'warning', 'rule_id': 'R2'},
            {'severity': 'info', 'rule_id': 'R2'},
        ]

        # When: 获取统计
        stats = alert_service.get_statistics()

        # Then: 应返回统计数据
        assert stats['total'] == 4
        assert stats['by_severity']['critical'] == 1
        assert stats['by_severity']['warning'] == 2
        assert 'by_rule' in stats

    # ==================== BU-WN-007: 预警规则禁用/启用 ====================

    @pytest.mark.unit
    def test_disable_alert_rule(self, alert_service, sample_alert_rule):
        """测试禁用预警规则"""
        # Given: 已启用的规则
        alert_service.create_rule(sample_alert_rule)

        # When: 禁用规则
        result = alert_service.disable_rule(sample_alert_rule['rule_id'])

        # Then: 规则应被禁用
        assert result['success'] is True
        rule = alert_service.get_rule(sample_alert_rule['rule_id'])
        assert rule['enabled'] is False

    @pytest.mark.unit
    def test_enable_alert_rule(self, alert_service, sample_alert_rule):
        """测试启用预警规则"""
        # Given: 已禁用的规则
        sample_alert_rule['enabled'] = False
        alert_service.create_rule(sample_alert_rule)

        # When: 启用规则
        result = alert_service.enable_rule(sample_alert_rule['rule_id'])

        # Then: 规则应被启用
        assert result['success'] is True
        rule = alert_service.get_rule(sample_alert_rule['rule_id'])
        assert rule['enabled'] is True

    @pytest.mark.unit
    def test_disabled_rule_not_trigger(self, alert_service, sample_alert_rule, sample_metrics):
        """测试禁用规则不触发预警"""
        # Given: 禁用的规则
        sample_alert_rule['enabled'] = False
        alert_service.create_rule(sample_alert_rule)

        # When: 评估指标
        result = alert_service.evaluate_metrics(
            rule_id=sample_alert_rule['rule_id'],
            metrics=sample_metrics['values']
        )

        # Then: 不应触发
        assert result['triggered'] is False
        assert result.get('reason') == 'rule_disabled'

    @pytest.mark.unit
    def test_toggle_rule_status(self, alert_service, sample_alert_rule):
        """测试切换规则状态"""
        # Given: 规则
        alert_service.create_rule(sample_alert_rule)
        initial_state = alert_service.get_rule(sample_alert_rule['rule_id'])['enabled']

        # When: 切换状态
        alert_service.toggle_rule(sample_alert_rule['rule_id'])
        after_toggle = alert_service.get_rule(sample_alert_rule['rule_id'])['enabled']

        # Then: 状态应反转
        assert after_toggle != initial_state


class SmartAlertService:
    """智能预警服务"""

    def __init__(self):
        self.rules = {}
        self.alert_history = []
        self.last_triggered = {}
        self.notification_service = None

    def create_rule(self, config: Dict) -> Dict:
        """创建预警规则"""
        # 验证阈值
        if 'threshold' in config:
            if config['threshold'] < 0 and config.get('condition') == 'drop_percentage':
                raise ValueError("Threshold for drop_percentage must be positive")

        rule_id = config.get('rule_id', f"RULE-{len(self.rules) + 1:03d}")
        rule = {
            'rule_id': rule_id,
            'name': config.get('name'),
            'metric': config.get('metric'),
            'condition': config.get('condition'),
            'conditions': config.get('conditions', []),
            'threshold': config.get('threshold'),
            'severity': config.get('severity', 'warning'),
            'notification_channels': config.get('notification_channels', []),
            'enabled': config.get('enabled', True),
            'cooldown_minutes': config.get('cooldown_minutes', 0),
            'created_at': datetime.now()
        }
        self.rules[rule_id] = rule

        return {'success': True, 'rule_id': rule_id, 'rule': rule}

    def get_rule(self, rule_id: str) -> Dict:
        """获取规则"""
        return self.rules.get(rule_id)

    def evaluate_metrics(self, rule_id: str, metrics: List[Dict]) -> Dict:
        """评估指标"""
        rule = self.rules.get(rule_id)
        if not rule:
            return {'triggered': False, 'reason': 'rule_not_found'}

        if not rule['enabled']:
            return {'triggered': False, 'reason': 'rule_disabled'}

        # 检查冷却期
        if rule_id in self.last_triggered:
            cooldown = timedelta(minutes=rule.get('cooldown_minutes', 0))
            if datetime.now() - self.last_triggered[rule_id] < cooldown:
                return {'triggered': False, 'in_cooldown': True}

        # 评估条件
        if rule['condition'] == 'drop_percentage':
            if len(metrics) < 2:
                return {'triggered': False, 'reason': 'insufficient_data'}

            # 计算变化百分比
            first_value = metrics[0]['value']
            last_value = metrics[-1]['value']
            change_pct = ((first_value - last_value) / first_value) * 100

            if change_pct >= rule['threshold']:
                self.last_triggered[rule_id] = datetime.now()
                alert = {
                    'alert_id': f"ALERT-{len(self.alert_history) + 1:03d}",
                    'rule_id': rule_id,
                    'triggered': True,
                    'severity': rule['severity'],
                    'change': change_pct,
                    'timestamp': datetime.now()
                }
                self.alert_history.append(alert)
                return alert

        elif rule['condition'] == 'below_threshold':
            last_value = metrics[-1]['value']
            if last_value < rule['threshold']:
                self.last_triggered[rule_id] = datetime.now()
                return {
                    'triggered': True,
                    'severity': rule['severity'],
                    'value': last_value,
                    'threshold': rule['threshold']
                }

        return {'triggered': False}

    async def send_notification(self, alert: Dict, channel: str, recipient: str) -> Dict:
        """发送通知"""
        if not self.notification_service:
            return {'success': False, 'error': 'notification_service_not_configured'}

        try:
            if channel == 'email':
                await self.notification_service.send_email(recipient, alert)
            elif channel == 'sms':
                await self.notification_service.send_sms(recipient, alert)
            elif channel == 'in_app':
                await self.notification_service.send_in_app(recipient, alert)

            return {'success': True, 'channel': channel, 'recipient': recipient}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def send_to_all_channels(self, alert: Dict, channels: List[str],
                                    recipients: Dict[str, List[str]]) -> List[Dict]:
        """发送到所有渠道"""
        results = []
        for channel in channels:
            for recipient in recipients.get(channel, []):
                result = await self.send_notification(alert, channel, recipient)
                results.append(result)
        return results

    def query_history(self, start_time: datetime = None, end_time: datetime = None,
                      severity: str = None, page: int = 1, page_size: int = 20) -> Dict:
        """查询预警历史"""
        alerts = self.alert_history

        # 时间筛选
        if start_time:
            alerts = [a for a in alerts if a.get('timestamp', datetime.min) >= start_time]
        if end_time:
            alerts = [a for a in alerts if a.get('timestamp', datetime.max) <= end_time]

        # 严重级别筛选
        if severity:
            alerts = [a for a in alerts if a.get('severity') == severity]

        # 分页
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = alerts[start_idx:end_idx]

        return {
            'alerts': paginated,
            'total': len(alerts),
            'page': page,
            'page_size': page_size
        }

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        by_severity = {}
        by_rule = {}

        for alert in self.alert_history:
            severity = alert.get('severity', 'unknown')
            rule_id = alert.get('rule_id', 'unknown')

            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_rule[rule_id] = by_rule.get(rule_id, 0) + 1

        return {
            'total': len(self.alert_history),
            'by_severity': by_severity,
            'by_rule': by_rule
        }

    def disable_rule(self, rule_id: str) -> Dict:
        """禁用规则"""
        if rule_id in self.rules:
            self.rules[rule_id]['enabled'] = False
            return {'success': True}
        return {'success': False, 'error': 'rule_not_found'}

    def enable_rule(self, rule_id: str) -> Dict:
        """启用规则"""
        if rule_id in self.rules:
            self.rules[rule_id]['enabled'] = True
            return {'success': True}
        return {'success': False, 'error': 'rule_not_found'}

    def toggle_rule(self, rule_id: str) -> Dict:
        """切换规则状态"""
        if rule_id in self.rules:
            self.rules[rule_id]['enabled'] = not self.rules[rule_id]['enabled']
            return {'success': True, 'enabled': self.rules[rule_id]['enabled']}
        return {'success': False, 'error': 'rule_not_found'}
