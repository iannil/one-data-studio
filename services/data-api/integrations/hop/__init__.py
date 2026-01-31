"""
Apache Hop ETL 引擎集成模块

提供与 Apache Hop Server 的集成功能，作为 Kettle 的现代替代方案。
"""

from .config import HopConfig
from .hop_bridge import HopBridge

__all__ = [
    "HopConfig",
    "HopBridge",
]
