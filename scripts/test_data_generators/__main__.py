"""
测试数据生成器 CLI - Main入口

允许直接运行: python -m scripts.test_data_generators
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
