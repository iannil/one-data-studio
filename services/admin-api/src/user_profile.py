"""
用户画像服务
Phase 2.3: 用户行为分析画像
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, case

from database import db_manager
from models.user_profile import UserProfile, UserSegment, UserTag, BehaviorAnomaly
from models.portal import UserActivityLog
from models.user import User

logger = logging.getLogger(__name__)


class UserProfileService:
    """用户画像服务"""

    def build_profile(self, user_id: str, force_rebuild: bool = False) -> Optional[UserProfile]:
        """
        构建用户画像

        Args:
            user_id: 用户ID
            force_rebuild: 是否强制重建

        Returns:
            用户画像对象
        """
        with db_manager.get_session() as session:
            # 检查用户是否存在
            user = session.query(User).filter(User.user_id == user_id).first()
            if not user:
                return None

            # 检查是否已存在画像
            profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if profile and not force_rebuild:
                # 检查是否需要更新（最近活动超过1天）
                if profile.profile_updated_at and profile.profile_updated_at > datetime.utcnow() - timedelta(days=1):
                    return profile

            # 获取用户活动数据
            activities = session.query(UserActivityLog).filter(
                UserActivityLog.user_id == user_id,
                UserActivityLog.created_at >= datetime.utcnow() - timedelta(days=90)
            ).all()

            # 计算活跃度分数
            activity_score = self._calculate_activity_score(activities)

            # 提取行为标签
            behavior_tags = self._extract_behavior_tags(activities)

            # 计算偏好特征
            preference_features = self._extract_preferences(activities)

            # 确定用户分群
            segment_id = self._determine_segment(activity_score, behavior_tags, activities)
            segment = session.query(UserSegment).filter(UserSegment.segment_id == segment_id).first()
            segment_name = segment.segment_name if segment else None

            # 获取最后活动时间
            last_activity = None
            if activities:
                last_activity = max(a.created_at for a in activities)

            # 创建或更新画像
            if profile:
                profile.activity_score = activity_score
                profile.behavior_tags = behavior_tags
                profile.preference_features = preference_features
                profile.segment_id = segment_id
                profile.last_activity = last_activity
                profile.profile_updated_at = datetime.utcnow()
            else:
                from models.user_profile import generate_profile_id
                profile = UserProfile(
                    profile_id=generate_profile_id(),
                    user_id=user_id,
                    username=user.username,
                    display_name=user.display_name,
                    activity_score=activity_score,
                    behavior_tags=behavior_tags,
                    preference_features=preference_features,
                    segment_id=segment_id,
                    last_activity=last_activity,
                    profile_updated_at=datetime.utcnow(),
                )
                session.add(profile)

            session.commit()
            session.refresh(profile)
            return profile

    def _calculate_activity_score(self, activities: List[UserActivityLog]) -> float:
        """计算活跃度分数 (0-100)"""
        if not activities:
            return 0.0

        now = datetime.utcnow()
        total_score = 0.0

        # 最近7天活动权重最高
        for activity in activities:
            days_ago = (now - activity.created_at).days
            if days_ago < 7:
                total_score += 10
            elif days_ago < 14:
                total_score += 7
            elif days_ago < 30:
                total_score += 4
            elif days_ago < 90:
                total_score += 1

        # 计算登录频率分数
        login_count = sum(1 for a in activities if a.action == "login")
        login_score = min(login_count * 2, 20)

        total_score = min(total_score + login_score, 100)
        return round(total_score, 2)

    def _extract_behavior_tags(self, activities: List[UserActivityLog]) -> List[str]:
        """提取行为标签"""
        tags = set()

        if not activities:
            return []

        # 分析活动类型
        action_counts = {}
        for activity in activities:
            action = activity.action
            action_counts[action] = action_counts.get(action, 0) + 1

        total_actions = len(activities)

        # 基于活动频率打标签
        if action_counts.get("login", 0) / total_actions > 0.5:
            tags.add("频繁登录")
        if action_counts.get("create", 0) > 5:
            tags.add("内容创作者")
        if action_counts.get("export", 0) > 3:
            tags.add("数据导出用户")
        if any("model" in a.resource_type for a in activities if a.resource_type):
            tags.add("模型使用者")
        if any("workflow" in a.resource_type for a in activities if a.resource_type):
            tags.add("工作流使用者")

        # 分析活动时间
        hours = [a.created_at.hour for a in activities if a.created_at]
        if hours:
            avg_hour = sum(hours) / len(hours)
            if avg_hour >= 9 and avg_hour <= 18:
                tags.add("工作时间活跃")
            else:
                tags.add("非工作时间活跃")

        return list(tags)

    def _extract_preferences(self, activities: List[UserActivityLog]) -> Dict[str, Any]:
        """提取偏好特征"""
        preferences = {}

        if not activities:
            return preferences

        # 资源类型偏好
        resource_counts = {}
        for activity in activities:
            if activity.resource_type:
                resource_counts[activity.resource_type] = resource_counts.get(activity.resource_type, 0) + 1

        if resource_counts:
            top_resource = max(resource_counts.items(), key=lambda x: x[1])
            preferences["favorite_resource_type"] = top_resource[0]

        # 活跃时间段
        hours = [a.created_at.hour for a in activities]
        if hours:
            hour_counts = {}
            for h in hours:
                hour_counts[h] = hour_counts.get(h, 0) + 1
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
            preferences["peak_active_hour"] = peak_hour

        # 常用功能
        resource_types = set(a.resource_type for a in activities if a.resource_type)
        preferences["used_features"] = list(resource_types)

        return preferences

    def _determine_segment(self, activity_score: float, tags: List[str], activities: List[UserActivityLog]) -> str:
        """确定用户分群"""
        # 获取现有分群
        segments = {
            "active": {"min_score": 70, "name": "活跃型"},
            "new": {"max_days": 7, "min_score": 0, "name": "新用户"},
            "churned": {"max_days": 30, "min_score": 10, "name": "流失风险"},
            "power": {"min_score": 80, "tags": ["频繁登录", "内容创作者"], "name": "深度用户"},
            "exploratory": {"min_score": 30, "max_score": 70, "name": "探索型"},
            "conservative": {"min_score": 0, "max_score": 30, "name": "保守型"},
        }

        # 计算最近活动天数
        last_activity_days = 999
        if activities:
            last_activity_days = (datetime.utcnow() - max(a.created_at for a in activities)).days

        # 检查分群条件
        # 深度用户
        if activity_score >= segments["power"]["min_score"]:
            required_tags = segments["power"]["tags"]
            if any(tag in tags for tag in required_tags):
                return "seg_power"

        # 新用户
        if last_activity_days <= segments["new"]["max_days"]:
            return "seg_new"

        # 流失风险
        if last_activity_days >= segments["churned"]["max_days"] and activity_score < segments["churned"]["min_score"]:
            return "seg_churned"

        # 活跃型
        if activity_score >= segments["active"]["min_score"]:
            return "seg_active"

        # 保守型
        if activity_score <= segments["conservative"]["max_score"]:
            return "seg_conservative"

        # 探索型
        if segments["exploratory"]["min_score"] <= activity_score <= segments["exploratory"]["max_score"]:
            return "seg_exploratory"

        # 默认
        return "seg_conservative"

    def get_insights(self, days: int = 30) -> Dict[str, Any]:
        """获取行为洞察"""
        start_time = datetime.utcnow() - timedelta(days=days)

        with db_manager.get_session() as session:
            # 总用户数
            total_users = session.query(func.count(User.user_id)).scalar()

            # 活跃用户数（有活动记录）
            active_users = session.query(func.count(func.distinct(UserActivityLog.user_id))).filter(
                UserActivityLog.created_at >= start_time
            ).scalar()

            # 分群分布
            segment_distribution = {}
            segments = session.query(UserSegment).filter(UserSegment.is_active == True).all()
            for seg in segments:
                count = session.query(func.count(UserProfile.user_id)).filter(
                    UserProfile.segment_id == seg.segment_id
                ).scalar()
                segment_distribution[seg.segment_name] = count or 0

            # 活跃热力图（小时 x 星期几）
            heatmap = {}
            activities = session.query(UserActivityLog).filter(
                UserActivityLog.created_at >= start_time
            ).all()

            for act in activities:
                hour = act.created_at.hour
                day = act.created_at.weekday()
                key = f"{day}_{hour}"
                heatmap[key] = heatmap.get(key, 0) + 1

            # 常用功能
            resource_counts = session.query(
                UserActivityLog.resource_type,
                func.count(UserActivityLog.id).label('count')
            ).filter(
                UserActivityLog.created_at >= start_time,
                UserActivityLog.resource_type.isnot(None)
            ).group_by(UserActivityLog.resource_type).order_by(
                func.count(UserActivityLog.id).desc()
            ).limit(10).all()

            top_features = [
                {"feature": r.resource_type, "usage_count": r.count}
                for r in resource_counts
            ]

            # 流失风险用户（30天无活动）
            churn_risk = session.query(func.count(UserProfile.user_id)).filter(
                UserProfile.last_activity < datetime.utcnow() - timedelta(days=30),
                UserProfile.activity_score < 30
            ).scalar()

            # 趋势行为
            recent_activities = session.query(
                func.date(UserActivityLog.created_at).label('date'),
                UserActivityLog.action,
                func.count(UserActivityLog.id).label('count')
            ).filter(
                UserActivityLog.created_at >= start_time
            ).group_by(
                func.date(UserActivityLog.created_at),
                UserActivityLog.action
            ).order_by(func.date(UserActivityLog.created_at)).all()

            trending_behaviors = []
            if len(recent_activities) >= 2:
                for i in range(len(recent_activities) - 1):
                    curr = recent_activities[i + 1]
                    prev = recent_activities[i]
                    trend = "up" if curr.count > prev.count else "down"
                    trending_behaviors.append({
                        "behavior": curr.action,
                        "count": curr.count,
                        "trend": trend
                    })

            return {
                "total_users": total_users or 0,
                "active_users": active_users or 0,
                "segment_distribution": segment_distribution,
                "activity_heatmap": heatmap,
                "top_features": top_features,
                "churn_risk_users": churn_risk or 0,
                "trending_behaviors": trending_behaviors,
            }

    def rebuild_all_profiles(self, days: int = 7) -> Dict[str, int]:
        """重建所有用户画像"""
        with db_manager.get_session() as session:
            # 获取最近活跃的用户
            active_user_ids = session.query(
                UserActivityLog.user_id
            ).filter(
                UserActivityLog.created_at >= datetime.utcnow() - timedelta(days=days)
            ).distinct().all()

            active_user_ids = [u[0] for u in active_user_ids]

            count = 0
            errors = 0
            for user_id in active_user_ids:
                try:
                    self.build_profile(user_id, force_rebuild=True)
                    count += 1
                except Exception as e:
                    logger.error(f"Error building profile for {user_id}: {e}")
                    errors += 1

            return {
                "total": len(active_user_ids),
                "success": count,
                "errors": errors
            }


# 全局实例
_user_profile_service: Optional[UserProfileService] = None


def get_user_profile_service() -> UserProfileService:
    """获取用户画像服务单例"""
    global _user_profile_service
    if _user_profile_service is None:
        _user_profile_service = UserProfileService()
    return _user_profile_service
