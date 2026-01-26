"""
用户画像构建服务
基于用户行为数据生成用户画像
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models.user_behavior import UserBehavior, UserSession
from models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """画像构建器"""

    def __init__(self):
        pass

    def build_user_profile(
        self,
        db: Session,
        user_id: str,
        tenant_id: str,
        user_info: Dict = None
    ) -> UserProfile:
        """
        构建或更新用户画像

        user_info: {
            "username": "用户名",
            "email": "邮箱",
            "department": "部门",
            "position": "职位"
        }
        """
        # 获取现有画像
        profile = db.query(UserProfile).filter(
            UserProfile.tenant_id == tenant_id,
            UserProfile.user_id == user_id
        ).first()

        # 分析用户行为数据
        behavior_stats = self._analyze_user_behaviors(db, user_id, tenant_id)

        # 计算活跃度等级
        activity_level = self._calculate_activity_level(behavior_stats)

        # 提取偏好模块
        preferred_modules = self._extract_preferred_modules(db, user_id, tenant_id)

        # 提取常用操作
        common_actions = self._extract_common_actions(db, user_id, tenant_id)

        # 提取活跃时段
        preferred_time_ranges = self._extract_active_time_ranges(db, user_id, tenant_id)

        # 计算统计指标
        thirty_days_ago = datetime.now() - timedelta(days=30)

        total_sessions = db.query(func.count(UserSession.id)).filter(
            UserSession.tenant_id == tenant_id,
            UserSession.user_id == user_id,
            UserSession.start_time >= thirty_days_ago
        ).scalar() or 0

        total_page_views = db.query(func.count(UserBehavior.id)).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.user_id == user_id,
            UserBehavior.behavior_type == "page_view",
            UserBehavior.occurred_at >= thirty_days_ago
        ).scalar() or 0

        total_actions = db.query(func.count(UserBehavior.id)).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.user_id == user_id,
            UserBehavior.occurred_at >= thirty_days_ago
        ).scalar() or 0

        # 计算登录频率
        login_frequency = total_sessions / 30 if total_sessions > 0 else 0

        # 计算平均会话时长
        avg_session_duration_result = db.query(
            func.avg(UserSession.duration)
        ).filter(
            UserSession.tenant_id == tenant_id,
            UserSession.user_id == user_id,
            UserSession.start_time >= thirty_days_ago
        ).scalar()
        avg_session_duration = float(avg_session_duration_result) / 60 if avg_session_duration_result else 0  # 转换为分钟

        # 平均日使用时长
        avg_daily_usage = (avg_session_duration * total_sessions) / 30 if total_sessions > 0 else 0

        # 生成分群标签
        segment_tags = self._generate_segment_tags({
            "activity_level": activity_level,
            "preferred_modules": preferred_modules,
            "login_frequency": login_frequency,
            "avg_daily_usage": avg_daily_usage,
            "total_actions": total_actions,
        })

        if profile:
            # 更新现有画像
            profile.username = user_info.get("username") if user_info else profile.username
            profile.email = user_info.get("email") if user_info else profile.email
            profile.department = user_info.get("department") if user_info else profile.department
            profile.position = user_info.get("position") if user_info else profile.position
            profile.activity_level = activity_level
            profile.last_active_at = behavior_stats.get("last_active_at")
            profile.login_frequency = round(login_frequency, 2)
            profile.avg_session_duration = round(avg_session_duration, 2)
            profile.preferred_modules = preferred_modules
            profile.preferred_time_ranges = preferred_time_ranges
            profile.common_actions = common_actions
            profile.total_sessions = total_sessions
            profile.total_page_views = total_page_views
            profile.total_actions = total_actions
            profile.avg_daily_usage = round(avg_daily_usage, 2)
            profile.segment_tags = segment_tags
            profile.updated_at = datetime.now()

        else:
            # 创建新画像
            profile = UserProfile(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                username=user_info.get("username") if user_info else None,
                email=user_info.get("email") if user_info else None,
                department=user_info.get("department") if user_info else None,
                position=user_info.get("position") if user_info else None,
                activity_level=activity_level,
                last_active_at=behavior_stats.get("last_active_at"),
                login_frequency=round(login_frequency, 2),
                avg_session_duration=round(avg_session_duration, 2),
                preferred_modules=preferred_modules,
                preferred_time_ranges=preferred_time_ranges,
                common_actions=common_actions,
                total_sessions=total_sessions,
                total_page_views=total_page_views,
                total_actions=total_actions,
                avg_daily_usage=round(avg_daily_usage, 2),
                segment_tags=segment_tags,
            )
            db.add(profile)

        db.commit()
        return profile

    def _analyze_user_behaviors(
        self,
        db: Session,
        user_id: str,
        tenant_id: str
    ) -> Dict:
        """分析用户行为统计"""
        # 最近活跃时间
        last_active = db.query(func.max(UserBehavior.occurred_at)).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.user_id == user_id
        ).scalar()

        # 30天内的行为数量
        thirty_days_ago = datetime.now() - timedelta(days=30)

        behavior_count = db.query(func.count(UserBehavior.id)).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.user_id == user_id,
            UserBehavior.occurred_at >= thirty_days_ago
        ).scalar() or 0

        return {
            "last_active_at": last_active,
            "behavior_count_30d": behavior_count,
        }

    def _calculate_activity_level(self, behavior_stats: Dict) -> str:
        """计算活跃度等级"""
        count = behavior_stats.get("behavior_count_30d", 0)
        last_active = behavior_stats.get("last_active_at")

        # 检查是否最近7天活跃
        recently_active = False
        if last_active:
            days_since_active = (datetime.now() - last_active).days
            recently_active = days_since_active <= 7

        if count >= 500 and recently_active:
            return "high"
        elif count >= 100 and recently_active:
            return "medium"
        elif count >= 10:
            return "low"
        else:
            return "inactive"

    def _extract_preferred_modules(
        self,
        db: Session,
        user_id: str,
        tenant_id: str
    ) -> List[str]:
        """提取用户偏好模块"""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        module_counts = db.query(
            UserBehavior.module,
            func.count(UserBehavior.id).label("count")
        ).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.user_id == user_id,
            UserBehavior.occurred_at >= thirty_days_ago,
            UserBehavior.module.isnot(None)
        ).group_by(UserBehavior.module).order_by(
            func.count(UserBehavior.id).desc()
        ).limit(5).all()

        return [module for module, _ in module_counts if module]

    def _extract_common_actions(
        self,
        db: Session,
        user_id: str,
        tenant_id: str
    ) -> List[Dict]:
        """提取常用操作"""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        action_counts = db.query(
            UserBehavior.action,
            UserBehavior.behavior_type,
            func.count(UserBehavior.id).label("count")
        ).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.user_id == user_id,
            UserBehavior.occurred_at >= thirty_days_ago,
            UserBehavior.action.isnot(None)
        ).group_by(
            UserBehavior.action,
            UserBehavior.behavior_type
        ).order_by(
            func.count(UserBehavior.id).desc()
        ).limit(10).all()

        return [
            {
                "action": action,
                "type": behavior_type,
                "count": count
            }
            for action, behavior_type, count in action_counts
        ]

    def _extract_active_time_ranges(
        self,
        db: Session,
        user_id: str,
        tenant_id: str
    ) -> List[Dict]:
        """提取用户活跃时段"""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        hour_counts = db.query(
            func.hour(UserBehavior.occurred_at).label("hour"),
            func.count(UserBehavior.id).label("count")
        ).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.user_id == user_id,
            UserBehavior.occurred_at >= thirty_days_ago
        ).group_by(func.hour(UserBehavior.occurred_at)).all()

        # 按时段分组
        time_ranges = {
            "morning": (6, 12),   # 早上 6-12点
            "afternoon": (12, 18), # 下午 12-18点
            "evening": (18, 24),   # 晚上 18-24点
            "night": (0, 6),       # 夜晚 0-6点
        }

        range_counts = {key: 0 for key in time_ranges.keys()}
        for hour, count in hour_counts:
            for range_name, (start, end) in time_ranges.items():
                if start <= hour < end:
                    range_counts[range_name] += count
                    break

        # 找出最活跃的时段
        total = sum(range_counts.values()) or 1
        return [
            {
                "range": range_name,
                "count": count,
                "percentage": round(count / total * 100, 2)
            }
            for range_name, count in sorted(
                range_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]

    def _generate_segment_tags(self, profile_data: Dict) -> List[str]:
        """生成分群标签"""
        tags = []

        activity_level = profile_data.get("activity_level")
        if activity_level == "high":
            tags.append("power_user")
        elif activity_level == "inactive":
            tags.append("dormant_user")

        # 根据偏好模块打标签
        preferred_modules = profile_data.get("preferred_modules", [])
        if "data" in str(preferred_modules).lower():
            tags.append("data_analyst")
        if "admin" in str(preferred_modules).lower():
            tags.append("admin_user")

        # 根据登录频率打标签
        login_frequency = profile_data.get("login_frequency", 0)
        if login_frequency >= 1:
            tags.append("daily_user")
        elif login_frequency >= 0.5:
            tags.append("regular_user")

        # 根据使用时长打标签
        avg_daily_usage = profile_data.get("avg_daily_usage", 0)
        if avg_daily_usage >= 120:
            tags.append("heavy_user")

        return tags

    def get_profile(self, db: Session, user_id: str, tenant_id: str) -> Optional[UserProfile]:
        """获取用户画像"""
        return db.query(UserProfile).filter(
            UserProfile.tenant_id == tenant_id,
            UserProfile.user_id == user_id
        ).first()

    def get_profiles_by_segment(
        self,
        db: Session,
        tenant_id: str,
        segment_tag: str
    ) -> List[UserProfile]:
        """根据分群标签获取用户列表"""
        return db.query(UserProfile).filter(
            UserProfile.tenant_id == tenant_id,
            UserProfile.segment_tags.contains(segment_tag)
        ).all()

    def refresh_all_profiles(
        self,
        db: Session,
        tenant_id: str,
        batch_size: int = 100
    ) -> int:
        """
        刷新所有用户画像

        返回: 更新的画像数量
        """
        # 获取所有活跃用户（最近30天有行为）
        thirty_days_ago = datetime.now() - timedelta(days=30)

        active_users = db.query(UserBehavior.user_id).filter(
            UserBehavior.tenant_id == tenant_id,
            UserBehavior.occurred_at >= thirty_days_ago
        ).distinct().all()

        updated_count = 0
        for (user_id,) in active_users:
            try:
                self.build_user_profile(db, user_id, tenant_id)
                updated_count += 1

                # 批量提交
                if updated_count % batch_size == 0:
                    db.commit()

            except Exception as e:
                logger.error(f"Failed to build profile for user {user_id}: {e}")
                db.rollback()

        db.commit()
        return updated_count

    def get_similar_users(
        self,
        db: Session,
        user_id: str,
        tenant_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        获取相似用户

        基于分群标签和偏好模块相似度
        """
        profile = self.get_profile(db, user_id, tenant_id)
        if not profile:
            return []

        # 获取有相似分群标签的用户
        similar_profiles = db.query(UserProfile).filter(
            UserProfile.tenant_id == tenant_id,
            UserProfile.user_id != user_id
        ).all()

        # 计算相似度分数
        scored_profiles = []
        for other_profile in similar_profiles:
            score = self._calculate_similarity(profile, other_profile)
            if score > 0:
                scored_profiles.append({
                    "user_id": other_profile.user_id,
                    "similarity_score": score,
                    "username": other_profile.username,
                })

        # 按相似度排序
        scored_profiles.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored_profiles[:limit]

    def _calculate_similarity(self, profile1: UserProfile, profile2: UserProfile) -> float:
        """计算两个用户画像的相似度"""
        score = 0.0

        # 分群标签相似度 (权重: 0.4)
        tags1 = set(profile1.segment_tags or [])
        tags2 = set(profile2.segment_tags or [])
        if tags1 and tags2:
            tag_similarity = len(tags1 & tags2) / len(tags1 | tags2)
            score += tag_similarity * 0.4

        # 偏好模块相似度 (权重: 0.3)
        modules1 = set(profile1.preferred_modules or [])
        modules2 = set(profile2.preferred_modules or [])
        if modules1 and modules2:
            module_similarity = len(modules1 & modules2) / len(modules1 | modules2)
            score += module_similarity * 0.3

        # 活跃度相似度 (权重: 0.2)
        if profile1.activity_level == profile2.activity_level:
            score += 0.2

        # 部门相似度 (权重: 0.1)
        if profile1.department and profile1.department == profile2.department:
            score += 0.1

        return round(score, 3)
