"""
服务监控模块单元测试
覆盖用例: SA-MN-001 ~ SA-MN-007
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time


class TestServiceMonitoringService:
    """服务监控服务测试"""

    @pytest.fixture
    def sample_services(self):
        """示例服务列表"""
        return [
            {'name': 'alldata-api', 'url': 'http://localhost:5001', 'type': 'backend'},
            {'name': 'bisheng-api', 'url': 'http://localhost:5002', 'type': 'backend'},
            {'name': 'openai-proxy', 'url': 'http://localhost:8000', 'type': 'backend'},
            {'name': 'mysql', 'host': 'localhost', 'port': 3306, 'type': 'database'},
            {'name': 'milvus', 'host': 'localhost', 'port': 19530, 'type': 'vector_db'},
            {'name': 'minio', 'url': 'http://localhost:9000', 'type': 'storage'},
            {'name': 'redis', 'host': 'localhost', 'port': 6379, 'type': 'cache'},
        ]

    @pytest.fixture
    def sample_api_metrics(self):
        """示例 API 调用指标"""
        base_time = datetime.now()
        return {
            'endpoint': '/api/v1/query',
            'metrics': [
                {'timestamp': base_time - timedelta(minutes=5), 'count': 100, 'avg_latency': 120, 'error_rate': 0.02},
                {'timestamp': base_time - timedelta(minutes=4), 'count': 150, 'avg_latency': 135, 'error_rate': 0.01},
                {'timestamp': base_time - timedelta(minutes=3), 'count': 120, 'avg_latency': 110, 'error_rate': 0.03},
                {'timestamp': base_time - timedelta(minutes=2), 'count': 200, 'avg_latency': 150, 'error_rate': 0.02},
                {'timestamp': base_time - timedelta(minutes=1), 'count': 180, 'avg_latency': 140, 'error_rate': 0.01},
            ]
        }

    @pytest.fixture
    def sample_resource_metrics(self):
        """示例资源使用指标"""
        return {
            'cpu': {'usage_percent': 65, 'cores': 8},
            'memory': {'used_gb': 12, 'total_gb': 32, 'usage_percent': 37.5},
            'disk': {'used_gb': 200, 'total_gb': 500, 'usage_percent': 40},
            'network': {'rx_bytes': 1024000, 'tx_bytes': 512000}
        }

    @pytest.fixture
    def monitoring_service(self):
        """监控服务实例"""
        return ServiceMonitoringService()

    # ==================== SA-MN-001: 服务健康检查 ====================

    @pytest.mark.unit
    def test_health_check_all_services(self, monitoring_service, sample_services):
        """测试所有服务健康检查"""
        # Given: 服务列表
        monitoring_service.register_services(sample_services)

        # When: 执行健康检查
        with patch.object(monitoring_service, '_check_http_service', return_value={'healthy': True, 'latency': 50}):
            with patch.object(monitoring_service, '_check_database', return_value={'healthy': True, 'latency': 10}):
                result = monitoring_service.health_check_all()

        # Then: 应返回所有服务状态
        assert 'services' in result
        assert len(result['services']) == len(sample_services)
        assert 'overall_status' in result

    @pytest.mark.unit
    def test_health_check_single_service(self, monitoring_service, sample_services):
        """测试单个服务健康检查"""
        # Given: 服务配置
        service = sample_services[0]
        monitoring_service.register_services([service])

        # When: 检查单个服务
        with patch.object(monitoring_service, '_check_http_service', return_value={'healthy': True, 'latency': 50}):
            result = monitoring_service.health_check(service['name'])

        # Then: 应返回服务状态
        assert result['healthy'] is True
        assert 'latency' in result
        assert result['service_name'] == service['name']

    @pytest.mark.unit
    def test_health_check_unhealthy_service(self, monitoring_service, sample_services):
        """测试不健康服务检测"""
        # Given: 服务配置
        service = sample_services[0]
        monitoring_service.register_services([service])

        # When: 服务不可用
        with patch.object(monitoring_service, '_check_http_service',
                         return_value={'healthy': False, 'error': 'Connection refused'}):
            result = monitoring_service.health_check(service['name'])

        # Then: 应检测到不健康
        assert result['healthy'] is False
        assert 'error' in result

    @pytest.mark.unit
    def test_health_check_with_timeout(self, monitoring_service, sample_services):
        """测试健康检查超时"""
        # Given: 服务配置
        service = sample_services[0]
        monitoring_service.register_services([service])

        # When: 检查超时
        with patch.object(monitoring_service, '_check_http_service',
                         side_effect=TimeoutError("Request timeout")):
            result = monitoring_service.health_check(service['name'])

        # Then: 应标记为超时
        assert result['healthy'] is False
        assert 'timeout' in result.get('error', '').lower()

    # ==================== SA-MN-002: API调用监控 ====================

    @pytest.mark.unit
    def test_api_call_statistics(self, monitoring_service, sample_api_metrics):
        """测试 API 调用统计"""
        # Given: API 调用数据
        monitoring_service.record_api_metrics(sample_api_metrics)

        # When: 获取统计
        result = monitoring_service.get_api_statistics(
            endpoint=sample_api_metrics['endpoint'],
            time_range=timedelta(minutes=10)
        )

        # Then: 应返回统计数据
        assert 'total_calls' in result
        assert 'avg_latency' in result
        assert 'error_rate' in result
        assert result['total_calls'] == sum(m['count'] for m in sample_api_metrics['metrics'])

    @pytest.mark.unit
    def test_api_latency_percentiles(self, monitoring_service, sample_api_metrics):
        """测试 API 延迟百分位"""
        # Given: API 调用数据
        monitoring_service.record_api_metrics(sample_api_metrics)

        # When: 获取延迟百分位
        result = monitoring_service.get_latency_percentiles(
            endpoint=sample_api_metrics['endpoint']
        )

        # Then: 应返回百分位数据
        assert 'p50' in result
        assert 'p90' in result
        assert 'p99' in result

    @pytest.mark.unit
    def test_api_error_tracking(self, monitoring_service):
        """测试 API 错误追踪"""
        # Given: 包含错误的请求记录
        errors = [
            {'endpoint': '/api/v1/query', 'status': 500, 'error': 'Internal Server Error', 'timestamp': datetime.now()},
            {'endpoint': '/api/v1/query', 'status': 503, 'error': 'Service Unavailable', 'timestamp': datetime.now()},
            {'endpoint': '/api/v1/upload', 'status': 400, 'error': 'Bad Request', 'timestamp': datetime.now()},
        ]
        for error in errors:
            monitoring_service.record_error(error)

        # When: 查询错误统计
        result = monitoring_service.get_error_statistics()

        # Then: 应返回错误统计
        assert result['total_errors'] == 3
        assert 'by_endpoint' in result
        assert 'by_status' in result

    # ==================== SA-MN-003: 资源使用监控 ====================

    @pytest.mark.unit
    def test_cpu_usage_monitoring(self, monitoring_service, sample_resource_metrics):
        """测试 CPU 使用率监控"""
        # Given: 资源指标
        monitoring_service.record_resource_metrics(sample_resource_metrics)

        # When: 获取 CPU 使用率
        result = monitoring_service.get_cpu_usage()

        # Then: 应返回 CPU 指标
        assert 'usage_percent' in result
        assert 'cores' in result
        assert 0 <= result['usage_percent'] <= 100

    @pytest.mark.unit
    def test_memory_usage_monitoring(self, monitoring_service, sample_resource_metrics):
        """测试内存使用监控"""
        # Given: 资源指标
        monitoring_service.record_resource_metrics(sample_resource_metrics)

        # When: 获取内存使用
        result = monitoring_service.get_memory_usage()

        # Then: 应返回内存指标
        assert 'used_gb' in result
        assert 'total_gb' in result
        assert 'usage_percent' in result

    @pytest.mark.unit
    def test_disk_usage_monitoring(self, monitoring_service, sample_resource_metrics):
        """测试磁盘使用监控"""
        # Given: 资源指标
        monitoring_service.record_resource_metrics(sample_resource_metrics)

        # When: 获取磁盘使用
        result = monitoring_service.get_disk_usage()

        # Then: 应返回磁盘指标
        assert 'used_gb' in result
        assert 'total_gb' in result
        assert 'usage_percent' in result

    @pytest.mark.unit
    def test_resource_usage_history(self, monitoring_service):
        """测试资源使用历史"""
        # Given: 多个时间点的资源数据
        for i in range(5):
            monitoring_service.record_resource_metrics({
                'cpu': {'usage_percent': 60 + i * 5},
                'memory': {'usage_percent': 40 + i * 2},
                'timestamp': datetime.now() - timedelta(minutes=5-i)
            })

        # When: 获取历史数据
        result = monitoring_service.get_resource_history(time_range=timedelta(minutes=10))

        # Then: 应返回历史记录
        assert 'cpu_history' in result
        assert 'memory_history' in result
        assert len(result['cpu_history']) == 5

    # ==================== SA-MN-004: ETL任务监控 ====================

    @pytest.mark.unit
    def test_etl_task_status_monitoring(self, monitoring_service):
        """测试 ETL 任务状态监控"""
        # Given: ETL 任务列表
        tasks = [
            {'task_id': 'ETL-001', 'name': '用户数据清洗', 'status': 'running', 'progress': 60},
            {'task_id': 'ETL-002', 'name': '订单数据同步', 'status': 'completed', 'progress': 100},
            {'task_id': 'ETL-003', 'name': '日志归档', 'status': 'pending', 'progress': 0},
        ]
        monitoring_service.register_etl_tasks(tasks)

        # When: 查询任务状态
        result = monitoring_service.get_etl_task_status()

        # Then: 应返回所有任务状态
        assert len(result['tasks']) == 3
        assert result['summary']['running'] == 1
        assert result['summary']['completed'] == 1
        assert result['summary']['pending'] == 1

    @pytest.mark.unit
    def test_etl_task_progress_update(self, monitoring_service):
        """测试 ETL 任务进度更新"""
        # Given: 运行中的任务
        task = {'task_id': 'ETL-001', 'name': '数据清洗', 'status': 'running', 'progress': 30}
        monitoring_service.register_etl_tasks([task])

        # When: 更新进度
        monitoring_service.update_task_progress('ETL-001', 75)
        result = monitoring_service.get_task_status('ETL-001')

        # Then: 进度应更新
        assert result['progress'] == 75

    # ==================== SA-MN-005: 模型服务监控 ====================

    @pytest.mark.unit
    def test_model_service_qps_monitoring(self, monitoring_service):
        """测试模型服务 QPS 监控"""
        # Given: 模型服务调用记录
        calls = [
            {'model': 'gpt-4', 'timestamp': datetime.now() - timedelta(seconds=i), 'latency': 100 + i}
            for i in range(100)
        ]
        monitoring_service.record_model_calls(calls)

        # When: 获取 QPS
        result = monitoring_service.get_model_service_metrics('gpt-4')

        # Then: 应返回 QPS 和延迟指标
        assert 'qps' in result
        assert 'avg_latency' in result
        assert result['qps'] > 0

    @pytest.mark.unit
    def test_model_service_latency_monitoring(self, monitoring_service):
        """测试模型服务延迟监控"""
        # Given: 模型服务延迟记录
        latencies = [100, 150, 120, 200, 180, 300, 250]
        for lat in latencies:
            monitoring_service.record_model_call({
                'model': 'embedding-model',
                'latency': lat,
                'timestamp': datetime.now()
            })

        # When: 获取延迟统计
        result = monitoring_service.get_model_latency_stats('embedding-model')

        # Then: 应返回延迟统计
        assert 'avg' in result
        assert 'max' in result
        assert 'min' in result
        assert result['min'] == 100
        assert result['max'] == 300

    # ==================== SA-MN-006: 告警配置 ====================

    @pytest.mark.unit
    def test_create_system_alert_rule(self, monitoring_service):
        """测试创建系统告警规则"""
        # Given: 告警配置
        rule = {
            'name': 'CPU 高负载告警',
            'metric': 'cpu_usage',
            'condition': '>',
            'threshold': 80,
            'severity': 'warning',
            'notification': ['email']
        }

        # When: 创建规则
        result = monitoring_service.create_alert_rule(rule)

        # Then: 规则应创建成功
        assert result['success'] is True
        assert 'rule_id' in result

    @pytest.mark.unit
    def test_alert_rule_evaluation(self, monitoring_service, sample_resource_metrics):
        """测试告警规则评估"""
        # Given: 告警规则和高 CPU 使用率
        rule = {
            'name': 'CPU 告警',
            'metric': 'cpu_usage',
            'condition': '>',
            'threshold': 60,
            'severity': 'warning'
        }
        monitoring_service.create_alert_rule(rule)

        # 模拟高 CPU
        high_cpu_metrics = sample_resource_metrics.copy()
        high_cpu_metrics['cpu']['usage_percent'] = 85
        monitoring_service.record_resource_metrics(high_cpu_metrics)

        # When: 评估规则
        result = monitoring_service.evaluate_alert_rules()

        # Then: 应触发告警
        assert len(result['triggered_alerts']) > 0
        assert result['triggered_alerts'][0]['severity'] == 'warning'

    # ==================== SA-MN-007: 告警通知 ====================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_system_alert(self, monitoring_service):
        """测试发送系统告警"""
        # Given: 告警信息
        alert = {
            'alert_id': 'SYS-001',
            'title': 'CPU 使用率过高',
            'message': 'CPU 使用率达到 85%',
            'severity': 'warning',
            'timestamp': datetime.now()
        }

        # When: 发送告警
        with patch.object(monitoring_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {'success': True}
            result = await monitoring_service.send_alert(alert, channels=['email'])

        # Then: 告警应发送成功
        assert result['success'] is True
        mock_send.assert_called_once()

    @pytest.mark.unit
    def test_alert_history_query(self, monitoring_service):
        """测试告警历史查询"""
        # Given: 历史告警
        alerts = [
            {'alert_id': f'SYS-{i:03d}', 'severity': 'warning' if i % 2 == 0 else 'critical',
             'timestamp': datetime.now() - timedelta(hours=i)}
            for i in range(10)
        ]
        monitoring_service.alert_history = alerts

        # When: 查询历史
        result = monitoring_service.query_alert_history(severity='critical')

        # Then: 应返回筛选结果
        assert len(result) == 5  # 一半是 critical


class ServiceMonitoringService:
    """服务监控服务"""

    def __init__(self):
        self.services = {}
        self.api_metrics = {}
        self.resource_metrics = []
        self.errors = []
        self.etl_tasks = {}
        self.model_calls = []
        self.alert_rules = {}
        self.alert_history = []

    def register_services(self, services: List[Dict]):
        """注册服务"""
        for service in services:
            self.services[service['name']] = service

    def health_check_all(self) -> Dict:
        """检查所有服务健康状态"""
        results = []
        all_healthy = True

        for name, config in self.services.items():
            result = self.health_check(name)
            results.append(result)
            if not result['healthy']:
                all_healthy = False

        return {
            'services': results,
            'overall_status': 'healthy' if all_healthy else 'degraded',
            'timestamp': datetime.now().isoformat()
        }

    def health_check(self, service_name: str) -> Dict:
        """检查单个服务健康状态"""
        service = self.services.get(service_name)
        if not service:
            return {'healthy': False, 'error': 'Service not found', 'service_name': service_name}

        try:
            if service['type'] == 'backend':
                result = self._check_http_service(service)
            elif service['type'] == 'database':
                result = self._check_database(service)
            else:
                result = self._check_http_service(service)

            result['service_name'] = service_name
            return result
        except TimeoutError:
            return {'healthy': False, 'error': 'Timeout', 'service_name': service_name}
        except Exception as e:
            return {'healthy': False, 'error': str(e), 'service_name': service_name}

    def _check_http_service(self, service: Dict) -> Dict:
        """检查 HTTP 服务"""
        # 实际实现会使用 requests 库
        return {'healthy': True, 'latency': 50}

    def _check_database(self, service: Dict) -> Dict:
        """检查数据库"""
        # 实际实现会使用数据库连接
        return {'healthy': True, 'latency': 10}

    def record_api_metrics(self, metrics: Dict):
        """记录 API 指标"""
        endpoint = metrics['endpoint']
        if endpoint not in self.api_metrics:
            self.api_metrics[endpoint] = []
        self.api_metrics[endpoint].extend(metrics['metrics'])

    def get_api_statistics(self, endpoint: str, time_range: timedelta) -> Dict:
        """获取 API 统计"""
        metrics = self.api_metrics.get(endpoint, [])
        if not metrics:
            return {'total_calls': 0, 'avg_latency': 0, 'error_rate': 0}

        total_calls = sum(m['count'] for m in metrics)
        avg_latency = sum(m['avg_latency'] * m['count'] for m in metrics) / total_calls if total_calls > 0 else 0
        avg_error_rate = sum(m['error_rate'] * m['count'] for m in metrics) / total_calls if total_calls > 0 else 0

        return {
            'total_calls': total_calls,
            'avg_latency': avg_latency,
            'error_rate': avg_error_rate
        }

    def get_latency_percentiles(self, endpoint: str) -> Dict:
        """获取延迟百分位"""
        metrics = self.api_metrics.get(endpoint, [])
        latencies = [m['avg_latency'] for m in metrics]

        if not latencies:
            return {'p50': 0, 'p90': 0, 'p99': 0}

        import numpy as np
        return {
            'p50': float(np.percentile(latencies, 50)),
            'p90': float(np.percentile(latencies, 90)),
            'p99': float(np.percentile(latencies, 99))
        }

    def record_error(self, error: Dict):
        """记录错误"""
        self.errors.append(error)

    def get_error_statistics(self) -> Dict:
        """获取错误统计"""
        by_endpoint = {}
        by_status = {}

        for error in self.errors:
            endpoint = error.get('endpoint', 'unknown')
            status = error.get('status', 0)

            by_endpoint[endpoint] = by_endpoint.get(endpoint, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        return {
            'total_errors': len(self.errors),
            'by_endpoint': by_endpoint,
            'by_status': by_status
        }

    def record_resource_metrics(self, metrics: Dict):
        """记录资源指标"""
        metrics['timestamp'] = metrics.get('timestamp', datetime.now())
        self.resource_metrics.append(metrics)

    def get_cpu_usage(self) -> Dict:
        """获取 CPU 使用率"""
        if not self.resource_metrics:
            return {'usage_percent': 0, 'cores': 0}
        latest = self.resource_metrics[-1]
        return latest.get('cpu', {'usage_percent': 0, 'cores': 0})

    def get_memory_usage(self) -> Dict:
        """获取内存使用"""
        if not self.resource_metrics:
            return {'used_gb': 0, 'total_gb': 0, 'usage_percent': 0}
        latest = self.resource_metrics[-1]
        return latest.get('memory', {'used_gb': 0, 'total_gb': 0, 'usage_percent': 0})

    def get_disk_usage(self) -> Dict:
        """获取磁盘使用"""
        if not self.resource_metrics:
            return {'used_gb': 0, 'total_gb': 0, 'usage_percent': 0}
        latest = self.resource_metrics[-1]
        return latest.get('disk', {'used_gb': 0, 'total_gb': 0, 'usage_percent': 0})

    def get_resource_history(self, time_range: timedelta) -> Dict:
        """获取资源使用历史"""
        cutoff = datetime.now() - time_range
        filtered = [m for m in self.resource_metrics if m.get('timestamp', datetime.min) >= cutoff]

        return {
            'cpu_history': [m.get('cpu', {}).get('usage_percent', 0) for m in filtered],
            'memory_history': [m.get('memory', {}).get('usage_percent', 0) for m in filtered],
            'timestamps': [m.get('timestamp') for m in filtered]
        }

    def register_etl_tasks(self, tasks: List[Dict]):
        """注册 ETL 任务"""
        for task in tasks:
            self.etl_tasks[task['task_id']] = task

    def get_etl_task_status(self) -> Dict:
        """获取 ETL 任务状态"""
        summary = {'running': 0, 'completed': 0, 'pending': 0, 'failed': 0}
        for task in self.etl_tasks.values():
            status = task.get('status', 'unknown')
            if status in summary:
                summary[status] += 1

        return {
            'tasks': list(self.etl_tasks.values()),
            'summary': summary
        }

    def update_task_progress(self, task_id: str, progress: int):
        """更新任务进度"""
        if task_id in self.etl_tasks:
            self.etl_tasks[task_id]['progress'] = progress

    def get_task_status(self, task_id: str) -> Dict:
        """获取任务状态"""
        return self.etl_tasks.get(task_id, {})

    def record_model_calls(self, calls: List[Dict]):
        """记录模型调用"""
        self.model_calls.extend(calls)

    def record_model_call(self, call: Dict):
        """记录单次模型调用"""
        self.model_calls.append(call)

    def get_model_service_metrics(self, model: str) -> Dict:
        """获取模型服务指标"""
        model_calls = [c for c in self.model_calls if c.get('model') == model]
        if not model_calls:
            return {'qps': 0, 'avg_latency': 0}

        # 计算最近一分钟的 QPS
        recent = [c for c in model_calls if c['timestamp'] > datetime.now() - timedelta(minutes=1)]
        qps = len(recent) / 60

        avg_latency = sum(c['latency'] for c in model_calls) / len(model_calls)

        return {
            'qps': qps,
            'avg_latency': avg_latency,
            'total_calls': len(model_calls)
        }

    def get_model_latency_stats(self, model: str) -> Dict:
        """获取模型延迟统计"""
        latencies = [c['latency'] for c in self.model_calls if c.get('model') == model]
        if not latencies:
            return {'avg': 0, 'max': 0, 'min': 0}

        return {
            'avg': sum(latencies) / len(latencies),
            'max': max(latencies),
            'min': min(latencies)
        }

    def create_alert_rule(self, rule: Dict) -> Dict:
        """创建告警规则"""
        rule_id = f"RULE-{len(self.alert_rules) + 1:03d}"
        rule['rule_id'] = rule_id
        self.alert_rules[rule_id] = rule
        return {'success': True, 'rule_id': rule_id}

    def evaluate_alert_rules(self) -> Dict:
        """评估告警规则"""
        triggered = []

        for rule_id, rule in self.alert_rules.items():
            metric = rule['metric']
            threshold = rule['threshold']
            condition = rule['condition']

            # 获取当前值
            if metric == 'cpu_usage':
                current = self.get_cpu_usage().get('usage_percent', 0)
            elif metric == 'memory_usage':
                current = self.get_memory_usage().get('usage_percent', 0)
            else:
                continue

            # 评估条件
            triggered_flag = False
            if condition == '>' and current > threshold:
                triggered_flag = True
            elif condition == '<' and current < threshold:
                triggered_flag = True

            if triggered_flag:
                triggered.append({
                    'rule_id': rule_id,
                    'rule_name': rule['name'],
                    'severity': rule['severity'],
                    'current_value': current,
                    'threshold': threshold,
                    'timestamp': datetime.now()
                })

        return {'triggered_alerts': triggered}

    async def send_alert(self, alert: Dict, channels: List[str]) -> Dict:
        """发送告警"""
        for channel in channels:
            await self._send_notification(alert, channel)
        return {'success': True, 'alert_id': alert['alert_id']}

    async def _send_notification(self, alert: Dict, channel: str):
        """发送通知"""
        pass  # 实际实现

    def query_alert_history(self, severity: str = None) -> List[Dict]:
        """查询告警历史"""
        if severity:
            return [a for a in self.alert_history if a.get('severity') == severity]
        return self.alert_history
