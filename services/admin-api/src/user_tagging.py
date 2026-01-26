"""
用户标签管理服务
Phase 1.3: 标签定义、规则、自动打标
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database import db_manager
from models.user_profile import UserProfile, UserTag, BehaviorAnomaly

logger = logging.getLogger(__name__)


# 预定义标签配置
PREDEFINED_TAGS = [
    {
        "tag_name": "active",
        "display_name": "活跃用户",
        "tag_category": "behavior",
        "description": "高频登录和操作的用户",
        "color": "green",
        "icon": "thunderbolt",
        "priority": 100,
        "is_auto": True,
        "update_frequency": "daily",
        "rules": {"type": "activity", "min_score": 70},
    },
    {
        "tag_name": "expert",
        "display_name": "专家用户",
        "tag_category": "ability",
        "description": "深度使用平台功能的高级用户",
        "color": "blue",
        "icon": "star",
        "priority": 90,
        "is_auto": True,
        "update_frequency": "weekly",
        "rules": {"type": "operations", "min_count": 100},
    },
    {
        "tag_name": "newbie",
        "display_name": "新手用户",
        "tag_category": "ability",
        "description": "最近注册的新用户",
        "color": "cyan",
        "icon": "user",
        "priority": 80,
        "is_auto": True,
        "update_frequency": "daily",
        "rules": {"type": "registration", "max_days": 7},
    },
    {
        "tag_name": "data_enthusiast",
        "display_name": "数据爱好者",
        "tag_category": "preference",
        "description": "频繁查询和分析数据的用户",
        "color": "purple",
        "icon": "bar-chart",
        "priority": 70,
        "is_auto": True,
        "update_frequency": "weekly",
        "rules": {"type": "query", "min_count": 50},
    },
    {
        "tag_name": "night_owl",
        "display_name": "夜猫子",
        "tag_category": "behavior",
        "description": "主要在夜间时段活跃的用户",
        "color": "orange",
        "icon": "moon",
        "priority": 60,
        "is_auto": True,
        "update_frequency": "weekly",
        "rules": {"type": "timing", "night_ratio_min": 0.5},
    },
    {
        "tag_name": "early_bird",
        "display_name": "早起鸟",
        "tag_category": "behavior",
        "description": "主要在工作日早晨活跃的用户",
        "color": "gold",
        "icon": "sun",
        "priority": 60,
        "is_auto": True,
        "update_frequency": "weekly",
        "rules": {"type": "timing", "morning_ratio_min": 0.4},
    },
    {
        "tag_name": "high_risk",
        "display_name": "高风险用户",
        "tag_category": "risk",
        "description": "存在异常行为需要关注的用户",
        "color": "red",
        "icon": "alert",
        "priority": 100,
        "is_auto": True,
        "update_frequency": "daily",
        "rules": {"type": "anomaly", "min_count": 1},
    },
]


class UserTagging:
    """用户标签管理器"""

    def __init__(self):
        self.predefined_tags = PREDEFINED_TAGS

    def initialize_tags(self) -> int:
        """
        初始化预定义标签

        Returns:
            创建的标签数量
        """
        count = 0
        with db_manager.get_session() as session:
            for tag_config in self.predefined_tags:
                # 检查是否已存在
                existing = session.query(UserTag).filter(
                    UserTag.tag_name == tag_config["tag_name"]
                ).first()

                if not existing:
                    tag = UserTag(
                        tag_id=f"tag_{uuid.uuid4().hex[:8]}",
                        tag_name=tag_config["tag_name"],
                        display_name=tag_config["display_name"],
                        tag_category=tag_config["tag_category"],
                        description=tag_config["description"],
                        color=tag_config["color"],
                        icon=tag_config["icon"],
                        priority=tag_config["priority"],
                        is_auto=tag_config["is_auto"],
                        update_frequency=tag_config["update_frequency"],
                        rules=tag_config["rules"],
                        is_active=True,
                    )
                    session.add(tag)
                    count += 1

            session.commit()

        logger.info(f"Initialized {count} predefined tags")
        return count

    def get_tags(
        self,
        category: Optional[str] = None,
        is_active: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        获取标签列表

        Args:
            category: 标签分类过滤
            is_active: 是否只返回启用的标签

        Returns:
            标签列表
        """
        with db_manager.get_session() as session:
            query = session.query(UserTag)

            if category:
                query = query.filter(UserTag.tag_category == category)
            if is_active:
                query = query.filter(UserTag.is_active == True)

            tags = query.order_by(UserTag.priority.desc()).all()

            return [tag.to_dict() for tag in tags]

    def create_tag(
        self,
        tag_name: str,
        display_name: str,
        tag_category: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        priority: int = 0,
        is_auto: bool = False,
        rules: Optional[Dict[str, Any]] = None,
    ) -> UserTag:
        """
        创建自定义标签

        Args:
            tag_name: 标签名称（唯一）
            display_name: 显示名称
            tag_category: 标签分类
            description: 描述
            color: 颜色
            icon: 图标
            priority: 优先级
            is_auto: 是否自动打标
            rules: 自动打标规则

        Returns:
            创建的标签对象
        """
        tag = UserTag(
            tag_id=f"tag_{uuid.uuid4().hex[:8]}",
            tag_name=tag_name,
            display_name=display_name,
            tag_category=tag_category,
            description=description,
            color=color,
            icon=icon,
            priority=priority,
            is_auto=is_auto,
            rules=rules,
            is_active=True,
        )

        with db_manager.get_session() as session:
            session.add(tag)
            session.commit()
            session.refresh(tag)

        return tag

    def update_tag(
        self,
        tag_id: str,
        **updates,
    ) -> bool:
        """
        更新标签

        Args:
            tag_id: 标签ID
            **updates: 更新字段

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            tag = session.query(UserTag).filter(
                UserTag.tag_id == tag_id
            ).first()

            if not tag:
                return False

            for key, value in updates.items():
                if hasattr(tag, key):
                    setattr(tag, key, value)

            tag.updated_at = datetime.utcnow()
            session.commit()

        return True

    def delete_tag(self, tag_id: str) -> bool:
        """
        删除标签

        Args:
            tag_id: 标签ID

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            tag = session.query(UserTag).filter(
                UserTag.tag_id == tag_id
            ).first()

            if not tag:
                return False

            # 删除标签（软删除：设为不活跃）
            tag.is_active = False
            tag.updated_at = datetime.utcnow()
            session.commit()

        return True

    def apply_auto_tags(self) -> Dict[str, Any]:
        """
        应用自动标签规则

        Returns:
            应用结果统计
        """
        stats = {
            "total_users": 0,
            "tags_applied": 0,
            "tags_removed": 0,
            "start_time": datetime.utcnow().isoformat(),
        }

        with db_manager.get_session() as session:
            # 获取所有自动标签
            auto_tags = session.query(UserTag).filter(
                UserTag.is_auto == True,
                UserTag.is_active == True,
            ).all()

            # 获取所有用户画像
            profiles = session.query(UserProfile).all()
            stats["total_users"] = len(profiles)

            for profile in profiles:
                profile_tags = set(t["tag"] for t in profile.get_behavior_tags())

                for tag in auto_tags:
                    should_have_tag = self._check_tag_rule(profile, tag.rules)
                    has_tag = tag.tag_name in profile_tags

                    if should_have_tag and not has_tag:
                        profile.add_tag(tag.tag_name, 1.0)
                        stats["tags_applied"] += 1
                    elif not should_have_tag and has_tag:
                        profile.remove_tag(tag.tag_name)
                        stats["tags_removed"] += 1

            session.commit()

        stats["end_time"] = datetime.utcnow().isoformat()
        return stats

    def _check_tag_rule(
        self,
        profile: UserProfile,
        rules: Optional[Dict[str, Any]],
    ) -> bool:
        """
        检查用户画像是否满足标签规则

        Args:
            profile: 用户画像
            rules: 标签规则

        Returns:
            是否满足
        """
        if not rules:
            return False

        rule_type = rules.get("type")

        if rule_type == "activity":
            return (profile.activity_score or 0) >= rules.get("min_score", 0)

        elif rule_type == "operations":
            total_ops = (
                (profile.query_count or 0) +
                (profile.create_count or 0) +
                (profile.export_count or 0)
            )
            return total_ops >= rules.get("min_count", 0)

        elif rule_type == "registration":
            days_since_created = (datetime.utcnow() - profile.created_at).days
            return days_since_created <= rules.get("max_days", 999)

        elif rule_type == "query":
            return (profile.query_count or 0) >= rules.get("min_count", 0)

        elif rule_type == "timing":
            peak_hours = profile.get_peak_hours()
            if not peak_hours:
                return False

            night_hours = sum(h["count"] for h in peak_hours if h["hour"] >= 18 or h["hour"] < 6)
            total_hours = sum(h["count"] for h in peak_hours)

            if "night_ratio_min" in rules:
                night_ratio = night_hours / max(total_hours, 1)
                if night_ratio >= rules["night_ratio_min"]:
                    return True

            if "morning_ratio_min" in rules:
                morning_hours = sum(h["count"] for h in peak_hours if 6 <= h["hour"] < 12)
                morning_ratio = morning_hours / max(total_hours, 1)
                if morning_ratio >= rules["morning_ratio_min"]:
                    return True

            return False

        elif rule_type == "anomaly":
            return profile.is_risk_user

        return False

    def manually_tag_user(
        self,
        user_id: str,
        tag_name: str,
        score: float = 1.0,
    ) -> bool:
        """
        手动给用户打标签

        Args:
            user_id: 用户ID
            tag_name: 标签名称
            score: 标签分数

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            profile = session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()

            if not profile:
                return False

            profile.add_tag(tag_name, score)
            session.commit()

        return True

    def remove_user_tag(
        self,
        user_id: str,
        tag_name: str,
    ) -> bool:
        """
        移除用户标签

        Args:
            user_id: 用户ID
            tag_name: 标签名称

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            profile = session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()

            if not profile:
                return False

            profile.remove_tag(tag_name)
            session.commit()

        return True

    def get_tagged_users(
        self,
        tag_name: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取拥有指定标签的用户列表

        Args:
            tag_name: 标签名称
            limit: 返回数量限制

        Returns:
            用户列表
        """
        with db_manager.get_session() as session:
            profiles = session.query(UserProfile).all()

            result = []
            for profile in profiles:
                tags = profile.get_behavior_tags()
                if any(t["tag"] == tag_name for t in tags):
                    result.append({
                        "user_id": profile.user_id,
                        "username": profile.username,
                        "activity_score": profile.activity_score,
                        "tag_score": next(t["score"] for t in tags if t["tag"] == tag_name),
                    })

                if len(result) >= limit:
                    break

            return result

    def get_user_tags(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        获取用户的所有标签

        Args:
            user_id: 用户ID

        Returns:
            标签列表
        """
        with db_manager.get_session() as session:
            profile = session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()

            if not profile:
                return []

            behavior_tags = profile.get_behavior_tags()
            tag_names = [t["tag"] for t in behavior_tags]

            # 获取标签详情
            tags = session.query(UserTag).filter(
                UserTag.tag_name.in_(tag_names),
                UserTag.is_active == True,
            ).all()

            tag_dict = {tag.tag_name: tag.to_dict() for tag in tags}

            # 合并分数
            result = []
            for bt in behavior_tags:
                if bt["tag"] in tag_dict:
                    result.append({
                        **tag_dict[bt["tag"]],
                        "score": bt["score"],
                        "assigned_at": bt.get("created_at"),
                    })

            return sorted(result, key=lambda x: x.get("priority", 0), reverse=True)


# 全局实例
_user_tagging: Optional[UserTagging] = None


def get_user_tagging() -> UserTagging:
    """获取用户标签管理器单例"""
    global _user_tagging
    if _user_tagging is None:
        _user_tagging = UserTagging()
    return _user_tagging
