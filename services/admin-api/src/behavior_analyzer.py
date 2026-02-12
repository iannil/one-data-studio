"""
用户行为特征提取服务
Phase 1.3: 分析用户活动日志，提取行为特征，生成用户画像
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from database import db_manager
from models.user_profile import UserProfile, generate_profile_id
from models.portal import UserActivityLog

logger = logging.getLogger(__name__)


# 默认行为标签定义
DEFAULT_BEHAVIOR_TAGS = {
    "active": {"name": "活跃用户", "threshold": 70, "category": "activity"},
    "expert": {"name": "专家用户", "threshold": 100, "category": "ability"},
    "explorer": {"name": "探索型", "threshold": 5, "category": "preference"},
    "data_consumer": {"name": "数据消费者", "threshold": 20, "category": "preference"},
    "data_creator": {"name": "数据创建者", "threshold": 10, "category": "preference"},
    "night_owl": {"name": "夜猫子", "threshold": 0.3, "category": "timing"},
    "early_bird": {"name": "早起鸟", "threshold": 0.3, "category": "timing"},
}


class UserProfileAnalyzer:
    """
    用户画像分析器

    原名: BehaviorAnalyzer

    职责: 分析用户活动日志，提取行为特征，生成用户画像
    区别于 behavior-service 的 BehaviorMetricsAnalyzer（行为统计指标分析）
    """

    def __init__(self):
        self.tags_definition = DEFAULT_BEHAVIOR_TAGS

    def analyze_user(
        self,
        user_id: str,
        days: int = 30,
        force_refresh: bool = False,
    ) -> Optional[UserProfile]:
        """
        分析单个用户的行为特征

        Args:
            user_id: 用户ID
            days: 分析天数
            force_refresh: 是否强制刷新

        Returns:
            用户画像对象
        """
        with db_manager.get_session() as session:
            # 获取或创建用户画像
            profile = (
                session.query(UserProfile)
                .filter(UserProfile.user_id == user_id)
                .first()
            )

            if not profile:
                profile = UserProfile(
                    profile_id=generate_profile_id(),
                    user_id=user_id,
                )
                session.add(profile)
            elif not force_refresh:
                # 检查是否需要更新
                if profile.last_analyzed_at:
                    days_since_update = (
                        datetime.utcnow() - profile.last_analyzed_at
                    ).days
                    if days_since_update < 7:  # 7天内不重复分析
                        return profile

            # 计算分析时间范围
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            # 获取用户活动日志
            activities = (
                session.query(UserActivityLog)
                .filter(
                    and_(
                        UserActivityLog.user_id == user_id,
                        UserActivityLog.created_at >= start_time,
                        UserActivityLog.created_at < end_time,
                    )
                )
                .all()
            )

            if not activities:
                profile.activity_score = 0
                profile.last_analyzed_at = datetime.utcnow()
                session.commit()
                return profile

            # 提取行为特征
            features = self._extract_features(activities)

            # 更新画像
            self._update_profile(profile, features, session)

            session.commit()
            session.refresh(profile)

            return profile

    def analyze_all_users(
        self,
        days: int = 30,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        分析所有用户的行为特征

        Args:
            days: 分析天数
            batch_size: 批量处理大小

        Returns:
            分析结果统计
        """
        stats = {
            "total_users": 0,
            "analyzed_users": 0,
            "failed_users": 0,
            "start_time": datetime.utcnow().isoformat(),
        }

        with db_manager.get_session() as session:
            # 获取所有活跃用户
            active_users = (
                session.query(UserActivityLog.user_id)
                .filter(
                    UserActivityLog.created_at
                    >= datetime.utcnow() - timedelta(days=days)
                )
                .distinct()
                .all()
            )

            stats["total_users"] = len(active_users)

        # 批量分析
        for i in range(0, len(active_users), batch_size):
            batch = active_users[i : i + batch_size]
            for (user_id,) in batch:
                try:
                    profile = self.analyze_user(
                        user_id[0], days=days, force_refresh=True
                    )
                    if profile:
                        stats["analyzed_users"] += 1
                except Exception as e:
                    logger.error(f"Error analyzing user {user_id}: {e}")
                    stats["failed_users"] += 1

        stats["end_time"] = datetime.utcnow().isoformat()
        return stats

    def _extract_features(self, activities: List[UserActivityLog]) -> Dict[str, Any]:
        """
        从活动日志中提取特征

        Args:
            activities: 活动日志列表

        Returns:
            特征字典
        """
        features = {
            "login_count": 0,
            "query_count": 0,
            "export_count": 0,
            "create_count": 0,
            "update_count": 0,
            "delete_count": 0,
            "unique_days": set(),
            "hour_distribution": defaultdict(int),
            "day_distribution": defaultdict(int),
            "module_usage": defaultdict(int),
            "resource_types": defaultdict(int),
        }

        for activity in activities:
            # 统计操作类型
            action = activity.action.lower()
            if action == "login":
                features["login_count"] += 1
            elif action in ["query", "search", "execute"]:
                features["query_count"] += 1
            elif action in ["export", "download"]:
                features["export_count"] += 1
            elif action in ["create", "add"]:
                features["create_count"] += 1
            elif action in ["update", "edit"]:
                features["update_count"] += 1
            elif action in ["delete", "remove"]:
                features["delete_count"] += 1

            # 统计活跃日期
            if activity.created_at:
                features["unique_days"].add(activity.created_at.date())

                # 时段分布
                features["hour_distribution"][activity.created_at.hour] += 1
                features["day_distribution"][activity.created_at.weekday()] += 1

            # 统计模块使用
            if activity.resource_type:
                features["module_usage"][activity.resource_type] += 1

            # 统计资源类型
            if activity.resource_type:
                features["resource_types"][activity.resource_type] += 1

        # 转换集合为数量
        features["unique_days_count"] = len(features["unique_days"])
        features["unique_days"] = list(features["unique_days"])

        return features

    def _update_profile(
        self,
        profile: UserProfile,
        features: Dict[str, Any],
        session: Session,
    ):
        """
        更新用户画像

        Args:
            profile: 用户画像对象
            features: 提取的特征
            session: 数据库会话
        """
        # 更新基本统计
        profile.login_count = features["login_count"]
        profile.query_count = features["query_count"]
        profile.export_count = features["export_count"]
        profile.create_count = features["create_count"]
        profile.login_days = features["unique_days_count"]

        # 获取用户名
        if features["unique_days"]:
            last_activity = (
                session.query(UserActivityLog)
                .filter(UserActivityLog.user_id == profile.user_id)
                .order_by(UserActivityLog.created_at.desc())
                .first()
            )
            if last_activity:
                profile.username = last_activity.username
                profile.last_login_at = last_activity.created_at

        # 计算活跃度分数 (0-100)
        profile.activity_score = self._calculate_activity_score(features)

        # 更新时段偏好
        peak_hours = [
            {"hour": h, "count": c} for h, c in features["hour_distribution"].items()
        ]
        peak_hours.sort(key=lambda x: x["count"], reverse=True)
        profile.set_peak_hours(peak_hours[:10])  # 保留前10个

        # 更新星期偏好
        peak_days = [
            {"day": d, "count": c} for d, c in features["day_distribution"].items()
        ]
        peak_days.sort(key=lambda x: x["count"], reverse=True)
        profile.set_peak_days(peak_days)

        # 更新模块使用统计
        profile.set_module_usage(dict(features["module_usage"]))

        # 更新偏好特征
        profile.preference_features = self._generate_preference_features(features)

        # 自动打标签
        self._auto_tagging(profile, features)

        # 更新分析时间
        profile.last_analyzed_at = datetime.utcnow()

    def _calculate_activity_score(self, features: Dict[str, Any]) -> float:
        """
        计算活跃度分数

        Args:
            features: 特征字典

        Returns:
            活跃度分数 (0-100)
        """
        score = 0.0

        # 登录分数 (0-30分)
        login_score = min(features["login_count"] / 30 * 30, 30)
        score += login_score

        # 操作分数 (0-40分)
        total_actions = (
            features["query_count"]
            + features["create_count"]
            + features["export_count"]
        )
        action_score = min(total_actions / 100 * 40, 40)
        score += action_score

        # 连续性分数 (0-30分)
        consistency_score = min(features["unique_days_count"] / 7 * 30, 30)
        score += consistency_score

        return round(score, 2)

    def _generate_preference_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成偏好特征

        Args:
            features: 特征字典

        Returns:
            偏好特征字典
        """
        preference = {}

        # 活跃时段偏好
        hour_dist = features["hour_distribution"]
        if hour_dist:
            total = sum(hour_dist.values())
            day_hours = sum(c for h, c in hour_dist.items() if 6 <= h < 18)
            night_hours = sum(c for h, c in hour_dist.items() if h >= 18 or h < 6)
            preference["time_preference"] = (
                "day" if day_hours > night_hours else "night"
            )

        # 模块偏好
        module_usage = features["module_usage"]
        if module_usage:
            top_module = max(module_usage.items(), key=lambda x: x[1])
            preference["preferred_module"] = top_module[0]

        # 操作偏好
        total_ops = (
            features["query_count"]
            + features["create_count"]
            + features["export_count"]
        )
        if total_ops > 0:
            preference["operation_preference"] = {
                "query": features["query_count"] / total_ops,
                "create": features["create_count"] / total_ops,
                "export": features["export_count"] / total_ops,
            }

        return preference

    def _auto_tagging(self, profile: UserProfile, features: Dict[str, Any]):
        """
        自动打标签

        Args:
            profile: 用户画像对象
            features: 特征字典
        """
        tags = profile.get_behavior_tags()
        existing_tag_names = {t["tag"] for t in tags}

        # 活跃用户标签
        if profile.activity_score >= 70 and "active" not in existing_tag_names:
            profile.add_tag("active", min(profile.activity_score / 100, 1.0))

        # 专家用户标签（操作次数多）
        total_actions = features["query_count"] + features["create_count"]
        if total_actions >= 100 and "expert" not in existing_tag_names:
            profile.add_tag("expert", min(total_actions / 200, 1.0))

        # 探索型标签（使用多种模块）
        if len(features["module_usage"]) >= 5 and "explorer" not in existing_tag_names:
            profile.add_tag("explorer", min(len(features["module_usage"]) / 10, 1.0))

        # 数据消费者标签（查询多，创建少）
        if features["query_count"] >= 20 and features["create_count"] < 5:
            if "data_consumer" not in existing_tag_names:
                profile.add_tag(
                    "data_consumer", min(features["query_count"] / 100, 1.0)
                )

        # 数据创建者标签（创建多）
        if features["create_count"] >= 10:
            if "data_creator" not in existing_tag_names:
                profile.add_tag("data_creator", min(features["create_count"] / 50, 1.0))

        # 时间偏好标签
        hour_dist = features["hour_distribution"]
        if hour_dist:
            total = sum(hour_dist.values())
            night_hours = sum(c for h, c in hour_dist.items() if h >= 18 or h < 6)
            night_ratio = night_hours / total

            if night_ratio > 0.5 and "night_owl" not in existing_tag_names:
                profile.add_tag("night_owl", night_ratio)
            elif night_ratio < 0.3 and "early_bird" not in existing_tag_names:
                profile.add_tag("early_bird", 1 - night_ratio)

    def get_behavior_insights(
        self,
        user_id: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        获取行为洞察

        Args:
            user_id: 用户ID（可选，为空则返回整体洞察）
            days: 分析天数

        Returns:
            洞察数据
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        with db_manager.get_session() as session:
            query = session.query(UserActivityLog).filter(
                UserActivityLog.created_at >= start_time
            )

            if user_id:
                query = query.filter(UserActivityLog.user_id == user_id)

            activities = query.all()

        if not activities:
            return {"error": "No activity data found"}

        # 整体统计
        total_actions = len(activities)
        unique_users = len(set(a.user_id for a in activities))

        # 操作类型分布
        action_distribution = Counter(a.action for a in activities)

        # 时段分布
        hour_distribution = Counter(
            a.created_at.hour for a in activities if a.created_at
        )

        # 模块使用分布
        module_distribution = Counter(
            a.resource_type for a in activities if a.resource_type
        )

        # 资源类型分布
        resource_distribution = Counter(
            a.resource_type for a in activities if a.resource_type
        )

        # 每日活跃趋势
        daily_trend = defaultdict(int)
        for activity in activities:
            if activity.created_at:
                daily_trend[activity.created_at.date()] += 1

        return {
            "summary": {
                "total_actions": total_actions,
                "unique_users": unique_users,
                "avg_actions_per_user": total_actions / max(unique_users, 1),
                "date_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
            },
            "action_distribution": dict(action_distribution.most_common(10)),
            "hour_distribution": dict(sorted(hour_distribution.items())),
            "module_distribution": dict(module_distribution.most_common(10)),
            "resource_distribution": dict(resource_distribution.most_common(10)),
            "daily_trend": {
                date.isoformat(): count for date, count in sorted(daily_trend.items())
            },
        }

    def get_user_ranking(
        self,
        metric: str = "activity_score",
        limit: int = 20,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        获取用户排名

        Args:
            metric: 排名指标 (activity_score, login_count, query_count)
            limit: 返回数量
            days: 分析天数

        Returns:
            排名列表
        """
        # 确保用户画像是最新的
        with db_manager.get_session() as session:
            # 获取最近活跃的用户
            active_users = (
                session.query(UserActivityLog.user_id)
                .filter(
                    UserActivityLog.created_at
                    >= datetime.utcnow() - timedelta(days=days)
                )
                .distinct()
                .limit(500)
                .all()
            )

            user_ids = [u[0] for u in active_users]

            # 获取这些用户的画像
            profiles = (
                session.query(UserProfile)
                .filter(UserProfile.user_id.in_(user_ids))
                .all()
            )

            # 排序
            if metric == "activity_score":
                profiles.sort(key=lambda p: p.activity_score or 0, reverse=True)
            elif metric == "login_count":
                profiles.sort(key=lambda p: p.login_count or 0, reverse=True)
            elif metric == "query_count":
                profiles.sort(key=lambda p: p.query_count or 0, reverse=True)

            return [
                {
                    "rank": i + 1,
                    "user_id": p.user_id,
                    "username": p.username,
                    "activity_score": p.activity_score,
                    "login_count": p.login_count,
                    "query_count": p.query_count,
                    "export_count": p.export_count,
                    "create_count": p.create_count,
                    "segment_id": p.segment_id,
                    "behavior_tags": p.get_behavior_tags(),
                }
                for i, p in enumerate(profiles[:limit])
            ]


# 全局实例
_behavior_analyzer: Optional[BehaviorAnalyzer] = None


def get_user_profile_analyzer() -> UserProfileAnalyzer:
    """获取用户画像分析器单例"""
    global _behavior_analyzer
    if _behavior_analyzer is None:
        _behavior_analyzer = UserProfileAnalyzer()
    return _behavior_analyzer


# 向后兼容别名
BehaviorAnalyzer = UserProfileAnalyzer
get_behavior_analyzer = get_user_profile_analyzer
