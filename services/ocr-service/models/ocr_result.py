"""
OCR结果模型
存储详细的识别结果
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base


class OCRResult(Base):
    """OCR识别结果详情表"""
    __tablename__ = "ocr_results"

    id = Column(String(64), primary_key=True, comment="结果ID")
    task_id = Column(String(64), ForeignKey("ocr_tasks.id", ondelete="CASCADE"), nullable=False, index=True, comment="任务ID")

    # 页面级别结果
    page_number = Column(Integer, default=1, comment="页码")
    page_image_path = Column(String(500), comment="页面图片路径")

    # 文本识别结果
    text_content = Column(Text, comment="识别的文本内容")
    text_confidence = Column(Float, comment="文本识别置信度")

    # 布局分析结果
    layout_blocks = Column(JSON, comment="布局块信息（文本块、表格、图片等）")
    tables = Column(JSON, comment="识别的表格数据")

    # 结构化提取结果
    extracted_fields = Column(JSON, comment="提取的字段和值")
    extraction_confidence = Column(JSON, comment="字段级别的置信度")

    # 校正信息
    corrections = Column(JSON, comment="人工校正记录")
    corrected_by = Column(String(64), comment="校正人ID")
    corrected_at = Column(DateTime, comment="校正时间")

    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联
    task = relationship("OCRTask", backref="results")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "page_number": self.page_number,
            "text_content": self.text_content,
            "text_confidence": self.text_confidence,
            "layout_blocks": self.layout_blocks,
            "tables": self.tables,
            "extracted_fields": self.extracted_fields,
            "extraction_confidence": self.extraction_confidence,
            "corrections": self.corrections,
            "corrected_by": self.corrected_by,
        }


class TableData(Base):
    """表格数据表"""
    __tablename__ = "ocr_table_data"

    id = Column(String(64), primary_key=True, comment="表格ID")
    task_id = Column(String(64), ForeignKey("ocr_tasks.id", ondelete="CASCADE"), nullable=False, index=True, comment="任务ID")
    result_id = Column(String(64), ForeignKey("ocr_results.id", ondelete="CASCADE"), comment="结果ID")

    # 表格信息
    table_index = Column(Integer, comment="表格索引")
    page_number = Column(Integer, comment="所在页码")
    row_count = Column(Integer, comment="行数")
    col_count = Column(Integer, comment="列数")

    # 表格数据
    headers = Column(JSON, comment="表头")
    rows = Column(JSON, comment="行数据")
    merged_cells = Column(JSON, comment="合并单元格信息")

    # 表格识别置信度
    confidence = Column(Float, comment="识别置信度")

    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联
    task = relationship("OCRTask", backref="tables_data")
    result = relationship("OCRResult", backref="tables")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "table_index": self.table_index,
            "page_number": self.page_number,
            "row_count": self.row_count,
            "col_count": self.col_count,
            "headers": self.headers,
            "rows": self.rows,
            "merged_cells": self.merged_cells,
            "confidence": self.confidence,
        }
