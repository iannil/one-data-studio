"""
异常检测服务
检测用户行为异常并生成告警
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models.user_behavior import UserBehavior, BehaviorRule
from models.user_profile import BehaviorAnomaly

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """异常检测器"""

    def __init__(self):
        pass

    def detect_login_anomalies(
        self,
        db: Session,
        tenant_id: str,
        hours: int = 24
    ) -> List[BehaviorAnomaly]:
        """
        检测登录异常

        检测项:
        1. 异地登录（IP地址变化超过阈值）
        2. 高频登录（短时间内多次登录）
        3. 非常时段登录（深夜/凌晨）
        """
        anomalies = []
        since = datetime.now() - timedelta(hours=hours)

        # 获取用户登录行为
        login_behaviors = db.query(UserBehavior).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.behavior_type == "login",
            UserBehavior.occurred_at >= since
        ).all()

        # 按用户分组
        user_logins = {}
        for behavior in login_behaviors:
            if behavior.user_id not in user_logins:
                user_logins[behavior.user_id] = []
            user_logins[behavior.user_id].append(behavior)

        # 检测异常
        for user_id, logins in user_logins.items():
            # 检测高频登录
            if len(logins) > 20:  # 24小时内超过20次登录
                anomalies.append(self._create_anomaly({
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "anomaly_type": "high_frequency_login",
                    "severity": "medium",
                    "description": f"24小时内登录{len(logins)}次",
                    "behavior_data": {"login_count": len(logins)},
                    "detected_at": datetime.now(),
                }, db))

            # 检测非常时段登录（0-6点）
            night_logins = [l for l in logins if l.occurred_at.hour < 6]
            if len(night_logins) > 3:
                anomalies.append(self._create_anomaly({
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "anomaly_type": "unusual_time_login",
                    "severity": "low",
                    "description": f"深夜时段(0-6点)登录{len(night_logins)}次",
                    "behavior_data": {"night_login_count": len(night_logins)},
                    "detected_at": datetime.now(),
                }, db))

            # 检测异地登录
            ips = set(l.ip_address for l in logins if l.ip_address)
            if len(ips) > 3:  # 从超过3个不同IP登录
                anomalies.append(self._create_anomaly({
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "anomaly_type": "multi_location_login",
                    "severity": "high",
                    "description": f"从{len(ips)}个不同IP地址登录",
                    "behavior_data": {"ip_addresses": list(ips)},
                    "detected_at": datetime.now(),
                }, db))

        return anomalies

    def detect_permission_anomalies(
        self,
        db: Session,
        tenant_id: str,
        hours: int = 24
    ) -> List[BehaviorAnomaly]:
        """
        检测权限异常

        检测项:
        1. 访问未授权页面
        2. 敏感操作频繁
        3. 越权访问尝试
        """
        anomalies = []
        since = datetime.now() - timedelta(hours=hours)

        # 获取被拒绝的访问行为
        denied_behaviors = db.query(UserBehavior).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.metadata.isnot(None),
            UserBehavior.occurred_at >= since
        ).all()

        for behavior in denied_behaviors:
            metadata = behavior.metadata or {}
            if metadata.get("status_code") == 403 or metadata.get("access_denied"):
                anomalies.append(self._create_anomaly({
                    "tenant_id": tenant_id,
                    "user_id": behavior.user_id,
                    "anomaly_type": "access_denied",
                    "severity": "high",
                    "description": f"尝试访问未授权资源: {behavior.action}",
                    "behavior_data": {
                        "action": behavior.action,
                        "page_url": behavior.page_url,
                    },
                    "detected_at": datetime.now(),
                }, db))

        return anomalies

    def detect_behavior_anomalies(
        self,
        db: Session,
        tenant_id: str,
        hours: int = 1
    ) -> List[BehaviorAnomaly]:
        """
        检测行为模式异常

        检测项:
        1. 高频操作（短时间内大量操作）
        2. 自动化行为（操作间隔过于规律）
        3. 数据大量导出
        """
        anomalies = []
        since = datetime.now() - timedelta(hours=hours)

        # 获取所有用户
        active_users = db.query(UserBehavior.user_id).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.occurred_at >= since
        ).distinct().all()

        for (user_id,) in active_users:
            # 检测高频操作
            user_behaviors = db.query(UserBehavior).filter(
                UserBehavior.tenant_id == tenant_id,
                UserBehavior.user_id == user_id,
                UserBehavior.occurred_at >= since
            ).all()

            if len(user_behaviors) > 1000:  # 1小时内超过1000次操作
                anomalies.append(self._create_anomaly({
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "anomaly_type": "high_frequency_action",
                    "severity": "medium",
                    "description": f"1小时内操作{len(user_behaviors)}次",
                    "behavior_data": {"action_count": len(user_behaviors)},
                    "detected_at": datetime.now(),
                }, db))

            # 检测数据导出异常
            export_actions = [b for b in user_behaviors if b.action and "export" in b.action.lower()]
            if len(export_actions) > 10:
                anomalies.append(self._create_anomaly({
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "anomaly_type": "suspicious_export",
                    "severity": "high",
                    "description": f"1小时内导出数据{len(export_actions)}次",
                    "behavior_data": {"export_count": len(export_actions)},
                    "detected_at": datetime.now(),
                }, db))

        return anomalies

    def detect_data_anomalies(
        self,
        db: Session,
        tenant_id: str
    ) -> List[BehaviorAnomaly]:
        """
        检测数据访问异常

        检测项:
        1. 批量下载敏感数据
        2. 非工作时间大量数据查询
        """
        anomalies = []

        # 检测非工作时间的大量数据访问
        now = datetime.now()
        if now.hour < 6 or now.hour > 22:  # 晚上10点到早上6点
            hour_ago = now - timedelta(hours=1)

            night_queries = db.query(UserBehavior).filter(
                UserBehavior.tenant_id == tenant_id,
                UserBehavior.behavior_type == "data_query",
                UserBehavior.occurred_at >= hour_ago
            ).all()

            # 按用户统计
            user_query_counts = {}
            for behavior in night_queries:
                user_query_counts[behavior.user_id] = user_query_counts.get(behavior.user_id, 0) + 1

            for user_id, count in user_query_counts.items():
                if count > 50:  # 非工作时间1小时内查询超过50次
                    anomalies.append(self._create_anomaly({
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "anomaly_type": "unusual_data_access",
                        "severity": "medium",
                        "description": f"非工作时间查询数据{count}次",
                        "behavior_data": {"query_count": count},
                        "detected_at": datetime.now(),
                    }, db))

        return anomalies

    def check_rules(
        self,
        db: Session,
        tenant_id: str
    ) -> List[BehaviorAnomaly]:
        """
        检查所有激活的规则并生成异常告警
        """
        anomalies = []

        # 获取激活的规则
        rules = db.query(BehaviorRule).filter(
            BehaviorRule.tenant_id == tenant_id,
            BehaviorRule.is_active == True
        ).all()

        for rule in rules:
            rule_anomalies = self._check_rule(rule, db)
            anomalies.extend(rule_anomalies)

            # 更新规则触发统计
            if rule_anomalies:
                rule.trigger_count = (rule.trigger_count or 0) + len(rule_anomalies)
                rule.last_triggered_at = datetime.now()

        db.commit()
        return anomalies

    def _check_rule(self, rule: BehaviorRule, db: Session) -> List[BehaviorAnomaly]:
        """检查单个规则"""
        anomalies = []
        conditions = rule.conditions or {}

        # 根据规则类型检测
        rule_type = conditions.get("rule_type", rule.rule_type)

        if rule_type == "frequency":
            anomalies = self._check_frequency_rule(rule, db)
        elif rule_type == "time":
            anomalies = self._check_time_rule(rule, db)
        elif rule_type == "location":
            anomalies = self._check_location_rule(rule, db)

        # 为异常添加规则信息
        for anomaly in anomalies:
            anomaly.rule_id = rule.id
            anomaly.rule_name = rule.name

        return anomalies

    def _check_frequency_rule(self, rule: BehaviorRule, db: Session) -> List[BehaviorAnomaly]:
        """检查频率规则"""
        anomalies = []
        conditions = rule.conditions or {}

        behavior_type = conditions.get("behavior_type")
        threshold = conditions.get("threshold", 100)
        time_window = conditions.get("time_window", "1h")

        # 解析时间窗口
        window_hours = self._parse_time_window(time_window)
        since = datetime.now() - timedelta(hours=window_hours)

        # 统计行为次数
        query = db.query(
            UserBehavior.user_id,
            func.count(UserBehavior.id).label("count")
        ).filter(
            UserBehavior.tenant_id == rule.tenant_id,
            UserBehavior.occurred_at >= since
        )

        if behavior_type:
            query = query.filter(UserBehavior.behavior_type == behavior_type)

        query = query.group_by(UserBehavior.user_id).all()

        for user_id, count in query:
            if count > threshold:
                anomalies.append(self._create_anomaly({
                    "tenant_id": rule.tenant_id,
                    "user_id": user_id,
                    "anomaly_type": f"frequency_{behavior_type or 'action'}",
                    "severity": conditions.get("severity", "medium"),
                    "description": f"{time_window}内{behavior_type or '操作'}{count}次，超过阈值{threshold}",
                    "behavior_data": {
                        "count": count,
                        "threshold": threshold,
                        "time_window": time_window,
                    },
                    "detected_at": datetime.now(),
                }, db))

        return anomalies

    def _check_time_rule(self, rule: BehaviorRule, db: Session) -> List[BehaviorAnomaly]:
        """检查时间规则"""
        anomalies = []
        conditions = rule.conditions or {}

        allowed_hours = conditions.get("allowed_hours", list(range(24)))
        behavior_types = conditions.get("behavior_types", [])

        since = datetime.now() - timedelta(hours=24)

        # 查询在允许时间之外的行为
        query = db.query(UserBehavior).filter(
            UserBehavior.tenant_id == rule.tenant_id,
            UserBehavior.occurred_at >= since
        )

        if behavior_types:
            query = query.filter(UserBehavior.behavior_type.in_(behavior_types))

        behaviors = query.all()

        for behavior in behaviors:
            if behavior.occurred_at.hour not in allowed_hours:
                anomalies.append(self._create_anomaly({
                    "tenant_id": rule.tenant_id,
                    "user_id": behavior.user_id,
                    "anomaly_type": "unusual_time_activity",
                    "severity": conditions.get("severity", "low"),
                    "description": f"在非允许时间({behavior.occurred_at.hour}:00)进行操作",
                    "behavior_data": {
                        "action": behavior.action,
                        "time": behavior.occurred_at.isoformat(),
                    },
                    "detected_at": datetime.now(),
                }, db))

        return anomalies

    def _check_location_rule(self, rule: BehaviorRule, db: Session) -> List[BehaviorAnomaly]:
        """检查位置规则"""
        # 简化实现：检查IP变化
        return []

    def _parse_time_window(self, time_window: str) -> int:
        """解析时间窗口字符串"""
        if time_window.endswith("h"):
            return int(time_window[:-1])
        elif time_window.endswith("d"):
            return int(time_window[:-1]) * 24
        elif time_window.endswith("m"):
            return int(time_window[:-1]) / 60
        return 1

    def _create_anomaly(self, anomaly_data: Dict, db: Session) -> BehaviorAnomaly:
        """创建异常记录"""
        # 检查是否已存在相同异常（去重）
        existing = db.query(BehaviorAnomaly).filter(
            BehaviorAnomaly.tenant_id == anomaly_data["tenant_id"],
            BehaviorAnomaly.user_id == anomaly_data["user_id"],
            BehaviorAnomaly.anomaly_type == anomaly_data["anomaly_type"],
            BehaviorAnomaly.status == "open",
            BehaviorAnomaly.created_at >= datetime.now() - timedelta(hours=1)
        ).first()

        if existing:
            return existing

        anomaly = BehaviorAnomaly(
            id=str(uuid.uuid4()),
            **anomaly_data
        )
        db.add(anomaly)
        db.commit()

        return anomaly

    def get_anomalies(
        self,
        db: Session,
        tenant_id: str,
        severity: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[BehaviorAnomaly]:
        """获取异常列表"""
        query = db.query(BehaviorAnomaly).filter(
            BehaviorAnomaly.tenant_id == tenant_id
        )

        if severity:
            query = query.filter(BehaviorAnomaly.severity == severity)
        if status:
            query = query.filter(BehaviorAnomaly.status == status)

        return query.order_by(
            BehaviorAnomaly.detected_at.desc()
        ).limit(limit).all()

    def update_anomaly_status(
        self,
        db: Session,
        anomaly_id: str,
        status: str,
        investigated_by: str = None,
        notes: str = None
    ) -> Optional[BehaviorAnomaly]:
        """更新异常状态"""
        anomaly = db.query(BehaviorAnomaly).filter(
            BehaviorAnomaly.id == anomaly_id
        ).first()

        if anomaly:
            anomaly.status = status
            if investigated_by:
                anomaly.investigated_by = investigated_by
            if notes:
                anomaly.investigation_notes = notes
            anomaly.investigated_at = datetime.now() if status != "open" else None
            db.commit()

        return anomaly
