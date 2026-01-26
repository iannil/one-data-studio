"""
OCR任务API路由
"""

import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import get_db
from models.ocr_task import OCRTask, TaskStatus, DocumentType, ExtractionType
from models.ocr_result import OCRResult, TableData
from services.document_parser import DocumentParser
from services.ocr_engine import OCREngine
from services.table_extractor import TableExtractor
from services.ai_extractor import AIExtractor
from services.validator import DataValidator

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化服务
document_parser = DocumentParser()
ocr_engine = OCREngine()
table_extractor = TableExtractor()
ai_extractor = AIExtractor()
data_validator = DataValidator()

# 临时文件目录
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/ocr")
os.makedirs(TEMP_DIR, exist_ok=True)


# Pydantic模型
class CreateOCRTaskRequest(BaseModel):
    """创建OCR任务请求"""
    extraction_type: str = Field(default="general", description="提取类型")
    template_id: Optional[str] = Field(None, description="使用的模板ID")
    extraction_config: Optional[dict] = Field(None, description="提取配置")


class OCRTaskResponse(BaseModel):
    """OCR任务响应"""
    id: str
    document_name: str
    document_type: str
    status: str
    progress: float
    created_at: str
    result_summary: Optional[dict] = None
    error_message: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int
    tasks: List[OCRTaskResponse]


class ExtractionResultResponse(BaseModel):
    """提取结果响应"""
    task_id: str
    structured_data: dict
    raw_text: Optional[str] = None
    tables: List[dict] = []
    confidence_score: float
    validation_issues: List[dict] = []


