"""
OCR任务API路由
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.ocr_task import OCRTask, TaskStatus, DocumentType, ExtractionType
from models.ocr_result import OCRResult, TableData
from services.document_parser import DocumentParser
from services.ocr_engine import OCREngine
from services.table_extractor import TableExtractor
from services.ai_extractor import AIExtractor
from services.validator import DataValidator
from services.layout_analyzer import LayoutAnalyzer
from services.cross_field_validator import CrossFieldValidator
from services.multi_page_processor import MultiPageProcessor

# 导入新的 ExtractionType 值以供前端使用
EXTRACTION_TYPES = {
    'invoice': '发票',
    'contract': '合同',
    'purchase_order': '采购订单',
    'delivery_note': '送货单',
    'quotation': '报价单',
    'receipt': '收据',
    'report': '报告',
    'table': '表格',
    'general': '通用文档'
}

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化服务
document_parser = DocumentParser()
ocr_engine = OCREngine()
table_extractor = TableExtractor()
ai_extractor = AIExtractor()
data_validator = DataValidator()
layout_analyzer = LayoutAnalyzer()
cross_field_validator = CrossFieldValidator()
multi_page_processor = MultiPageProcessor()

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
                elif task.extraction_type == ExtractionType.PURCHASE_ORDER.value:
                    extraction_result = ai_extractor.extract_purchase_order(full_text)
                elif task.extraction_type == ExtractionType.DELIVERY_NOTE.value:
                    extraction_result = ai_extractor.extract_delivery_note(full_text)
                elif task.extraction_type == ExtractionType.QUOTATION.value:
                    extraction_result = ai_extractor.extract_quotation(full_text)
                elif task.extraction_type == ExtractionType.RECEIPT.value:
                    extraction_result = ai_extractor.extract_receipt(full_text)
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


# ============================================
# 新增API端点
# ============================================

class BatchTaskResponse(BaseModel):
    """批量任务响应"""
    batch_id: str
    total_files: int
    tasks: List[str]
    status: str


@router.post("/tasks/batch", response_model=BatchTaskResponse)
async def create_batch_ocr_tasks(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    extraction_type: str = Query(default="general", description="提取类型"),
    template_id: Optional[str] = Query(None, description="模板ID"),
    tenant_id: str = Query(default="default", description="租户ID"),
    user_id: str = Query(default="system", description="用户ID"),
    db: Session = Depends(get_db)
):
    """批量创建OCR任务"""
    batch_id = str(uuid.uuid4())
    task_ids = []

    for file in files:
        # 为每个文件创建任务
        task_id = str(uuid.uuid4())

        file_ext = os.path.splitext(file.filename)[1]
        temp_path = os.path.join(TEMP_DIR, f"{task_id}{file_ext}")

        # 保存文件
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
        task_ids.append(task_id)

        # 添加后台任务
        background_tasks.add_task(process_ocr_task, task_id, db)

    db.commit()

    return BatchTaskResponse(
        batch_id=batch_id,
        total_files=len(files),
        tasks=task_ids,
        status="pending"
    )


class DocumentTypeDetectionResponse(BaseModel):
    """文档类型识别响应"""
    detected_type: str
    confidence: float
    suggested_templates: List[str]
    metadata: Dict[str, Any]


@router.post("/detect-type", response_model=DocumentTypeDetectionResponse)
async def detect_document_type(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """自动识别文档类型"""
    content = await file.read()

    # 保存临时文件
    temp_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    temp_path = os.path.join(TEMP_DIR, f"{temp_id}{file_ext}")

    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        # 解析文档
        parsed_doc = document_parser.parse(temp_path)

        # 合并所有文本
        all_text = []
        for page in parsed_doc.get("pages", []):
            all_text.append(page.get("text", ""))

        full_text = "\n\n".join(all_text)

        # 基于关键词识别文档类型
        detected_type, confidence = _detect_document_type_by_keywords(full_text)

        # 获取建议的模板
        suggested_templates = _get_suggested_templates(detected_type, db)

        return DocumentTypeDetectionResponse(
            detected_type=detected_type,
            confidence=confidence,
            suggested_templates=suggested_templates,
            metadata={
                "file_name": file.filename,
                "file_size": len(content),
                "page_count": len(parsed_doc.get("pages", [])),
                "text_length": len(full_text)
            }
        )

    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _detect_document_type_by_keywords(text: str) -> tuple:
    """基于关键词识别文档类型"""
    # 文档类型关键词映射
    type_keywords = {
        "invoice": ["发票", "增值税", "发票号码", "发票代码", "价税合计", "购买方", "销售方"],
        "contract": ["合同", "协议", "甲方", "乙方", "签订日期", "合同金额"],
        "purchase_order": ["订单", "采购单", "供应商", "采购方", "交货日期"],
        "delivery_note": ["送货单", "收货单位", "送货日期", "实收数量", "验收人"],
        "quotation": ["报价单", "报价日期", "报价有效期", "客户"],
        "receipt": ["收据", "收款", "付款", "收据编号", "收款单位"]
    }

    # 计算每种类型的匹配分数
    scores = {}
    for doc_type, keywords in type_keywords.items():
        score = sum(1 for kw in keywords if kw in text)
        scores[doc_type] = score

    # 找出最高分的类型
    max_score = max(scores.values())
    if max_score == 0:
        return "general", 0.0

    detected_type = max(scores, key=scores.get)
    confidence = min(max_score / 5.0, 1.0)  # 最多5个关键词匹配就是100%

    return detected_type, confidence


def _get_suggested_templates(doc_type: str, db: Session) -> List[str]:
    """获取建议的模板"""
    try:
        from models.extraction_rule import ExtractionTemplate

        templates = db.query(ExtractionTemplate).filter(
            ExtractionTemplate.template_type == doc_type,
            ExtractionTemplate.is_active == True
        ).limit(3).all()

        return [t.id for t in templates]
    except Exception:
        return []


class EnhancedExtractionResultResponse(BaseModel):
    """增强的提取结果响应"""
    task_id: str
    structured_data: dict
    raw_text: Optional[str] = None
    tables: List[dict] = []
    confidence_score: float
    validation_issues: List[dict] = []
    cross_field_validation: Dict[str, Any] = {}
    layout_info: Dict[str, Any] = {}
    completeness: Dict[str, Any] = {}


@router.get("/tasks/{task_id}/result/enhanced", response_model=EnhancedExtractionResultResponse)
async def get_task_result_enhanced(
    task_id: str,
    include_validation: bool = Query(True, description="是否包含校验结果"),
    include_layout: bool = Query(True, description="是否包含布局信息"),
    db: Session = Depends(get_db)
):
    """获取OCR任务增强结果（包含跨字段校验和布局分析）"""
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

    # 获取模板
    template = None
    if task.template_id:
        from models.extraction_rule import ExtractionTemplate
        template = db.query(ExtractionTemplate).filter(
            ExtractionTemplate.id == task.template_id
        ).first()

    # 准备响应数据
    structured_data = task.structured_data or {}
    validation_issues = task.result_summary.get("validation_issues", []) if task.result_summary else []
    cross_field_validation = {}
    layout_info = {}
    completeness = {}

    # 跨字段校验
    if include_validation and template:
        template_config = template.extraction_rules or {}
        validation_result = cross_field_validator.validate(structured_data, template_config)
        cross_field_validation = validation_result

    # 布局分析
    if include_layout:
        layout_info = {
            "signature_regions": [],
            "seal_regions": [],
            "has_signatures": False,
            "has_seals": False
        }

        # 从原始结果中获取布局信息
        for table_data in tables:
            if hasattr(table_data, 'layout_info') and table_data.layout_info:
                layout_info.update(table_data.layout_info)

    # 完整性检查
    if template:
        completeness = cross_field_validator.validate_template_completeness(
            structured_data, template.extraction_rules or {}
        )

    return EnhancedExtractionResultResponse(
        task_id=task.id,
        structured_data=structured_data,
        raw_text=task.raw_text,
        tables=[t.to_dict() for t in tables],
        confidence_score=task.confidence_score or 0.0,
        validation_issues=validation_issues,
        cross_field_validation=cross_field_validation,
        layout_info=layout_info,
        completeness=completeness
    )


class TemplatePreviewRequest(BaseModel):
    """模板预览请求"""
    template_config: Dict[str, Any] = Field(..., description="模板配置")


class TemplatePreviewResponse(BaseModel):
    """模板预览响应"""
    extracted_fields: Dict[str, Any]
    detected_tables: List[Dict[str, Any]]
    validation_result: Dict[str, Any]
    confidence_score: float


@router.post("/templates/preview", response_model=TemplatePreviewResponse)
async def preview_template_extraction(
    file: UploadFile = File(...),
    request: TemplatePreviewRequest = None,
    db: Session = Depends(get_db)
):
    """使用模板预览提取结果"""
    content = await file.read()

    # 保存临时文件
    temp_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    temp_path = os.path.join(TEMP_DIR, f"{temp_id}{file_ext}")

    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        # 解析文档
        parsed_doc = document_parser.parse(temp_path)

        # 合并所有文本
        all_text = []
        all_tables = []

        for page in parsed_doc.get("pages", []):
            page_text = page.get("text", "")
            all_text.append(page_text)

            # 收集表格
            for table in page.get("tables", []):
                all_tables.append(table)

        full_text = "\n\n".join(all_text)

        # 使用模板配置提取字段
        template_config = request.template_config if request else {}
        extracted_fields = {}

        if template_config:
            # 使用AI提取
            extraction_result = ai_extractor.extract_with_template(full_text, template_config)
            extracted_fields = extraction_result.get("extracted", {})

        # 检测表格
        detected_tables = []
        for i, table in enumerate(all_tables):
            detected_tables.append({
                "index": i,
                "headers": table[0] if isinstance(table, list) and table else [],
                "rows": table[1:] if isinstance(table, list) and len(table) > 1 else [],
                "row_count": len(table) if isinstance(table, list) else 0
            })

        # 校验结果
        validation_result = {}
        if template_config and extracted_fields:
            validation_result = cross_field_validator.validate(extracted_fields, template_config)

        return TemplatePreviewResponse(
            extracted_fields=extracted_fields,
            detected_tables=detected_tables,
            validation_result=validation_result,
            confidence_score=0.8
        )

    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/templates/types")
async def list_document_types():
    """列出支持的文档类型"""
    return {
        "document_types": [
            {
                "type": "invoice",
                "name": "发票",
                "category": "financial",
                "supported_formats": ["pdf", "image"]
            },
            {
                "type": "contract",
                "name": "合同",
                "category": "legal",
                "supported_formats": ["pdf", "word"]
            },
            {
                "type": "purchase_order",
                "name": "采购订单",
                "category": "procurement",
                "supported_formats": ["pdf", "image", "word", "excel"]
            },
            {
                "type": "delivery_note",
                "name": "送货单",
                "category": "logistics",
                "supported_formats": ["pdf", "image", "word", "excel"]
            },
            {
                "type": "quotation",
                "name": "报价单",
                "category": "sales",
                "supported_formats": ["pdf", "image", "word", "excel"]
            },
            {
                "type": "receipt",
                "name": "收据",
                "category": "financial",
                "supported_formats": ["pdf", "image"]
            },
            {
                "type": "report",
                "name": "报告",
                "category": "business",
                "supported_formats": ["pdf", "word"]
            },
            {
                "type": "general",
                "name": "通用文档",
                "category": "general",
                "supported_formats": ["pdf", "word", "excel", "image"]
            }
        ]
    }


@router.post("/templates/load-defaults")
async def load_default_templates(
    tenant_id: str = Query(default="default", description="租户ID"),
    db: Session = Depends(get_db)
):
    """加载默认模板到数据库"""
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")

    loaded_templates = []
    template_files = {
        "invoice.json": "invoice",
        "contract.json": "contract",
        "contract_enhanced.json": "contract",
        "purchase_order.json": "purchase_order",
        "delivery_note.json": "delivery_note",
        "quotation.json": "quotation",
        "receipt.json": "receipt",
        "report.json": "report",
        "report_enhanced.json": "report"
    }

    for filename, doc_type in template_files.items():
        filepath = os.path.join(templates_dir, filename)

        if not os.path.exists(filepath):
            logger.warning(f"Template file not found: {filepath}")
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                template_config = json.load(f)

            # 检查是否已存在
            from models.extraction_rule import ExtractionTemplate
            existing = db.query(ExtractionTemplate).filter(
                ExtractionTemplate.tenant_id == tenant_id,
                ExtractionTemplate.template_type == doc_type,
                ExtractionTemplate.name == template_config.get("name", filename)
            ).first()

            if existing:
                # 更新现有模板
                existing.extraction_rules = template_config
                existing.updated_at = datetime.now()
                loaded_templates.append({
                    "name": existing.name,
                    "type": existing.template_type,
                    "action": "updated"
                })
            else:
                # 创建新模板
                new_template = ExtractionTemplate(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    user_id="system",
                    name=template_config.get("name", filename),
                    description=template_config.get("description", ""),
                    template_type=doc_type,
                    category=template_config.get("category", "general"),
                    supported_formats=template_config.get("supported_formats", ["pdf"]),
                    extraction_rules=template_config,
                    is_active=True,
                    is_public=True,
                    version=1
                )
                db.add(new_template)
                loaded_templates.append({
                    "name": new_template.name,
                    "type": new_template.template_type,
                    "action": "created"
                })

        except Exception as e:
            logger.error(f"Error loading template {filename}: {e}")

    db.commit()

    return {
        "message": "Templates loaded successfully",
        "templates": loaded_templates,
        "count": len(loaded_templates)
    }
