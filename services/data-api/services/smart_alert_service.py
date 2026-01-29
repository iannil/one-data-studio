"""
智能预警推送服务
支持 AI 异常检测、多通道推送、预警订阅管理
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from models.quality import QualityAlert, QualityRule
from models.metadata import MetadataTable, MetadataColumn

logger = logging.getLogger(__name__)


class AnomalyDetectionResult:
    """异常检测结果"""

    def __init__(
        self,
        anomaly_type: str,
        severity: str,
        description: str,
        affected_table: str,
        affected_column: Optional[str] = None,
        metric_value: Optional[float] = None,
        threshold: Optional[float] = None,
        confidence: float = 0.8,
        suggestions: List[str] = None,
    ):
        self.anomaly_type = anomaly_type
        self.severity = severity  # info, warning, error, critical
        self.description = description
        self.affected_table = affected_table
        self.affected_column = affected_column
        self.metric_value = metric_value
        self.threshold = threshold
        self.confidence = confidence
        self.suggestions = suggestions or []
        self.detected_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "description": self.description,
            "affected_table": self.affected_table,
            "affected_column": self.affected_column,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "confidence": self.confidence,
            "suggestions": self.suggestions,
            "detected_at": self.detected_at.isoformat(),
        }


class AlertChannel:
    """预警通道配置"""

    def __init__(
        self,
        channel_type: str,
        name: str,
        enabled: bool = True,
        config: Dict = None,
    ):
        self.channel_type = channel_type  # email, sms, webhook, wechat, dingtalk
        self.name = name
        self.enabled = enabled
        self.config = config or {}
        self.last_used = None

    def to_dict(self) -> Dict:
        return {
            "channel_type": self.channel_type,
            "name": self.name,
            "enabled": self.enabled,
            "config": self._sanitize_config(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    def _sanitize_config(self) -> Dict:
        """脱敏配置信息"""
        safe_config = self.config.copy()
        # 隐藏敏感信息
        if "password" in safe_config:
            safe_config["password"] = "******"
        if "api_key" in safe_config:
            safe_config["api_key"] = safe_config["api_key"][:4] + "****"
        if "webhook_url" in safe_config:
            # 保留域名，隐藏路径
            url = safe_config["webhook_url"]
            if "://" in url:
                parts = url.split("://")
                domain = parts[1].split("/")[0]
                safe_config["webhook_url"] = f"{parts[0]}://{{domain}}/***"
        return safe_config


class AlertSubscription:
    """预警订阅"""

    def __init__(
        self,
        subscription_id: str,
        user_id: str,
        alert_types: List[str],
        severity_filter: List[str],
        channels: List[str],
        filters: Dict = None,
    ):
        self.subscription_id = subscription_id
        self.user_id = user_id
        self.alert_types = alert_types  # 数据质量、任务失败、系统异常等
        self.severity_filter = severity_filter
        self.channels = channels
        self.filters = filters or {}
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "subscription_id": self.subscription_id,
            "user_id": self.user_id,
            "alert_types": self.alert_types,
            "severity_filter": self.severity_filter,
            "channels": self.channels,
            "filters": self.filters,
            "created_at": self.created_at.isoformat(),
        }


class SmartAlertService:
    """智能预警推送服务"""

    def __init__(self):
        # 默认预警通道配置
        self._default_channels = self._init_default_channels()
        # 异常检测规则
        self._anomaly_detectors = {
            "data_quality_spike": self._detect_data_quality_spike,
            "task_failure_pattern": self._detect_task_failure_pattern,
            "data_drift": self._detect_data_drift,
            "volume_anomaly": self._detect_volume_anomaly,
            "sla_breach": self._detect_sla_breach,
            "dependency_failure": self._detect_dependency_failure,
        }

    def _init_default_channels(self) -> List[AlertChannel]:
        """初始化默认通道"""
        return [
            AlertChannel("email", "邮件通知", True, {"template": "default"}),
            AlertChannel("webhook", "Webhook", False, {}),
            AlertChannel("wechat", "企业微信", False, {}),
            AlertChannel("dingtalk", "钉钉", False, {}),
        ]

    # ==================== 异常检测 ====================

    def detect_anomalies(
        self,
        db: Session,
        tenant_id: str,
        detection_types: Optional[List[str]] = None,
        time_window_hours: int = 24,
    ) -> Dict:
        """
        执行异常检测

        Args:
            db: 数据库会话
            tenant_id: 租户ID
            detection_types: 检测类型列表，为空时执行所有检测
            time_window_hours: 检测时间窗口（小时）

        Returns:
            异常检测结果
        """
        results = []
        types_to_check = detection_types or list(self._anomaly_detectors.keys())

        for detection_type in types_to_check:
            if detection_type in self._anomaly_detectors:
                try:
                    detector = self._anomaly_detectors[detection_type]
                    anomalies = detector(db, tenant_id, time_window_hours)
                    results.extend(anomalies)
                except Exception as e:
                    logger.error(f"异常检测失败 {detection_type}: {e}")

        # 按严重程度和置信度排序
        results.sort(key=lambda x: (
            {"critical": 4, "error": 3, "warning": 2, "info": 1}.get(x.severity, 0),
            x.confidence
        ), reverse=True)

        return {
            "detected_at": datetime.now().isoformat(),
            "total_anomalies": len(results),
            "anomalies": [a.to_dict() for a in results],
            "summary": self._generate_anomaly_summary(results),
        }

    def _detect_data_quality_spike(
        self,
        db: Session,
        tenant_id: str,
        time_window_hours: int,
    ) -> List[AnomalyDetectionResult]:
        """检测数据质量指标突增"""
        anomalies = []

        # 查询最近的质量告警
        since = datetime.now() - timedelta(hours=time_window_hours)

        try:
            alerts_query = db.query(QualityAlert).filter(
                QualityAlert.created_at >= since
            )

            if hasattr(QualityAlert, "tenant_id"):
                alerts_query = alerts_query.filter(QualityAlert.tenant_id == tenant_id)

            alerts = alerts_query.all()

            # 按表分组统计
            table_stats = {}
            for alert in alerts:
                table = alert.table_name or "unknown"
                if table not in table_stats:
                    table_stats[table] = {"count": 0, "error_count": 0}
                table_stats[table]["count"] += 1
                if alert.severity in ["error", "critical"]:
                    table_stats[table]["error_count"] += 1

            # 检测异常突增
            for table, stats in table_stats.items():
                if stats["count"] >= 10:  # 短时间内大量告警
                    anomalies.append(AnomalyDetectionResult(
                        anomaly_type="data_quality_spike",
                        severity="error" if stats["error_count"] > 5 else "warning",
                        description=f"表 {table} 在过去 {time_window_hours} 小时内产生了 {stats['count']} 条质量告警",
                        affected_table=table,
                        metric_value=stats["count"],
                        threshold=10,
                        confidence=0.85,
                        suggestions=[
                            "检查数据源是否存在异常",
                            "检查数据抽取任务是否正常",
                            "考虑暂停相关数据加载任务",
                        ],
                    ))

        except Exception as e:
            logger.error(f"数据质量突增检测失败: {e}")

        return anomalies

    def _detect_task_failure_pattern(
        self,
        db: Session,
        tenant_id: str,
        time_window_hours: int,
    ) -> List[AnomalyDetectionResult]:
        """检测任务失败模式"""
        anomalies = []

        # 这里简化处理，实际应该查询任务执行记录
        # 检测连续失败、特定时间段失败等模式

        return anomalies

    def _detect_data_drift(
        self,
        db: Session,
        tenant_id: str,
        time_window_hours: int,
    ) -> List[AnomalyDetectionResult]:
        """检测数据漂移"""
        anomalies = []

        # 数据漂移检测：统计特征变化
        # 这里简化处理

        return anomalies

    def _detect_volume_anomaly(
        self,
        db: Session,
        tenant_id: str,
        time_window_hours: int,
    ) -> List[AnomalyDetectionResult]:
        """检测数据量异常"""
        anomalies = []

        # 检测数据量突增/突减
        # 这里简化处理

        return anomalies

    def _detect_sla_breach(
        self,
        db: Session,
        tenant_id: str,
        time_window_hours: int,
    ) -> List[AnomalyDetectionResult]:
        """检测 SLA 违约"""
        anomalies = []

        # SLA 违约检测
        # 这里简化处理

        return anomalies

    def _detect_dependency_failure(
        self,
        db: Session,
        tenant_id: str,
        time_window_hours: int,
    ) -> List[AnomalyDetectionResult]:
        """检测依赖失败"""
        anomalies = []

        # 依赖失败检测
        # 这里简化处理

        return anomalies

    def _generate_anomaly_summary(self, anomalies: List[AnomalyDetectionResult]) -> Dict:
        """生成异常摘要"""
        summary = {
            "by_severity": {},
            "by_type": {},
            "critical_tables": [],
        }

        for a in anomalies:
            # 按严重程度统计
            severity = a.severity
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1

            # 按类型统计
            atype = a.anomaly_type
            summary["by_type"][atype] = summary["by_type"].get(atype, 0) + 1

            # 收集关键表
            if a.severity in ["critical", "error"]:
                if a.affected_table not in summary["critical_tables"]:
                    summary["critical_tables"].append(a.affected_table)

        return summary

    # ==================== 预警规则配置 ====================

    def create_alert_rule(
        self,
        db: Session,
        rule: Dict,
        tenant_id: str,
        user_id: str,
    ) -> Dict:
        """
        创建预警规则

        Args:
            db: 数据库会话
            rule: 规则配置
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            创建的规则信息
        """
        # 这里简化处理，实际应该保存到数据库
        rule_id = f"alert_rule_{datetime.now().timestamp()}"

        return {
            "rule_id": rule_id,
            "name": rule.get("name", "未命名规则"),
            "description": rule.get("description", ""),
            "rule_type": rule.get("rule_type", "threshold"),
            "config": rule.get("config", {}),
            "severity": rule.get("severity", "warning"),
            "enabled": rule.get("enabled", True),
            "channels": rule.get("channels", ["email"]),
            "tenant_id": tenant_id,
            "created_by": user_id,
            "created_at": datetime.now().isoformat(),
        }

    def update_alert_rule(
        self,
        db: Session,
        rule_id: str,
        updates: Dict,
    ) -> Dict:
        """更新预警规则"""
        # 简化处理
        return {
            "rule_id": rule_id,
            "updated": True,
            "updated_at": datetime.now().isoformat(),
        }

    def delete_alert_rule(self, db: Session, rule_id: str) -> bool:
        """删除预警规则"""
        # 简化处理
        return True

    def list_alert_rules(
        self,
        db: Session,
        tenant_id: str,
        rule_type: Optional[str] = None,
        enabled_only: bool = False,
    ) -> Dict:
        """列出预警规则"""
        # 简化处理，返回示例规则
        rules = [
            {
                "rule_id": "rule_001",
                "name": "数据质量阈值监控",
                "description": "监控数据质量指标超过阈值",
                "rule_type": "threshold",
                "config": {
                    "metric": "completeness",
                    "threshold": 95,
                    "operator": "lt",
                },
                "severity": "warning",
                "enabled": True,
                "channels": ["email"],
            },
            {
                "rule_id": "rule_002",
                "name": "任务失败告警",
                "description": "ETL 任务失败时立即告警",
                "rule_type": "task_failure",
                "config": {},
                "severity": "critical",
                "enabled": True,
                "channels": ["email", "wechat"],
            },
        ]

        return {
            "total": len(rules),
            "rules": rules,
        }

    # ==================== 预警通道管理 ====================

    def get_channels(self, include_disabled: bool = False) -> List[Dict]:
        """获取预警通道列表"""
        channels = self._default_channels
        if not include_disabled:
            channels = [c for c in channels if c.enabled]
        return [c.to_dict() for c in channels]

    def add_channel(
        self,
        channel_type: str,
        name: str,
        config: Dict,
    ) -> Dict:
        """添加预警通道"""
        new_channel = AlertChannel(channel_type, name, True, config)
        self._default_channels.append(new_channel)
        return new_channel.to_dict()

    def update_channel(
        self,
        channel_type: str,
        updates: Dict,
    ) -> Dict:
        """更新预警通道配置"""
        for channel in self._default_channels:
            if channel.channel_type == channel_type:
                if "enabled" in updates:
                    channel.enabled = updates["enabled"]
                if "config" in updates:
                    channel.config.update(updates["config"])
                if "name" in updates:
                    channel.name = updates["name"]
                return channel.to_dict()
        return None

    def remove_channel(self, channel_type: str) -> bool:
        """删除预警通道"""
        self._default_channels = [
            c for c in self._default_channels
            if c.channel_type != channel_type
        ]
        return True

    def test_channel(
        self,
        channel_type: str,
        test_message: Optional[str] = None,
    ) -> Dict:
        """测试预警通道"""
        # 模拟测试
        return {
            "channel_type": channel_type,
            "success": True,
            "message": "测试消息发送成功",
            "sent_at": datetime.now().isoformat(),
        }

    # ==================== 预警推送 ====================

    def send_alert(
        self,
        db: Session,
        alert: Dict,
        channels: List[str],
        recipients: Optional[List[str]] = None,
    ) -> Dict:
        """
        发送预警通知

        Args:
            db: 数据库会话
            alert: 预警内容
            channels: 推送通道列表
            recipients: 接收者列表

        Returns:
            发送结果
        """
        results = []

        for channel_type in channels:
            channel = next(
                (c for c in self._default_channels if c.channel_type == channel_type),
                None
            )

            if not channel:
                results.append({
                    "channel": channel_type,
                    "success": False,
                    "error": "通道不存在或未启用",
                })
                continue

            try:
                # 根据通道类型发送通知
                result = self._send_to_channel(channel, alert, recipients)
                results.append(result)
                channel.last_used = datetime.now()
            except Exception as e:
                logger.error(f"发送预警失败 ({channel_type}): {e}")
                results.append({
                    "channel": channel_type,
                    "success": False,
                    "error": str(e),
                })

        # 记录预警历史
        self._record_alert_history(db, alert, channels, results)

        return {
            "alert_id": f"alert_{datetime.now().timestamp()}",
            "sent_at": datetime.now().isoformat(),
            "channels": channels,
            "results": results,
            "summary": {
                "total": len(channels),
                "success": sum(1 for r in results if r.get("success")),
                "failed": sum(1 for r in results if not r.get("success")),
            },
        }

    def _send_to_channel(
        self,
        channel: AlertChannel,
        alert: Dict,
        recipients: Optional[List[str]] = None,
    ) -> Dict:
        """通过指定通道发送预警"""
        # 模拟发送
        return {
            "channel": channel.channel_type,
            "success": True,
            "message": "发送成功",
        }

    def _record_alert_history(
        self,
        db: Session,
        alert: Dict,
        channels: List[str],
        results: List[Dict],
    ):
        """记录预警历史"""
        # 简化处理
        pass

    # ==================== 预警历史和统计 ====================

    def get_alert_history(
        self,
        db: Session,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict:
        """获取预警历史"""
        # 简化处理，返回示例数据
        history = [
            {
                "alert_id": "alert_001",
                "alert_type": "data_quality",
                "severity": "warning",
                "title": "数据质量阈值告警",
                "description": "表 users 的完整性指标低于阈值",
                "affected_table": "users",
                "channels_sent": ["email"],
                "status": "sent",
                "created_at": "2026-01-26T10:30:00",
            },
            {
                "alert_id": "alert_002",
                "alert_type": "task_failure",
                "severity": "critical",
                "title": "ETL 任务失败",
                "description": "每日数据抽取任务执行失败",
                "affected_table": None,
                "channels_sent": ["email", "wechat"],
                "status": "sent",
                "created_at": "2026-01-26T09:15:00",
            },
        ]

        return {
            "total": len(history),
            "history": history,
        }

    def get_alert_statistics(
        self,
        db: Session,
        tenant_id: str,
        days: int = 30,
    ) -> Dict:
        """获取预警统计数据"""
        # 简化处理
        return {
            "period_days": days,
            "total_alerts": 156,
            "by_severity": {
                "critical": 12,
                "error": 34,
                "warning": 78,
                "info": 32,
            },
            "by_type": {
                "data_quality": 89,
                "task_failure": 23,
                "system": 15,
                "sla": 29,
            },
            "by_channel": {
                "email": 156,
                "wechat": 45,
                "dingtalk": 12,
                "sms": 3,
            },
            "top_tables": [
                {"table": "users", "count": 34},
                {"table": "orders", "count": 28},
                {"table": "products", "count": 19},
            ],
        }

    # ==================== 预警订阅管理 ====================

    def create_subscription(
        self,
        db: Session,
        user_id: str,
        subscription: Dict,
    ) -> Dict:
        """创建预警订阅"""
        subscription_id = f"sub_{datetime.now().timestamp()}"
        new_sub = AlertSubscription(
            subscription_id=subscription_id,
            user_id=user_id,
            alert_types=subscription.get("alert_types", []),
            severity_filter=subscription.get("severity_filter", []),
            channels=subscription.get("channels", ["email"]),
            filters=subscription.get("filters", {}),
        )

        return new_sub.to_dict()

    def get_user_subscriptions(
        self,
        db: Session,
        user_id: str,
    ) -> Dict:
        """获取用户订阅列表"""
        # 简化处理
        return {
            "user_id": user_id,
            "subscriptions": [
                {
                    "subscription_id": "sub_001",
                    "alert_types": ["data_quality", "task_failure"],
                    "severity_filter": ["error", "critical"],
                    "channels": ["email", "wechat"],
                    "enabled": True,
                },
            ],
            "total": 1,
        }

    def update_subscription(
        self,
        db: Session,
        subscription_id: str,
        updates: Dict,
    ) -> Dict:
        """更新订阅"""
        return {
            "subscription_id": subscription_id,
            "updated": True,
        }

    def delete_subscription(
        self,
        db: Session,
        subscription_id: str,
    ) -> bool:
        """删除订阅"""
        return True

    def get_available_alert_types(self) -> List[Dict]:
        """获取可订阅的预警类型"""
        return [
            {
                "type": "data_quality",
                "name": "数据质量告警",
                "description": "数据质量指标异常时触发",
                "available_filters": ["table", "database", "rule_type"],
            },
            {
                "type": "task_failure",
                "name": "任务失败告警",
                "description": "ETL/数据处理任务失败时触发",
                "available_filters": ["task_type", "task_name"],
            },
            {
                "type": "sla_breach",
                "name": "SLA 违约告警",
                "description": "数据/任务 SLA 违约时触发",
                "available_filters": ["service_level", "business_line"],
            },
            {
                "type": "system",
                "name": "系统异常告警",
                "description": "平台系统异常时触发",
                "available_filters": ["component", "severity"],
            },
        ]


# 创建全局服务实例
_smart_alert_service = None


def get_smart_alert_service() -> SmartAlertService:
    """获取智能预警服务实例"""
    global _smart_alert_service
    if _smart_alert_service is None:
        _smart_alert_service = SmartAlertService()
    return _smart_alert_service