# 后台任务处理函数
async def process_ocr_task(task_id: str, db: Session):
    """后台处理OCR任务"""
    try:
        # 获取任务
        task = db.query(OCRTask).filter(OCRTask.id == task_id).first()
        if not task:
            logger.error(f"Task not found: {task_id}")
            return

        # 更新任务状态
        task.status = TaskStatus.PROCESSING.value
        task.started_at = datetime.now()
        task.progress = 10.0
        db.commit()

        # 解析文档
        logger.info(f"Parsing document for task {task_id}")
        parsed_doc = document_parser.parse(task.document_path)
        task.progress = 30.0
        db.commit()

        # OCR识别
        all_text = []
        all_tables = []
        page_results = []

        for i, page in enumerate(parsed_doc.get("pages", [])):
            page_num = page.get("number", i + 1)
            page_image = page.get("image")
            page_text = page.get("text", "")
            page_tables = page.get("tables", [])

            # 如果没有文本但有图片，进行OCR
            if not page_text and page_image is not None:
                ocr_result = ocr_engine.recognize(page_image)
                page_text = ocr_result.get("text", "")

            all_text.append(page_text)

            # 处理表格
            if page_tables:
                for table in page_tables:
                    normalized_table = table_extractor.normalize_table({
                        "index": len(all_tables),
                        "page": page_num,
                        "headers": table[0] if isinstance(table, list) and table else [],
                        "rows": table[1:] if isinstance(table, list) and len(table) > 1 else [],
                        "row_count": len(table) if isinstance(table, list) else 0,
                        "col_count": len(table[0]) if isinstance(table, list) and table else 0,
                    })
                    all_tables.append(normalized_table)

            # 创建页面结果记录
            result_id = str(uuid.uuid4())
            ocr_result = OCRResult(
                id=result_id,
                task_id=task_id,
                page_number=page_num,
                text_content=page_text,
                tables=page_tables[:10],  # 限制存储数量
                created_at=datetime.now()
            )
            db.add(ocr_result)
            page_results.append(ocr_result)

            # 更新进度
            progress = 30 + (50 * (i + 1) / len(parsed_doc.get("pages", [])))
            task.progress = progress

        db.commit()

        # 合并所有文本
        full_text = "\n\n".join(all_text)
        task.raw_text = full_text[:10000]  # 限制存储长度

        # AI信息提取
        structured_data = {}
        confidence_score = 0.8
        validation_issues = []

        if task.extraction_type != ExtractionType.GENERAL.value:
            # 获取模板
            template = None
            if task.template_id:
                from models.extraction_rule import ExtractionTemplate
                template = db.query(ExtractionTemplate).filter(
                    ExtractionTemplate.id == task.template_id
                ).first()

            if template:
                extraction_rules = template.extraction_config or template.extraction_rules
            else:
                extraction_rules = task.extraction_config

            # 调用AI提取
            if extraction_rules:
                if task.extraction_type == ExtractionType.INVOICE.value:
                    extraction_result = ai_extractor.extract_invoice(full_text)
                elif task.extraction_type == ExtractionType.CONTRACT.value:
                    extraction_result = ai_extractor.extract_contract(full_text)
                elif task.extraction_type == ExtractionType.REPORT.value:
                    extraction_result = ai_extractor.extract_report(full_text)
                else:
                    extraction_result = ai_extractor.extract_with_template(
                        full_text, extraction_rules
                    )

                structured_data = extraction_result.get("extracted", {})
                confidence_score = extraction_result.get("confidence", 0.8)
                validation_issues = extraction_result.get("missing_fields", [])

        # 数据验证
        if structured_data:
            is_valid, issues, overall_confidence = data_validator.validate_extraction_result(
                structured_data, extraction_rules or {}
            )
            validation_issues.extend(issues)
            confidence_score = overall_confidence

        # 保存表格数据
        for table_data in all_tables[:20]:  # 限制存储数量
            table_record = TableData(
                id=str(uuid.uuid4()),
                task_id=task_id,
                table_index=table_data.get("index", 0),
                page_number=table_data.get("page", 1),
                row_count=table_data.get("row_count", 0),
                col_count=table_data.get("col_count", 0),
                headers=table_data.get("headers", []),
                rows=table_data.get("rows", []),
                confidence=table_data.get("confidence", 0.0)
            )
            db.add(table_record)

        # 更新任务结果
        task.structured_data = structured_data
        task.confidence_score = confidence_score
        task.result_summary = {
            "pages_processed": len(parsed_doc.get("pages", [])),
            "tables_found": len(all_tables),
            "text_length": len(full_text),
            "fields_extracted": len(structured_data),
            "validation_issues": len(validation_issues)
        }
        task.status = TaskStatus.COMPLETED.value
        task.progress = 100.0
        task.completed_at = datetime.now()

        # 更新模板使用统计
        if task.template_id:
            from models.extraction_rule import ExtractionTemplate
            template = db.query(ExtractionTemplate).filter(
                ExtractionTemplate.id == task.template_id
            ).first()
            if template:
                template.usage_count = (template.usage_count or 0) + 1
                template.last_used_at = datetime.now()

        db.commit()

        logger.info(f"OCR task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Error processing OCR task {task_id}: {e}", exc_info=True)

        # 更新任务状态为失败
        try:
            task = db.query(OCRTask).filter(OCRTask.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED.value
                task.error_message = str(e)
                task.progress = 0.0
                db.commit()
        except Exception as commit_error:
            logger.error(f"Error updating failed task status: {commit_error}")


# API端点
@router.post("/tasks", response_model=OCRTaskResponse)
async def create_ocr_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    extraction_type: str = Query(default="general", description="提取类型"),
    template_id: Optional[str] = Query(None, description="模板ID"),
    tenant_id: str = Query(default="default", description="租户ID"),
    user_id: str = Query(default="system", description="用户ID"),
    db: Session = Depends(get_db)
):
    """创建OCR任务"""
    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 保存上传的文件
    file_ext = os.path.splitext(file.filename)[1]
    temp_path = os.path.join(TEMP_DIR, f"{task_id}{file_ext}")

    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 检测文档类型
    doc_format = document_parser.detect_format(file.filename, content)

    # 创建任务记录
    task = OCRTask(
        id=task_id,
        tenant_id=tenant_id,
        user_id=user_id,
        document_name=file.filename,
        document_type=doc_format.value,
        document_path=temp_path,
        file_size=len(content),
        extraction_type=extraction_type,
        template_id=template_id,
        status=TaskStatus.PENDING.value,
        progress=0.0
    )

    db.add(task)
    db.commit()

    # 添加后台任务
    background_tasks.add_task(process_ocr_task, task_id, db)

    return OCRTaskResponse(
        id=task.id,
        document_name=task.document_name,
        document_type=task.document_type,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at.isoformat()
    )


