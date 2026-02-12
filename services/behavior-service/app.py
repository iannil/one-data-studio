"""
用户行为管理服务
采集用户行为并生成画像，提供行为审计功能
"""

import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Text,
    DateTime,
    Float,
    JSON,
    Boolean,
    Index,
)
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import BIGINT
import redis
import os
import uuid

from models.base import engine, SessionLocal, get_db
from api.behaviors import router as behaviors_router
from api.profiles import router as profiles_router
from api.audit import router as audit_router
from services.behavior_collector import BehaviorCollector
from services.behavior_analyzer import (
    BehaviorMetricsAnalyzer,
)  # renamed from BehaviorAnalyzer
from services.profile_builder import ProfileBuilder
from services.anomaly_detector import AnomalyDetector

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Redis配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("用户行为管理服务启动中...")

    # 创建数据库表
    from models.base import Base

    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")

    # 初始化分析器
    analyzer = BehaviorAnalyzer()
    profile_builder = ProfileBuilder()
    logger.info("行为分析器初始化完成")

    yield

    logger.info("用户行为管理服务关闭中...")
    redis_client.close()
    logger.info("服务已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="用户行为管理服务",
    description="采集用户行为并生成画像，提供行为审计功能",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(behaviors_router, prefix="/api/v1/behaviors", tags=["行为采集"])
app.include_router(profiles_router, prefix="/api/v1/profiles", tags=["用户画像"])
app.include_router(audit_router, prefix="/api/v1/audit", tags=["行为审计"])


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "用户行为管理服务",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health_check():
    """健康检查详情"""
    return {"status": "healthy", "database": check_database(), "redis": check_redis()}


def check_database():
    """检查数据库连接"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception:
        return False


def check_redis():
    """检查Redis连接"""
    try:
        return redis_client.ping()
    except Exception:
        return False


# 中间件：记录API调用
@app.middleware("http")
async def log_requests(request, call_next):
    """记录所有API请求"""
    import time

    start_time = time.time()

    # 获取用户信息（从header或token）
    user_id = request.headers.get("X-User-Id", "anonymous")
    tenant_id = request.headers.get("X-Tenant-Id", "default")

    response = await call_next(request)

    # 记录API调用行为
    process_time = time.time() - start_time
    try:
        collector = BehaviorCollector()
        collector.collect_api_call(
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": process_time,
                "user_agent": request.headers.get("user-agent"),
                "ip": request.client.host if request.client else None,
            }
        )
    except Exception as e:
        logger.error(f"Failed to log API call: {e}")

    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8008, reload=True, log_level="info")
