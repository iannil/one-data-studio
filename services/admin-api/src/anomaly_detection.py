"""
用户行为异常检测服务
Phase 1.3: 检测用户行为中的异常模式
"""

import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database import db_manager
from models.user_profile import UserProfile, BehaviorAnomaly
from models.portal import UserActivityLog
from behavior_analyzer import get_behavior_analyzer

logger = logging.getLogger(__name__)


# 异常检测配置
ANOMALY_THRESHOLDS = {
    "login_frequency": {
        "max_per_hour": 20,  # 每小时最多登录次数
        "max_per_day": 100,  # 每天最多登录次数
    },
    "query_volume": {
        "max_per_hour": 100,  # 每小时最多查询次数
        "max_per_day": 1000,  # 每天最多查询次数
    },
    "export_volume": {
        "max_per_day": 50,  # 每天最多导出次数
        "max_rows_per_export": 100000,  # 单次最多导出行数
    },
    "unusual_time": {
        "night_start": 22,  # 夜间开始时间
        "night_end": 6,  # 夜间结束时间
        "night_threshold": 10,  # 夜间操作阈值
    },
    "geographic": {
        "max_distance_km": 1000,  # 最大地理位置距离
    },
}


class AnomalyDetector:
    """用户行为异常检测器"""

    def __init__(self):
        self.analyzer = get_behavior_analyzer()
        self.thresholds = ANOMALY_THRESHOLDS

    def detect_anomalies(
        self,
        user_id: Optional[str] = None,
        hours: int = 24,
        auto_create: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        检测用户行为异常

        Args:
            user_id: 用户ID（为空则检测所有用户）
            hours: 检测时间范围（小时）
            auto_create: 是否自动创建异常记录

        Returns:
            检测到的异常列表
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        anomalies = []

        with db_manager.get_session() as session:
            # 构建查询
            query = session.query(UserActivityLog.user_id).filter(
                UserActivityLog.created_at >= start_time
            )

            if user_id:
                query = query.filter(UserActivityLog.user_id == user_id)

            user_ids = [u[0] for u in query.distinct().all()]

            # 逐个用户检测
            for uid in user_ids:
                user_anomalies = self._detect_user_anomalies(uid, start_time, end_time, session)
                anomalies.extend(user_anomalies)

                # 自动创建异常记录
                if auto_create:
                    for anomaly_data in user_anomalies:
                        self._create_anomaly_record(anomaly_data, session)

            session.commit()

        return anomalies

    def _detect_user_anomalies(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        session: Session,
    ) -> List[Dict[str, Any]]:
        """
        检测单个用户的异常

        Args:
            user_id: 用户ID
            start_time: 开始时间
            end_time: 结束时间
            session: 数据库会话

        Returns:
            异常列表
        """
        anomalies = []

        # 获取用户活动
        activities = session.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.created_at >= start_time,
                UserActivityLog.created_at < end_time,
            )
        ).all()

        if not activities:
            return anomalies

        # 获取用户名
        username = activities[0].username if activities else None

        # 检测各种异常类型
        anomalies.extend(self._detect_login_anomalies(user_id, username, activities))
        anomalies.extend(self._detect_query_volume_anomalies(user_id, username, activities))
        anomalies.extend(self._detect_export_anomalies(user_id, username, activities))
        anomalies.extend(self._detect_time_anomalies(user_id, username, activities))
        anomalies.extend(self._detect_frequency_surge(user_id, username, activities, session))

        return anomalies

    def _detect_login_anomalies(
        self,
        user_id: str,
        username: Optional[str],
        activities: List[UserActivityLog],
    ) -> List[Dict[str, Any]]:
        """检测登录异常"""
        anomalies = []

        # 统计登录次数
        logins = [a for a in activities if a.action.lower() == "login"]

        # 按小时统计
        hourly_logins = defaultdict(int)
        for login in logins:
            if login.created_at:
                hourly_logins[login.created_at.hour] += 1

        # 检查每小时登录频率
        for hour, count in hourly_logins.items():
            if count > self.thresholds["login_frequency"]["max_per_hour"]:
                anomalies.append({
                    "user_id": user_id,
                    "username": username,
                    "anomaly_type": "login_anomaly",
                    "severity": "high" if count > self.thresholds["login_frequency"]["max_per_hour"] * 2 else "medium",
                    "description": f"在 {hour}:00-{hour+1}:00 时段内登录 {count} 次，超过正常阈值",
                    "details": {
                        "hour": hour,
                        "login_count": count,
                        "threshold": self.thresholds["login_frequency"]["max_per_hour"],
                    },
                })

        # 检查每天登录频率
        if len(logins) > self.thresholds["login_frequency"]["max_per_day"]:
            anomalies.append({
                "user_id": user_id,
                "username": username,
                "anomaly_type": "login_anomaly",
                "severity": "medium",
                "description": f"24小时内登录 {len(logins)} 次，超过正常阈值",
                "details": {
                    "login_count": len(logins),
                    "threshold": self.thresholds["login_frequency"]["max_per_day"],
                },
            })

        return anomalies

    def _detect_query_volume_anomalies(
        self,
        user_id: str,
        username: Optional[str],
        activities: List[UserActivityLog],
    ) -> List[Dict[str, Any]]:
        """检测查询量异常"""
        anomalies = []

        # 统计查询操作
        queries = [a for a in activities if a.action.lower() in ["query", "search", "execute"]]

        # 按小时统计
        hourly_queries = defaultdict(int)
        for query in queries:
            if query.created_at:
                hourly_queries[query.created_at.hour] += 1

        # 检查每小时查询频率
        for hour, count in hourly_queries.items():
            if count > self.thresholds["query_volume"]["max_per_hour"]:
                anomalies.append({
                    "user_id": user_id,
                    "username": username,
                    "anomaly_type": "query_volume",
                    "severity": "high" if count > self.thresholds["query_volume"]["max_per_hour"] * 2 else "medium",
                    "description": f"在 {hour}:00-{hour+1}:00 时段内执行查询 {count} 次，超过正常阈值",
                    "details": {
                        "hour": hour,
                        "query_count": count,
                        "threshold": self.thresholds["query_volume"]["max_per_hour"],
                    },
                })

        # 检查每天查询总量
        if len(queries) > self.thresholds["query_volume"]["max_per_day"]:
            anomalies.append({
                "user_id": user_id,
                "username": username,
                "anomaly_type": "query_volume",
                "severity": "medium",
                "description": f"24小时内执行查询 {len(queries)} 次，超过正常阈值",
                "details": {
                    "query_count": len(queries),
                    "threshold": self.thresholds["query_volume"]["max_per_day"],
                },
            })

        return anomalies

    def _detect_export_anomalies(
        self,
        user_id: str,
        username: Optional[str],
        activities: List[UserActivityLog],
    ) -> List[Dict[str, Any]]:
        """检测导出异常"""
        anomalies = []

        # 统计导出操作
        exports = [a for a in activities if a.action.lower() in ["export", "download"]]

        # 检查每天导出次数
        if len(exports) > self.thresholds["export_volume"]["max_per_day"]:
            anomalies.append({
                "user_id": user_id,
                "username": username,
                "anomaly_type": "data_export",
                "severity": "high",
                "description": f"24小时内导出数据 {len(exports)} 次，超过正常阈值，可能存在数据泄露风险",
                "details": {
                    "export_count": len(exports),
                    "threshold": self.thresholds["export_volume"]["max_per_day"],
                },
            })

        # 检查单次导出行数（如果有）
        for export in exports:
            request_body = export.get_request_body() if hasattr(export, 'get_request_body') else None
            if request_body and isinstance(request_body, dict):
                row_count = request_body.get("row_count") or request_body.get("limit")
                if row_count and row_count > self.thresholds["export_volume"]["max_rows_per_export"]:
                    anomalies.append({
                        "user_id": user_id,
                        "username": username,
                        "anomaly_type": "data_export",
                        "severity": "high",
                        "description": f"单次导出数据量过大 ({row_count} 行)，可能存在数据泄露风险",
                        "details": {
                            "row_count": row_count,
                            "threshold": self.thresholds["export_volume"]["max_rows_per_export"],
                            "resource": export.resource_name,
                        },
                    })

        return anomalies

    def _detect_time_anomalies(
        self,
        user_id: str,
        username: Optional[str],
        activities: List[UserActivityLog],
    ) -> List[Dict[str, Any]]:
        """检测时间异常（夜间操作）"""
        anomalies = []

        # 统计夜间操作
        night_start = self.thresholds["unusual_time"]["night_start"]
        night_end = self.thresholds["unusual_time"]["night_end"]

        night_activities = []
        for activity in activities:
            if activity.created_at:
                hour = activity.created_at.hour
                if hour >= night_start or hour < night_end:
                    night_activities.append(activity)

        # 检查夜间操作频率
        if len(night_activities) > self.thresholds["unusual_time"]["night_threshold"]:
            anomalies.append({
                "user_id": user_id,
                "username": username,
                "anomaly_type": "unusual_access",
                "severity": "medium",
                "description": f"在夜间时段 ({night_start}:00-{night_end}:00) 有 {len(night_activities)} 次操作",
                "details": {
                    "night_activity_count": len(night_activities),
                    "threshold": self.thresholds["unusual_time"]["night_threshold"],
                },
            })

        return anomalies

    def _detect_frequency_surge(
        self,
        user_id: str,
        username: Optional[str],
        activities: List[UserActivityLog],
        session: Session,
    ) -> List[Dict[str, Any]]:
        """检测操作频率激增"""
        anomalies = []

        if not activities:
            return anomalies

        # 获取历史平均操作频率
        end_time = activities[-1].created_at if activities[-1].created_at else datetime.utcnow()
        start_time = end_time - timedelta(days=30)

        historical_activities = session.query(func.count(UserActivityLog.id)).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.created_at >= start_time,
                UserActivityLog.created_at < end_time,
            )
        ).scalar() or 0

        # 计算平均每天操作次数
        avg_daily = historical_activities / 30

        # 当前窗口的操作次数
        current_window_start = end_time - timedelta(hours=24)
        current_count = len([a for a in activities if a.created_at and a.created_at >= current_window_start])

        # 检查是否激增
        if avg_daily > 0 and current_count > avg_daily * 5:  # 超过平均5倍
            anomalies.append({
                "user_id": user_id,
                "username": username,
                "anomaly_type": "frequency_surge",
                "severity": "medium",
                "description": f"操作频率激增，24小时内操作 {current_count} 次，是历史平均值 ({avg_daily:.1f} 次/天) 的 {current_count / avg_daily:.1f} 倍",
                "details": {
                    "current_count": current_count,
                    "historical_avg": avg_daily,
                    "surge_ratio": current_count / avg_daily if avg_daily > 0 else 0,
                },
            })

        return anomalies

    def _create_anomaly_record(
        self,
        anomaly_data: Dict[str, Any],
        session: Session,
    ) -> Optional[BehaviorAnomaly]:
        """创建异常记录"""
        # 检查是否已存在类似的未解决异常
        existing = session.query(BehaviorAnomaly).filter(
            and_(
                BehaviorAnomaly.user_id == anomaly_data["user_id"],
                BehaviorAnomaly.anomaly_type == anomaly_data["anomaly_type"],
                BehaviorAnomaly.status == "open",
                BehaviorAnomaly.created_at >= datetime.utcnow() - timedelta(hours=24),
            )
        ).first()

        if existing:
            return None

        anomaly = BehaviorAnomaly(
            anomaly_id=f"anom_{uuid.uuid4().hex[:12]}",
            user_id=anomaly_data["user_id"],
            username=anomaly_data["username"],
            anomaly_type=anomaly_data["anomaly_type"],
            severity=anomaly_data["severity"],
            description=anomaly_data["description"],
            details=anomaly_data["details"],
            status="open",
        )

        session.add(anomaly)

        # 标记用户为风险用户
        if anomaly_data["severity"] == "high":
            profile = session.query(UserProfile).filter(
                UserProfile.user_id == anomaly_data["user_id"]
            ).first()
            if profile:
                profile.is_risk_user = True
                profile.risk_reason = anomaly_data["description"]

        return anomaly

    def get_anomalies(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取异常记录

        Args:
            user_id: 用户ID过滤
            status: 状态过滤
            severity: 严重程度过滤
            limit: 返回数量限制

        Returns:
            异常记录列表
        """
        with db_manager.get_session() as session:
            query = session.query(BehaviorAnomaly)

            if user_id:
                query = query.filter(BehaviorAnomaly.user_id == user_id)
            if status:
                query = query.filter(BehaviorAnomaly.status == status)
            if severity:
                query = query.filter(BehaviorAnomaly.severity == severity)

            anomalies = query.order_by(
                BehaviorAnomaly.detected_at.desc()
            ).limit(limit).all()

            return [a.to_dict() for a in anomalies]

    def resolve_anomaly(
        self,
        anomaly_id: str,
        resolution: str,
        handled_by: str,
    ) -> bool:
        """
        处理异常

        Args:
            anomaly_id: 异常ID
            resolution: 处理结果
            handled_by: 处理人

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            anomaly = session.query(BehaviorAnomaly).filter(
                BehaviorAnomaly.anomaly_id == anomaly_id
            ).first()

            if not anomaly:
                return False

            anomaly.status = "resolved"
            anomaly.resolution = resolution
            anomaly.handled_by = handled_by
            anomaly.handled_at = datetime.utcnow()

            # 如果该用户没有其他未解决的高风险异常，移除风险标记
            high_risk_count = session.query(func.count(BehaviorAnomaly.id)).filter(
                and_(
                    BehaviorAnomaly.user_id == anomaly.user_id,
                    BehaviorAnomaly.severity == "high",
                    BehaviorAnomaly.status == "open",
                )
            ).scalar()

            if high_risk_count == 0:
                profile = session.query(UserProfile).filter(
                    UserProfile.user_id == anomaly.user_id
                ).first()
                if profile:
                    profile.is_risk_user = False
                    profile.risk_reason = None

            session.commit()

        return True


# 全局实例
_anomaly_detector: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    """获取异常检测器单例"""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector
