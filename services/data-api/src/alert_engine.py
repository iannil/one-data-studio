"""
智能预警引擎
P6.2: 智能预警推送

支持三种检测类型:
- threshold: 阈值检测（大于、小于、等于）
- change_rate: 变化率检测（环比、同比）
- anomaly: 异常检测（Z-Score、孤立森林）
"""

import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class ConditionType(str, Enum):
    """条件类型枚举"""
    THRESHOLD = "threshold"
    CHANGE_RATE = "change_rate"
    ANOMALY = "anomaly"


class Operator(str, Enum):
    """比较运算符枚举"""
    GT = "gt"      # 大于
    GTE = "gte"    # 大于等于
    LT = "lt"      # 小于
    LTE = "lte"    # 小于等于
    EQ = "eq"      # 等于
    NEQ = "neq"    # 不等于


@dataclass
class AlertResult:
    """告警检测结果"""
    should_alert: bool
    current_value: float
    threshold_value: Optional[float] = None
    change_rate: Optional[float] = None
    anomaly_score: Optional[float] = None
    message: str = ""


def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class AlertEngine:
    """智能预警引擎"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def check_metric_rule(self, rule, current_value: float = None) -> AlertResult:
        """
        检测指标规则

        Args:
            rule: MetricAlertRule 实例
            current_value: 当前指标值（可选，不提供则从数据库获取最新值）

        Returns:
            AlertResult: 检测结果
        """
        from models.data_monitoring import MetricValue

        # 获取当前指标值
        if current_value is None:
            latest = self.db.query(MetricValue).filter(
                MetricValue.metric_id == rule.metric_id
            ).order_by(MetricValue.timestamp.desc()).first()

            if not latest:
                return AlertResult(
                    should_alert=False,
                    current_value=0,
                    message="无法获取指标值"
                )
            current_value = latest.value

        # 根据条件类型执行检测
        condition_type = rule.condition_type
        config = rule.condition_config or {}

        if condition_type == ConditionType.THRESHOLD:
            return self._check_threshold(current_value, config)
        elif condition_type == ConditionType.CHANGE_RATE:
            return self._check_change_rate(rule.metric_id, current_value, config)
        elif condition_type == ConditionType.ANOMALY:
            return self._check_anomaly(rule.metric_id, current_value, config)
        else:
            return AlertResult(
                should_alert=False,
                current_value=current_value,
                message=f"未知的条件类型: {condition_type}"
            )

    def _check_threshold(self, current_value: float, config: dict) -> AlertResult:
        """
        阈值检测

        config: {
            "operator": "gt|lt|eq|gte|lte|neq",
            "value": 100
        }
        """
        operator = config.get("operator", "gt")
        threshold = config.get("value", 0)

        should_alert = False
        if operator == Operator.GT:
            should_alert = current_value > threshold
        elif operator == Operator.GTE:
            should_alert = current_value >= threshold
        elif operator == Operator.LT:
            should_alert = current_value < threshold
        elif operator == Operator.LTE:
            should_alert = current_value <= threshold
        elif operator == Operator.EQ:
            should_alert = current_value == threshold
        elif operator == Operator.NEQ:
            should_alert = current_value != threshold

        operator_text = {
            "gt": "大于", "gte": "大于等于", "lt": "小于",
            "lte": "小于等于", "eq": "等于", "neq": "不等于"
        }

        return AlertResult(
            should_alert=should_alert,
            current_value=current_value,
            threshold_value=threshold,
            message=f"当前值 {current_value} {operator_text.get(operator, operator)} 阈值 {threshold}"
        )

    def _check_change_rate(self, metric_id: str, current_value: float, config: dict) -> AlertResult:
        """
        变化率检测

        config: {
            "period": "1h|6h|24h|7d",
            "operator": "gt|lt",
            "value": 0.2  # 20%
        }
        """
        from models.data_monitoring import MetricValue

        period = config.get("period", "1h")
        operator = config.get("operator", "gt")
        threshold_rate = config.get("value", 0.1)

        # 解析时间周期
        period_delta = self._parse_period(period)
        compare_time = datetime.utcnow() - period_delta

        # 获取对比时间点的值
        historical = self.db.query(MetricValue).filter(
            MetricValue.metric_id == metric_id,
            MetricValue.timestamp <= compare_time
        ).order_by(MetricValue.timestamp.desc()).first()

        if not historical or historical.value == 0:
            return AlertResult(
                should_alert=False,
                current_value=current_value,
                message=f"无法获取 {period} 前的历史数据"
            )

        # 计算变化率
        change_rate = (current_value - historical.value) / abs(historical.value)

        should_alert = False
        if operator == Operator.GT:
            should_alert = abs(change_rate) > threshold_rate
        elif operator == Operator.LT:
            should_alert = abs(change_rate) < threshold_rate

        return AlertResult(
            should_alert=should_alert,
            current_value=current_value,
            threshold_value=historical.value,
            change_rate=change_rate,
            message=f"变化率 {change_rate:.2%}，阈值 {threshold_rate:.2%}"
        )

    def _check_anomaly(self, metric_id: str, current_value: float, config: dict) -> AlertResult:
        """
        异常检测

        config: {
            "algorithm": "zscore|isolation_forest",
            "sensitivity": 0.95,
            "window": "24h"
        }
        """
        from models.data_monitoring import MetricValue

        algorithm = config.get("algorithm", "zscore")
        sensitivity = config.get("sensitivity", 0.95)
        window = config.get("window", "24h")

        window_delta = self._parse_period(window)
        start_time = datetime.utcnow() - window_delta

        # 获取历史数据
        historical_values = self.db.query(MetricValue.value).filter(
            MetricValue.metric_id == metric_id,
            MetricValue.timestamp >= start_time
        ).all()

        values = [v[0] for v in historical_values]

        if len(values) < 10:
            return AlertResult(
                should_alert=False,
                current_value=current_value,
                message="历史数据不足，无法进行异常检测"
            )

        if algorithm == "zscore":
            return self._zscore_detection(current_value, values, sensitivity)
        elif algorithm == "isolation_forest":
            return self._isolation_forest_detection(current_value, values, sensitivity)
        else:
            return AlertResult(
                should_alert=False,
                current_value=current_value,
                message=f"未知的异常检测算法: {algorithm}"
            )

    def _zscore_detection(self, current_value: float, historical_values: List[float],
                          sensitivity: float) -> AlertResult:
        """Z-Score 异常检测"""
        mean = np.mean(historical_values)
        std = np.std(historical_values)

        if std == 0:
            return AlertResult(
                should_alert=False,
                current_value=current_value,
                message="标准差为0，无法计算Z-Score"
            )

        z_score = abs((current_value - mean) / std)

        # sensitivity 转换为 Z-Score 阈值
        # 0.95 -> ~2.0, 0.99 -> ~2.58
        from scipy import stats
        z_threshold = stats.norm.ppf((1 + sensitivity) / 2)

        should_alert = z_score > z_threshold

        return AlertResult(
            should_alert=should_alert,
            current_value=current_value,
            anomaly_score=z_score,
            message=f"Z-Score: {z_score:.2f}，阈值: {z_threshold:.2f}"
        )

    def _isolation_forest_detection(self, current_value: float, historical_values: List[float],
                                     sensitivity: float) -> AlertResult:
        """孤立森林异常检测"""
        try:
            from sklearn.ensemble import IsolationForest

            # 准备数据
            X = np.array(historical_values + [current_value]).reshape(-1, 1)

            # 训练模型
            contamination = 1 - sensitivity
            clf = IsolationForest(contamination=contamination, random_state=42)
            clf.fit(X[:-1])  # 用历史数据训练

            # 预测当前值
            prediction = clf.predict([[current_value]])[0]
            anomaly_score = -clf.score_samples([[current_value]])[0]

            should_alert = prediction == -1

            return AlertResult(
                should_alert=should_alert,
                current_value=current_value,
                anomaly_score=anomaly_score,
                message=f"孤立森林异常分数: {anomaly_score:.4f}"
            )
        except ImportError:
            logger.warning("sklearn not installed, falling back to zscore")
            return self._zscore_detection(current_value, historical_values, sensitivity)

    def _parse_period(self, period: str) -> timedelta:
        """解析时间周期字符串"""
        unit = period[-1].lower()
        try:
            value = int(period[:-1])
        except ValueError:
            value = 1

        if unit == 'h':
            return timedelta(hours=value)
        elif unit == 'd':
            return timedelta(days=value)
        elif unit == 'm':
            return timedelta(minutes=value)
        elif unit == 'w':
            return timedelta(weeks=value)
        else:
            return timedelta(hours=1)

    def trigger_alert(self, rule, result: AlertResult, notify: bool = True) -> Optional[str]:
        """
        触发告警

        Args:
            rule: MetricAlertRule 实例
            result: AlertResult 检测结果
            notify: 是否发送通知

        Returns:
            alert_id: 告警ID
        """
        from models.data_monitoring import DataAlert, AlertHistory

        # 检查冷却期
        if not rule.can_trigger():
            logger.info(f"规则 {rule.rule_id} 在冷却期内，跳过告警")
            return None

        # 渲染告警内容
        context = {
            "metric_id": rule.metric_id,
            "metric_name": rule.metric_name or rule.metric_id,
            "current_value": result.current_value,
            "threshold_value": result.threshold_value,
            "change_rate": f"{result.change_rate:.2%}" if result.change_rate else None,
            "anomaly_score": result.anomaly_score,
            "condition_type": rule.condition_type,
            "severity": rule.severity,
            "triggered_at": datetime.utcnow().isoformat(),
        }
        title, message = rule.render_alert(context)

        # 创建告警记录
        alert = DataAlert(
            alert_id=generate_id("alert_"),
            rule_id=rule.rule_id,
            rule_name=rule.name,
            title=title,
            message=message,
            severity=rule.severity,
            target_type=rule.metric_type,
            target_id=rule.metric_id,
            target_name=rule.metric_name,
            current_value=result.current_value,
            threshold_value=result.threshold_value,
            status="active",
            triggered_at=datetime.utcnow()
        )
        self.db.add(alert)

        # 记录告警历史
        history = AlertHistory(
            history_id=generate_id("hist_"),
            alert_id=alert.alert_id,
            rule_id=rule.rule_id,
            previous_status=None,
            new_status="active",
            action="triggered",
            action_by="system",
            alert_snapshot=alert.to_dict()
        )
        self.db.add(history)

        # 更新规则状态
        rule.last_triggered_at = datetime.utcnow()
        rule.trigger_count = (rule.trigger_count or 0) + 1

        self.db.commit()

        logger.info(f"告警已触发: {alert.alert_id}, 规则: {rule.name}")

        # 发送通知
        if notify and rule.notification_channels:
            self._send_notifications(rule, alert, title, message)

        return alert.alert_id

    def _send_notifications(self, rule, alert, title: str, message: str):
        """发送告警通知"""
        try:
            import sys
            sys.path.insert(0, '/app/shared')
            from notification_service import get_notification_service

            service = get_notification_service()
            channels = rule.notification_channels or []
            targets = rule.notification_targets or []

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                for channel in channels:
                    for target in targets:
                        result = loop.run_until_complete(
                            service.send(channel, target, title, message, {
                                "alert_id": alert.alert_id,
                                "severity": alert.severity,
                                "rule_id": rule.rule_id
                            })
                        )
                        if result.success:
                            logger.info(f"通知发送成功: {channel} -> {target}")
                        else:
                            logger.warning(f"通知发送失败: {channel} -> {target}: {result.error}")
            finally:
                loop.close()

        except ImportError:
            logger.warning("通知服务不可用，跳过通知发送")
        except Exception as e:
            logger.error(f"发送通知时发生错误: {e}")

    def acknowledge_alert(self, alert_id: str, user_id: str, note: str = None) -> bool:
        """确认告警"""
        from models.data_monitoring import DataAlert, AlertHistory

        alert = self.db.query(DataAlert).filter(DataAlert.alert_id == alert_id).first()
        if not alert:
            return False

        old_status = alert.status
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user_id

        # 记录历史
        history = AlertHistory(
            history_id=generate_id("hist_"),
            alert_id=alert.alert_id,
            rule_id=alert.rule_id,
            previous_status=old_status,
            new_status="acknowledged",
            action="acknowledged",
            action_by=user_id,
            action_note=note,
            alert_snapshot=alert.to_dict()
        )
        self.db.add(history)
        self.db.commit()

        logger.info(f"告警已确认: {alert_id} by {user_id}")
        return True

    def resolve_alert(self, alert_id: str, user_id: str, note: str = None) -> bool:
        """解决告警"""
        from models.data_monitoring import DataAlert, AlertHistory

        alert = self.db.query(DataAlert).filter(DataAlert.alert_id == alert_id).first()
        if not alert:
            return False

        old_status = alert.status
        alert.status = "resolved"
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = user_id

        # 记录历史
        history = AlertHistory(
            history_id=generate_id("hist_"),
            alert_id=alert.alert_id,
            rule_id=alert.rule_id,
            previous_status=old_status,
            new_status="resolved",
            action="resolved",
            action_by=user_id,
            action_note=note,
            alert_snapshot=alert.to_dict()
        )
        self.db.add(history)
        self.db.commit()

        logger.info(f"告警已解决: {alert_id} by {user_id}")
        return True

    def check_all_enabled_rules(self) -> List[str]:
        """
        检查所有启用的规则（用于定时任务）

        Returns:
            List of triggered alert IDs
        """
        from models.data_monitoring import MetricAlertRule

        rules = self.db.query(MetricAlertRule).filter(
            MetricAlertRule.is_enabled == True
        ).all()

        triggered_alerts = []

        for rule in rules:
            try:
                result = self.check_metric_rule(rule)
                if result.should_alert and rule.can_trigger():
                    alert_id = self.trigger_alert(rule, result)
                    if alert_id:
                        triggered_alerts.append(alert_id)
            except Exception as e:
                logger.error(f"检查规则 {rule.rule_id} 时发生错误: {e}")

        return triggered_alerts


def get_alert_engine(db_session: Session) -> AlertEngine:
    """获取告警引擎实例"""
    return AlertEngine(db_session)