@router.get("/tasks", response_model=TaskListResponse)
async def list_ocr_tasks(
    tenant_id: str = Query(default="default", description="租户ID"),
    status: Optional[str] = Query(None, description="状态筛选"),
    extraction_type: Optional[str] = Query(None, description="提取类型筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取OCR任务列表"""
    query = db.query(OCRTask).filter(OCRTask.tenant_id == tenant_id)

    if status:
        query = query.filter(OCRTask.status == status)
    if extraction_type:
        query = query.filter(OCRTask.extraction_type == extraction_type)

    total = query.count()
    tasks = query.order_by(OCRTask.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return TaskListResponse(
        total=total,
        tasks=[
            OCRTaskResponse(
                id=t.id,
                document_name=t.document_name,
                document_type=t.document_type,
                status=t.status,
                progress=t.progress,
                created_at=t.created_at.isoformat(),
                result_summary=t.result_summary,
                error_message=t.error_message
            )
            for t in tasks
        ]
    )


@router.get("/tasks/{task_id}", response_model=OCRTaskResponse)
async def get_ocr_task(task_id: str, db: Session = Depends(get_db)):
    """获取OCR任务详情"""
    task = db.query(OCRTask).filter(OCRTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return OCRTaskResponse(
        id=task.id,
        document_name=task.document_name,
        document_type=task.document_type,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at.isoformat(),
        result_summary=task.result_summary,
        error_message=task.error_message
    )


@router.get("/tasks/{task_id}/result", response_model=ExtractionResultResponse)
async def get_task_result(task_id: str, db: Session = Depends(get_db)):
    """获取OCR任务结果"""
    task = db.query(OCRTask).filter(OCRTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed, current status: {task.status}"
        )

    # 获取表格数据
    tables = db.query(TableData).filter(TableData.task_id == task_id).all()

    return ExtractionResultResponse(
        task_id=task.id,
        structured_data=task.structured_data or {},
        raw_text=task.raw_text,
        tables=[t.to_dict() for t in tables],
        confidence_score=task.confidence_score or 0.0,
        validation_issues=task.result_summary.get("validation_issues", []) if task.result_summary else []
    )


@router.post("/tasks/{task_id}/verify")
async def verify_task_result(
    task_id: str,
    corrections: dict,
    verified_by: str,
    db: Session = Depends(get_db)
):
    """验证和校正OCR结果"""
    task = db.query(OCRTask).filter(OCRTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 应用校正
    task.structured_data = {**(task.structured_data or {}), **corrections}
    task.is_verified = True
    task.verified_by = verified_by
    task.verified_at = datetime.now()

    db.commit()

    return {"message": "Verification completed", "task_id": task_id}


@router.delete("/tasks/{task_id}")
async def delete_ocr_task(task_id: str, db: Session = Depends(get_db)):
    """删除OCR任务"""
    task = db.query(OCRTask).filter(OCRTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 删除文件
    if task.document_path and os.path.exists(task.document_path):
        try:
            os.remove(task.document_path)
        except Exception as e:
            logger.warning(f"Failed to delete file {task.document_path}: {e}")

    # 删除数据库记录（级联删除相关记录）
    db.delete(task)
    db.commit()

    return {"message": "Task deleted successfully"}
