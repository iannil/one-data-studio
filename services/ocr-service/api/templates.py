"""
提取模板API路由
"""

import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import get_db
from models.extraction_rule import ExtractionTemplate
from models.ocr_task import ExtractionType

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic模型
class CreateTemplateRequest(BaseModel):
    """创建模板请求"""
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    template_type: str = Field(..., description="模板类型")
    category: Optional[str] = Field(None, description="分类")
    extraction_rules: dict = Field(..., description="提取规则配置")
    ai_prompt_template: Optional[str] = Field(None, description="AI提示词模板")
    post_processing: Optional[dict] = Field(None, description="后处理规则")


class UpdateTemplateRequest(BaseModel):
    """更新模板请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    extraction_rules: Optional[dict] = None
    ai_prompt_template: Optional[str] = None
    post_processing: Optional[dict] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    """模板响应"""
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    template_type: str
    category: Optional[str]
    extraction_rules: dict
    is_active: bool
    is_public: bool
    version: int
    usage_count: int
    success_rate: int
    created_at: str
    updated_at: str


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    tenant_id: str = Query(default="default", description="租户ID"),
    user_id: str = Query(default="system", description="用户ID"),
    db: Session = Depends(get_db)
):
    """创建提取模板"""
    template_id = str(uuid.uuid4())

    template = ExtractionTemplate(
        id=template_id,
        tenant_id=tenant_id,
        user_id=user_id,
        name=request.name,
        description=request.description,
        template_type=request.template_type,
        category=request.category,
        supported_formats=["pdf", "image", "word", "excel"],
        extraction_rules=request.extraction_rules,
        ai_prompt_template=request.ai_prompt_template,
        post_processing=request.post_processing,
        is_active=True,
        is_public=False,
        version=1,
        usage_count=0,
        success_rate=0
    )

    db.add(template)
    db.commit()

    return TemplateResponse(
        id=template.id,
        tenant_id=template.tenant_id,
        name=template.name,
        description=template.description,
        template_type=template.template_type,
        category=template.category,
        extraction_rules=template.extraction_rules,
        is_active=template.is_active,
        is_public=template.is_public,
        version=template.version,
        usage_count=template.usage_count,
        success_rate=template.success_rate,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    tenant_id: str = Query(default="default", description="租户ID"),
    template_type: Optional[str] = Query(None, description="模板类型筛选"),
    category: Optional[str] = Query(None, description="分类筛选"),
    is_active: Optional[bool] = Query(None, description="是否只返回启用的模板"),
    include_public: bool = Query(True, description="是否包含公开模板"),
    db: Session = Depends(get_db)
):
    """获取模板列表"""
    query = db.query(ExtractionTemplate)

    # 租户筛选
    if include_public:
        query = query.filter(
            (ExtractionTemplate.tenant_id == tenant_id) |
            (ExtractionTemplate.is_public == True)
        )
    else:
        query = query.filter(ExtractionTemplate.tenant_id == tenant_id)

    # 其他筛选
    if template_type:
        query = query.filter(ExtractionTemplate.template_type == template_type)
    if category:
        query = query.filter(ExtractionTemplate.category == category)
    if is_active is not None:
        query = query.filter(ExtractionTemplate.is_active == is_active)

    templates = query.order_by(
        ExtractionTemplate.usage_count.desc(),
        ExtractionTemplate.created_at.desc()
    ).all()

    return [
        TemplateResponse(
            id=t.id,
            tenant_id=t.tenant_id,
            name=t.name,
            description=t.description,
            template_type=t.template_type,
            category=t.category,
            extraction_rules=t.extraction_rules,
            is_active=t.is_active,
            is_public=t.is_public,
            version=t.version,
            usage_count=t.usage_count,
            success_rate=t.success_rate,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat()
        )
        for t in templates
    ]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str, db: Session = Depends(get_db)):
    """获取模板详情"""
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateResponse(
        id=template.id,
        tenant_id=template.tenant_id,
        name=template.name,
        description=template.description,
        template_type=template.template_type,
        category=template.category,
        extraction_rules=template.extraction_rules,
        is_active=template.is_active,
        is_public=template.is_public,
        version=template.version,
        usage_count=template.usage_count,
        success_rate=template.success_rate,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    db: Session = Depends(get_db)
):
    """更新模板"""
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 更新字段
    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.category is not None:
        template.category = request.category
    if request.extraction_rules is not None:
        template.extraction_rules = request.extraction_rules
    if request.ai_prompt_template is not None:
        template.ai_prompt_template = request.ai_prompt_template
    if request.post_processing is not None:
        template.post_processing = request.post_processing
    if request.is_active is not None:
        template.is_active = request.is_active

    # 增加版本号
    template.version += 1
    template.updated_at = datetime.now()

    db.commit()

    return TemplateResponse(
        id=template.id,
        tenant_id=template.tenant_id,
        name=template.name,
        description=template.description,
        template_type=template.template_type,
        category=template.category,
        extraction_rules=template.extraction_rules,
        is_active=template.is_active,
        is_public=template.is_public,
        version=template.version,
        usage_count=template.usage_count,
        success_rate=template.success_rate,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, db: Session = Depends(get_db)):
    """删除模板"""
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()

    return {"message": "Template deleted successfully"}


@router.get("/templates/{template_id}/preview")
async def preview_template(template_id: str, db: Session = Depends(get_db)):
    """预览模板配置（用于编辑器）"""
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "template_type": template.template_type,
        "extraction_rules": template.extraction_rules,
        "ai_prompt_template": template.ai_prompt_template,
        "post_processing": template.post_processing,
        "supported_formats": template.supported_formats,
    }


# 预设模板初始化
def init_preset_templates(db: Session, tenant_id: str = "default"):
    """初始化预设模板"""

    # 发票模板
    invoice_template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.tenant_id == tenant_id,
        ExtractionTemplate.template_type == ExtractionType.INVOICE.value,
        ExtractionTemplate.name == "增值税发票模板"
    ).first()

    if not invoice_template:
        invoice_template = ExtractionTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id="system",
            name="增值税发票模板",
            description="用于提取增值税发票的关键信息",
            template_type=ExtractionType.INVOICE.value,
            category="financial",
            supported_formats=["pdf", "image"],
            extraction_rules={
                "fields": [
                    {"name": "发票类型", "key": "invoice_type", "required": False},
                    {"name": "发票号码", "key": "invoice_number", "required": True},
                    {"name": "开票日期", "key": "invoice_date", "required": True},
                    {"name": "购买方名称", "key": "buyer_name", "required": False},
                    {"name": "购买方税号", "key": "buyer_tax_id", "required": False},
                    {"name": "销售方名称", "key": "seller_name", "required": False},
                    {"name": "销售方税号", "key": "seller_tax_id", "required": False},
                    {"name": "价税合计", "key": "total_amount", "required": True},
                    {"name": "金额", "key": "amount", "required": False},
                    {"name": "税额", "key": "tax_amount", "required": False},
                    {"name": "税率", "key": "tax_rate", "required": False},
                ]
            },
            is_active=True,
            is_public=True,
            version=1
        )
        db.add(invoice_template)

    # 合同模板
    contract_template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.tenant_id == tenant_id,
        ExtractionTemplate.template_type == ExtractionType.CONTRACT.value,
        ExtractionTemplate.name == "通用合同模板"
    ).first()

    if not contract_template:
        contract_template = ExtractionTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id="system",
            name="通用合同模板",
            description="用于提取合同的基本信息",
            template_type=ExtractionType.CONTRACT.value,
            category="legal",
            supported_formats=["pdf", "word"],
            extraction_rules={
                "fields": [
                    {"name": "合同编号", "key": "contract_number", "required": False},
                    {"name": "合同名称", "key": "contract_name", "required": True},
                    {"name": "甲方", "key": "party_a", "required": True},
                    {"name": "乙方", "key": "party_b", "required": True},
                    {"name": "合同金额", "key": "contract_amount", "required": False},
                    {"name": "签订日期", "key": "signing_date", "required": False},
                    {"name": "生效日期", "key": "effective_date", "required": False},
                    {"name": "截止日期", "key": "expiry_date", "required": False},
                ]
            },
            is_active=True,
            is_public=True,
            version=1
        )
        db.add(contract_template)

    # 报告模板
    report_template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.tenant_id == tenant_id,
        ExtractionTemplate.template_type == ExtractionType.REPORT.value,
        ExtractionTemplate.name == "通用报告模板"
    ).first()

    if not report_template:
        report_template = ExtractionTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id="system",
            name="通用报告模板",
            description="用于提取报告的关键指标",
            template_type=ExtractionTemplate.REPORT.value,
            category="business",
            supported_formats=["pdf", "word"],
            extraction_rules={
                "fields": [
                    {"name": "报告标题", "key": "report_title", "required": True},
                    {"name": "报告日期", "key": "report_date", "required": False},
                    {"name": "报告期", "key": "report_period", "required": False},
                    {"name": "核心指标", "key": "key_metrics", "required": False},
                ]
            },
            is_active=True,
            is_public=True,
            version=1
        )
        db.add(report_template)

    # 采购订单模板
    purchase_order_template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.tenant_id == tenant_id,
        ExtractionTemplate.template_type == ExtractionType.PURCHASE_ORDER.value,
        ExtractionTemplate.name == "采购订单模板"
    ).first()

    if not purchase_order_template:
        purchase_order_template = ExtractionTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id="system",
            name="采购订单模板",
            description="用于提取采购订单的关键信息",
            template_type=ExtractionType.PURCHASE_ORDER.value,
            category="procurement",
            supported_formats=["pdf", "image", "word", "excel"],
            extraction_rules={
                "fields": [
                    {"name": "订单编号", "key": "order_number", "required": True},
                    {"name": "订单日期", "key": "order_date", "required": True},
                    {"name": "供应商名称", "key": "supplier_name", "required": True},
                    {"name": "采购方名称", "key": "buyer_name", "required": True},
                    {"name": "订单总金额", "key": "total_amount", "required": True},
                ]
            },
            is_active=True,
            is_public=True,
            version=1
        )
        db.add(purchase_order_template)

    # 送货单模板
    delivery_note_template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.tenant_id == tenant_id,
        ExtractionTemplate.template_type == ExtractionType.DELIVERY_NOTE.value,
        ExtractionTemplate.name == "送货单模板"
    ).first()

    if not delivery_note_template:
        delivery_note_template = ExtractionTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id="system",
            name="送货单模板",
            description="用于提取送货单的关键信息",
            template_type=ExtractionType.DELIVERY_NOTE.value,
            category="logistics",
            supported_formats=["pdf", "image", "word", "excel"],
            extraction_rules={
                "fields": [
                    {"name": "送货单号", "key": "delivery_number", "required": True},
                    {"name": "送货日期", "key": "delivery_date", "required": True},
                    {"name": "供应商名称", "key": "supplier_name", "required": True},
                    {"name": "收货单位", "key": "receiver_name", "required": True},
                ]
            },
            is_active=True,
            is_public=True,
            version=1
        )
        db.add(delivery_note_template)

    # 报价单模板
    quotation_template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.tenant_id == tenant_id,
        ExtractionTemplate.template_type == ExtractionType.QUOTATION.value,
        ExtractionTemplate.name == "报价单模板"
    ).first()

    if not quotation_template:
        quotation_template = ExtractionTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id="system",
            name="报价单模板",
            description="用于提取报价单的关键信息",
            template_type=ExtractionType.QUOTATION.value,
            category="sales",
            supported_formats=["pdf", "image", "word", "excel"],
            extraction_rules={
                "fields": [
                    {"name": "报价单号", "key": "quotation_number", "required": True},
                    {"name": "报价日期", "key": "quotation_date", "required": True},
                    {"name": "报价方名称", "key": "provider_name", "required": True},
                    {"name": "客户名称", "key": "customer_name", "required": True},
                    {"name": "报价总金额", "key": "total_amount", "required": True},
                ]
            },
            is_active=True,
            is_public=True,
            version=1
        )
        db.add(quotation_template)

    # 收据模板
    receipt_template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.tenant_id == tenant_id,
        ExtractionTemplate.template_type == ExtractionType.RECEIPT.value,
        ExtractionTemplate.name == "收据模板"
    ).first()

    if not receipt_template:
        receipt_template = ExtractionTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id="system",
            name="收据模板",
            description="用于提取收据的关键信息",
            template_type=ExtractionType.RECEIPT.value,
            category="financial",
            supported_formats=["pdf", "image"],
            extraction_rules={
                "fields": [
                    {"name": "收据编号", "key": "receipt_number", "required": True},
                    {"name": "收据日期", "key": "receipt_date", "required": True},
                    {"name": "付款方名称", "key": "payer_name", "required": True},
                    {"name": "收款方名称", "key": "payee_name", "required": True},
                    {"name": "收款金额", "key": "amount", "required": True},
                ]
            },
            is_active=True,
            is_public=True,
            version=1
        )
        db.add(receipt_template)

    db.commit()
    logger.info("Preset templates initialized")
