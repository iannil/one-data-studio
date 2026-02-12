"""
用户分群分析服务
Phase 1.3: 基于行为特征对用户进行分群
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database import db_manager
from models.user_profile import UserProfile, UserSegment, generate_segment_id
from behavior_analyzer import (
    get_user_profile_analyzer,
)  # renamed from get_behavior_analyzer

logger = logging.getLogger(__name__)


# 预定义分群配置
PREDEFINED_SEGMENTS = {
    "active": {
        "segment_name": "活跃用户",
        "segment_type": "active",
        "description": "高活跃度用户，频繁使用平台",
        "criteria": {
            "activity_score_min": 70,
            "login_days_min": 7,
        },
        "strategy": "提供高级功能试用，邀请参与产品内测",
    },
    "exploratory": {
        "segment_name": "探索型用户",
        "segment_type": "exploratory",
        "description": "喜欢尝试新功能，使用多种模块",
        "criteria": {
            "module_diversity_min": 5,
        },
        "strategy": "优先推送新功能介绍，收集反馈意见",
    },
    "conservative": {
        "segment_name": "保守型用户",
        "segment_type": "conservative",
        "description": "使用少数核心功能，操作频率低",
        "criteria": {
            "activity_score_max": 30,
            "module_diversity_max": 2,
        },
        "strategy": "提供基础教程，引导探索更多功能",
    },
    "power": {
        "segment_name": "专家用户",
        "segment_type": "power",
        "description": "深度用户，操作频率高",
        "criteria": {
            "query_count_min": 100,
            "create_count_min": 10,
        },
        "strategy": "邀请成为社区专家，分享使用经验",
    },
    "new": {
        "segment_name": "新用户",
        "segment_type": "new",
        "description": "最近注册的用户",
        "criteria": {
            "days_since_first_login_max": 7,
        },
        "strategy": "提供新手引导，帮助快速上手",
    },
    "churned": {
        "segment_name": "流失用户",
        "segment_type": "churned",
        "description": "长时间未登录的用户",
        "criteria": {
            "days_since_last_login_min": 30,
        },
        "strategy": "发送召回邮件，了解流失原因",
    },
}


class UserSegmentation:
    """用户分群管理器"""

    def __init__(self):
        self.analyzer = get_user_profile_analyzer()
        self.predefined_segments = PREDEFINED_SEGMENTS

    def initialize_segments(self) -> int:
        """
        初始化预定义分群

        Returns:
            创建的分群数量
        """
        count = 0
        with db_manager.get_session() as session:
            for key, config in self.predefined_segments.items():
                # 检查是否已存在
                existing = (
                    session.query(UserSegment)
                    .filter(UserSegment.segment_type == config["segment_type"])
                    .first()
                )

                if not existing:
                    segment = UserSegment(
                        segment_id=generate_segment_id(),
                        segment_name=config["segment_name"],
                        segment_type=config["segment_type"],
                        description=config["description"],
                        criteria=config["criteria"],
                        strategy=config["strategy"],
                        is_system=True,
                        is_active=True,
                    )
                    session.add(segment)
                    count += 1

            session.commit()

        logger.info(f"Initialized {count} predefined segments")
        return count

    def rebuild_segments(self, segment_type: Optional[str] = None) -> Dict[str, Any]:
        """
        重建用户分群

        Args:
            segment_type: 分群类型（为空则重建所有）

        Returns:
            重建结果统计
        """
        stats = {
            "total_users": 0,
            "segmented_users": 0,
            "segments_updated": 0,
            "start_time": datetime.utcnow().isoformat(),
        }

        with db_manager.get_session() as session:
            # 获取需要重建的分群
            query = session.query(UserSegment).filter(UserSegment.is_active == True)
            if segment_type:
                query = query.filter(UserSegment.segment_type == segment_type)

            segments = query.all()

            # 清空现有分群用户关联
            for segment in segments:
                session.query(UserProfile).filter(
                    UserProfile.segment_id == segment.segment_id
                ).update({"segment_id": None})

            # 获取所有用户画像
            profiles = session.query(UserProfile).all()
            stats["total_users"] = len(profiles)

            # 为每个用户分配分群
            for profile in profiles:
                matched_segment = self._match_segment(profile, segments)
                if matched_segment:
                    profile.segment_id = matched_segment.segment_id
                    stats["segmented_users"] += 1

            # 更新分群统计
            for segment in segments:
                user_count = (
                    session.query(UserProfile)
                    .filter(UserProfile.segment_id == segment.segment_id)
                    .count()
                )
                segment.user_count = user_count
                segment.last_rebuilt_at = datetime.utcnow()

                # 生成分群特征
                segment.characteristics = self._generate_segment_characteristics(
                    segment.segment_id, session
                )

                stats["segments_updated"] += 1

            session.commit()

        stats["end_time"] = datetime.utcnow().isoformat()
        return stats

    def _match_segment(
        self,
        profile: UserProfile,
        segments: List[UserSegment],
    ) -> Optional[UserSegment]:
        """
        匹配用户到分群

        Args:
            profile: 用户画像
            segments: 分群列表

        Returns:
            匹配的分群或None
        """
        for segment in segments:
            criteria = segment.criteria or {}

            # 检查所有条件
            if self._check_criteria(profile, criteria):
                return segment

        return None

    def _check_criteria(self, profile: UserProfile, criteria: Dict[str, Any]) -> bool:
        """
        检查用户画像是否满足分群条件

        Args:
            profile: 用户画像
            criteria: 分群条件

        Returns:
            是否满足
        """
        # 活跃度条件
        if "activity_score_min" in criteria:
            if (profile.activity_score or 0) < criteria["activity_score_min"]:
                return False

        if "activity_score_max" in criteria:
            if (profile.activity_score or 0) > criteria["activity_score_max"]:
                return False

        # 登录天数条件
        if "login_days_min" in criteria:
            if (profile.login_days or 0) < criteria["login_days_min"]:
                return False

        # 操作次数条件
        if "query_count_min" in criteria:
            if (profile.query_count or 0) < criteria["query_count_min"]:
                return False

        if "create_count_min" in criteria:
            if (profile.create_count or 0) < criteria["create_count_min"]:
                return False

        # 模块多样性条件
        module_usage = profile.get_module_usage()
        module_diversity = len(module_usage)

        if "module_diversity_min" in criteria:
            if module_diversity < criteria["module_diversity_min"]:
                return False

        if "module_diversity_max" in criteria:
            if module_diversity > criteria["module_diversity_max"]:
                return False

        # 时间条件
        if profile.last_login_at:
            days_since_last_login = (datetime.utcnow() - profile.last_login_at).days

            if "days_since_last_login_min" in criteria:
                if days_since_last_login < criteria["days_since_last_login_min"]:
                    return False

            if "days_since_first_login_max" in criteria:
                # 简化处理：使用创建时间作为首次登录时间
                days_since_created = (datetime.utcnow() - profile.created_at).days
                if days_since_created > criteria["days_since_first_login_max"]:
                    return False

        return True

    def _generate_segment_characteristics(
        self,
        segment_id: str,
        session: Session,
    ) -> Dict[str, Any]:
        """
        生成分群特征统计

        Args:
            segment_id: 分群ID
            session: 数据库会话

        Returns:
            分群特征字典
        """
        profiles = (
            session.query(UserProfile)
            .filter(UserProfile.segment_id == segment_id)
            .all()
        )

        if not profiles:
            return {}

        # 计算平均特征
        avg_activity = sum(p.activity_score or 0 for p in profiles) / len(profiles)
        avg_login_days = sum(p.login_days or 0 for p in profiles) / len(profiles)
        avg_query_count = sum(p.query_count or 0 for p in profiles) / len(profiles)

        # 统计常见标签
        all_tags = []
        for p in profiles:
            all_tags.extend([t["tag"] for t in p.get_behavior_tags()])

        from collections import Counter

        common_tags = dict(Counter(all_tags).most_common(5))

        # 统计常见模块偏好
        all_modules = []
        for p in profiles:
            all_modules.extend(list(p.get_module_usage().keys()))

        common_modules = dict(Counter(all_modules).most_common(5))

        return {
            "avg_activity": round(avg_activity, 2),
            "avg_login_days": round(avg_login_days, 2),
            "avg_query_count": round(avg_query_count, 2),
            "common_tags": common_tags,
            "common_modules": common_modules,
            "user_count": len(profiles),
        }

    def get_segments(
        self,
        segment_type: Optional[str] = None,
        include_users: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        获取分群列表

        Args:
            segment_type: 分群类型过滤
            include_users: 是否包含用户列表

        Returns:
            分群列表
        """
        with db_manager.get_session() as session:
            query = session.query(UserSegment).filter(UserSegment.is_active == True)

            if segment_type:
                query = query.filter(UserSegment.segment_type == segment_type)

            segments = query.all()

            result = []
            for segment in segments:
                seg_dict = segment.to_dict()

                if include_users:
                    users = (
                        session.query(UserProfile)
                        .filter(UserProfile.segment_id == segment.segment_id)
                        .limit(100)
                        .all()
                    )

                    seg_dict["users"] = [
                        {
                            "user_id": u.user_id,
                            "username": u.username,
                            "activity_score": u.activity_score,
                        }
                        for u in users
                    ]

                result.append(seg_dict)

            return result

    def create_segment(
        self,
        segment_name: str,
        segment_type: str,
        description: Optional[str] = None,
        criteria: Optional[Dict[str, Any]] = None,
        strategy: Optional[str] = None,
    ) -> UserSegment:
        """
        创建自定义分群

        Args:
            segment_name: 分群名称
            segment_type: 分群类型
            description: 描述
            criteria: 分群条件
            strategy: 运营策略

        Returns:
            创建的分群对象
        """
        segment = UserSegment(
            segment_id=generate_segment_id(),
            segment_name=segment_name,
            segment_type=segment_type,
            description=description,
            criteria=criteria,
            strategy=strategy,
            is_system=False,
            is_active=True,
        )

        with db_manager.get_session() as session:
            session.add(segment)
            session.commit()
            session.refresh(segment)

        return segment

    def update_segment(
        self,
        segment_id: str,
        **updates,
    ) -> bool:
        """
        更新分群配置

        Args:
            segment_id: 分群ID
            **updates: 更新字段

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            segment = (
                session.query(UserSegment)
                .filter(UserSegment.segment_id == segment_id)
                .first()
            )

            if not segment:
                return False

            if segment.is_system:
                # 系统分群不允许修改核心属性
                allowed_fields = {"strategy", "description"}
                for key in list(updates.keys()):
                    if key not in allowed_fields:
                        updates.pop(key)

            for key, value in updates.items():
                if hasattr(segment, key):
                    setattr(segment, key, value)

            segment.updated_at = datetime.utcnow()
            session.commit()

        return True

    def delete_segment(self, segment_id: str) -> bool:
        """
        删除分群

        Args:
            segment_id: 分群ID

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            segment = (
                session.query(UserSegment)
                .filter(UserSegment.segment_id == segment_id)
                .first()
            )

            if not segment:
                return False

            if segment.is_system:
                # 系统分群只做停用处理
                segment.is_active = False
            else:
                # 清空用户关联
                session.query(UserProfile).filter(
                    UserProfile.segment_id == segment_id
                ).update({"segment_id": None})
                session.delete(segment)

            session.commit()

        return True


# 全局实例
_segmentation: Optional[UserSegmentation] = None


def get_user_segmentation() -> UserSegmentation:
    """获取用户分群管理器单例"""
    global _segmentation
    if _segmentation is None:
        _segmentation = UserSegmentation()
    return _segmentation
