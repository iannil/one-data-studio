"""
用户画像API路由
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import get_db
from models.user_profile import UserProfile
from services.profile_builder import ProfileBuilder
from services.behavior_analyzer import BehaviorAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化服务
profile_builder = ProfileBuilder()
analyzer = BehaviorAnalyzer()


@router.get("/user/{user_id}")
async def get_user_profile(
    user_id: str,
    tenant_id: str = Query("default"),
    refresh: bool = Query(False, description="是否刷新画像"),
    db: Session = Depends(get_db)
):
    """获取用户画像"""
    if refresh:
        profile = profile_builder.build_user_profile(db, user_id, tenant_id)
    else:
        profile = profile_builder.get_profile(db, user_id, tenant_id)

    if not profile:
        # 自动构建画像
        profile = profile_builder.build_user_profile(db, user_id, tenant_id)

    return profile.to_dict()


@router.post("/user/{user_id}/refresh")
async def refresh_user_profile(
    user_id: str,
    tenant_id: str = Body("default"),
    user_info: dict = Body(None),
    db: Session = Depends(get_db)
):
    """刷新用户画像"""
    profile = profile_builder.build_user_profile(db, user_id, tenant_id, user_info)
    return {
        "success": True,
        "profile": profile.to_dict()
    }


@router.get("/segment/{segment_tag}")
async def get_profiles_by_segment(
    segment_tag: str,
    tenant_id: str = Query("default"),
    db: Session = Depends(get_db)
):
    """根据分群标签获取用户列表"""
    profiles = profile_builder.get_profiles_by_segment(db, tenant_id, segment_tag)
    return {
        "segment": segment_tag,
        "count": len(profiles),
        "users": [p.to_dict() for p in profiles]
    }


@router.get("/segments")
async def list_segments(
    tenant_id: str = Query("default"),
    db: Session = Depends(get_db)
):
    """列出所有分群标签"""
    profiles = db.query(UserProfile).filter(
        UserProfile.tenant_id == tenant_id
    ).all()

    segment_counts = {}
    for profile in profiles:
        tags = profile.segment_tags or []
        for tag in tags:
            segment_counts[tag] = segment_counts.get(tag, 0) + 1

    return {
        "segments": [
            {"tag": tag, "count": count}
            for tag, count in sorted(segment_counts.items(), key=lambda x: x[1], reverse=True)
        ]
    }


@router.get("/user/{user_id}/similar")
async def get_similar_users(
    user_id: str,
    tenant_id: str = Query("default"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取相似用户"""
    similar = profile_builder.get_similar_users(db, user_id, tenant_id, limit)
    return {
        "user_id": user_id,
        "similar_users": similar
    }


@router.get("/activity/user/{user_id}")
async def get_user_activity(
    user_id: str,
    tenant_id: str = Query("default"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """获取用户活跃度分析"""
    activity = analyzer.analyze_user_activity(db, user_id, tenant_id, days)
    return activity


@router.get("/activity/modules")
async def get_module_usage(
    tenant_id: str = Query("default"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """获取功能模块使用情况"""
    modules = analyzer.analyze_module_usage(db, tenant_id, days)
    return {"modules": modules}


@router.get("/activity/users")
async def get_active_users(
    tenant_id: str = Query("default"),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """获取活跃用户列表"""
    users = analyzer.get_active_users(db, tenant_id, days)
    return {"users": users}


@router.get("/activity/hourly")
async def get_hourly_activity(
    tenant_id: str = Query("default"),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """获取按小时统计的活动量"""
    hourly = analyzer.get_hourly_activity(db, tenant_id, days)
    return {"hourly_data": hourly}


@router.post("/funnel")
async def analyze_funnel(
    steps: List[str] = Body(...),
    tenant_id: str = Body("default"),
    days: int = Body(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """分析行为漏斗"""
    funnel = analyzer.get_behavior_funnel(db, tenant_id, steps, days)
    return funnel


@router.get("/retention")
async def get_retention(
    tenant_id: str = Query("default"),
    cohort_days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """计算用户留存率"""
    retention = analyzer.calculate_retention(db, tenant_id, cohort_days)
    return {"retention_data": retention}


@router.post("/refresh-all")
async def refresh_all_profiles(
    tenant_id: str = Body("default"),
    batch_size: int = Body(100),
    db: Session = Depends(get_db)
):
    """刷新所有用户画像"""
    count = profile_builder.refresh_all_profiles(db, tenant_id, batch_size)
    return {
        "success": True,
        "refreshed_count": count
    }
