"""
OCR服务Python客户端SDK
"""

from .ocr_client import (
    OCRClient,
    DocumentType,
    TaskStatus,
    ExtractionResult,
    Template,
    OCRClientError,
    ServiceUnavailableError,
    TaskFailedError,
    extract_document
)

__version__ = "1.0.0"
__all__ = [
    "OCRClient",
    "DocumentType",
    "TaskStatus",
    "ExtractionResult",
    "Template",
    "OCRClientError",
    "ServiceUnavailableError",
    "TaskFailedError",
    "extract_document"
]
