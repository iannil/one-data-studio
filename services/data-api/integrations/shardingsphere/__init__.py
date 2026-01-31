"""
ShardingSphere 透明脱敏集成模块

提供与 ShardingSphere Proxy 的集成功能，实现透明脱敏。
"""

from .config import ShardingSphereConfig
from .client import ShardingSphereClient
from .masking_rule_generator import MaskingRuleGenerator

__all__ = [
    "ShardingSphereConfig",
    "ShardingSphereClient",
    "MaskingRuleGenerator",
]
