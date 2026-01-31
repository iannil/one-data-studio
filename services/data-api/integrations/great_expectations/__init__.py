"""
Great Expectations 数据质量引擎集成

提供基于 Great Expectations 的数据质量校验能力，
作为内置质量引擎的增强补充。
"""

from .config import GEConfig
from .ge_engine import GEValidationEngine

__all__ = [
    "GEConfig",
    "GEValidationEngine",
]
