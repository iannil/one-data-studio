"""
Kettle/PDI ETL 引擎集成模块

提供与 Pentaho Data Integration (Kettle) Carte 服务器的集成功能。
"""

from .config import KettleConfig
from .kettle_bridge import KettleBridge

__all__ = [
    "KettleConfig",
    "KettleBridge",
]
