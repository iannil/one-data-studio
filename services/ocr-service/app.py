"""
OCR文档识别服务
支持非结构化文档（PDF、Word、Excel、图片、扫描件）的智能识别
"""

import logging
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import redis
import os

from services.ocr_engine import OCREngine
from services.document_parser import DocumentParser
from services.table_extractor import TableExtractor
from services.ai_extractor import AIExtractor
from services.validator import DataValidator
from services.metrics import metrics, get_metrics_summary
from api.ocr_tasks import router as ocr_tasks_router
from api.templates import router as templates_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/ocr_service"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("OCR服务启动中...")
    # 创建数据库表
    from models.base import Base
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")

    # 初始化OCR引擎
    ocr_engine = OCREngine()
    if ocr_engine.is_ready():
        logger.info("OCR引擎初始化完成")
    else:
        logger.warning("OCR引擎初始化失败，部分功能可能不可用")

    yield

    # 关闭时清理
    logger.info("OCR服务关闭中...")
    redis_client.close()
    logger.info("OCR服务已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="OCR文档识别服务",
    description="支持非结构化文档（PDF、Word、Excel、图片、扫描件）的智能识别",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(ocr_tasks_router, prefix="/api/v1/ocr", tags=["OCR任务"])
app.include_router(templates_router, prefix="/api/v1/ocr", tags=["提取模板"])


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "OCR文档识别服务",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """健康检查详情"""
    ocr_engine = OCREngine()
    return {
        "status": "healthy",
        "ocr_engine": ocr_engine.is_ready(),
        "database": check_database(),
        "redis": check_redis()
    }


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


@app.get("/metrics")
async def get_metrics():
    """Prometheus格式指标"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=metrics.export_prometheus(),
        media_type="text/plain"
    )


@app.get("/api/v1/metrics")
async def get_metrics_json():
    """JSON格式指标"""
    return get_metrics_summary()


@app.get("/api/v1/metrics/raw")
async def get_metrics_raw():
    """原始指标数据"""
    return metrics.export_json()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8007,
        reload=True,
        log_level="info"
    )
