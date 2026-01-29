"""
工具模块初始化
Sprint 17: Agent 工具扩展

提供扩展工具的导入和注册
"""

import os

# 在测试环境下跳过导入有外部依赖的模块
_TESTING = os.environ.get('ENVIRONMENT', '') == 'test'

__all__ = []

if not _TESTING:
    try:
        from .web_browser import WebBrowserTool
        from .file_reader import FileReaderTool
        from .code_executor import CodeExecutorTool
        from .notification import NotificationTool

        __all__ = [
            'WebBrowserTool',
            'FileReaderTool',
            'CodeExecutorTool',
            'NotificationTool',
        ]
    except ImportError:
        pass
