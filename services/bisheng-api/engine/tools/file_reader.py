"""
文件读取工具
Sprint 17: Agent 工具扩展

功能:
- 读取 CSV、Excel、JSON 文件
- 数据预览和统计
- 路径安全控制
"""

import logging
import os
from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import BaseTool, ToolSchema

logger = logging.getLogger(__name__)


class FileReaderTool(BaseTool):
    """
    文件读取工具
    Sprint 17: Agent 工具扩展

    安全特性:
    - 路径白名单
    - 文件大小限制
    - 支持格式限制
    """

    name = "file_reader"
    description = "读取 CSV、Excel 或 JSON 文件内容。可以获取文件数据和基本统计信息。"
    parameters = [
        ToolSchema("file_path", "string", "文件路径", required=True),
        ToolSchema("file_type", "string", "文件类型 (csv, excel, json)", default="auto"),
        ToolSchema("preview_rows", "integer", "预览行数", default=10),
        ToolSchema("include_stats", "boolean", "是否包含统计信息", default=True),
    ]

    # 支持的文件类型
    SUPPORTED_TYPES = {
        "csv": [".csv", ".tsv"],
        "excel": [".xlsx", ".xls"],
        "json": [".json", ".jsonl"],
    }

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_PREVIEW_ROWS = 100

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # 允许访问的目录白名单
        self.allowed_dirs = config.get("allowed_dirs", []) if config else []
        # 默认上传目录
        self.upload_dir = config.get("upload_dir", "/tmp/uploads") if config else "/tmp/uploads"

    def _validate_path(self, file_path: str) -> tuple[bool, str]:
        """验证文件路径安全性"""
        try:
            # 解析为绝对路径
            abs_path = Path(file_path).resolve()

            # 检查路径遍历攻击
            if ".." in str(abs_path):
                return False, "路径包含非法字符"

            # 检查是否在允许的目录内
            if self.allowed_dirs:
                allowed = False
                for dir_path in self.allowed_dirs:
                    if str(abs_path).startswith(str(Path(dir_path).resolve())):
                        allowed = True
                        break
                if not allowed:
                    # 默认允许上传目录
                    if not str(abs_path).startswith(str(Path(self.upload_dir).resolve())):
                        return False, f"文件路径不在允许的目录内"

            # 检查文件是否存在
            if not abs_path.exists():
                return False, "文件不存在"

            # 检查是否是文件
            if not abs_path.is_file():
                return False, "路径不是文件"

            # 检查文件大小
            if abs_path.stat().st_size > self.MAX_FILE_SIZE:
                return False, f"文件大小超过限制 ({self.MAX_FILE_SIZE / 1024 / 1024}MB)"

            return True, str(abs_path)

        except Exception as e:
            return False, f"路径验证失败: {str(e)}"

    def _detect_file_type(self, file_path: str) -> str:
        """检测文件类型"""
        ext = Path(file_path).suffix.lower()
        for file_type, extensions in self.SUPPORTED_TYPES.items():
            if ext in extensions:
                return file_type
        return "unknown"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """读取文件"""
        file_path = kwargs.get("file_path")
        file_type = kwargs.get("file_type", "auto")
        preview_rows = min(kwargs.get("preview_rows", 10), self.MAX_PREVIEW_ROWS)
        include_stats = kwargs.get("include_stats", True)

        if not file_path:
            return {"success": False, "error": "File path is required"}

        # 验证路径
        is_valid, result = self._validate_path(file_path)
        if not is_valid:
            return {"success": False, "error": result}

        abs_path = result

        # 检测或验证文件类型
        if file_type == "auto":
            file_type = self._detect_file_type(abs_path)

        if file_type == "unknown":
            return {
                "success": False,
                "error": f"不支持的文件类型。支持: {list(self.SUPPORTED_TYPES.keys())}"
            }

        try:
            if file_type == "csv":
                return await self._read_csv(abs_path, preview_rows, include_stats)
            elif file_type == "excel":
                return await self._read_excel(abs_path, preview_rows, include_stats)
            elif file_type == "json":
                return await self._read_json(abs_path, preview_rows)
            else:
                return {"success": False, "error": f"不支持的文件类型: {file_type}"}

        except Exception as e:
            logger.error(f"File read failed for {file_path}: {e}")
            return {"success": False, "error": str(e)}

    async def _read_csv(self, file_path: str, preview_rows: int, include_stats: bool) -> Dict[str, Any]:
        """读取 CSV 文件"""
        try:
            import pandas as pd
        except ImportError:
            return {
                "success": False,
                "error": "pandas is required. Install with: pip install pandas"
            }

        # 读取 CSV
        df = pd.read_csv(file_path, nrows=preview_rows if not include_stats else None)

        result = {
            "success": True,
            "file_path": file_path,
            "file_type": "csv",
            "columns": list(df.columns),
            "total_rows": len(df),
            "preview": df.head(preview_rows).to_dict(orient="records"),
        }

        if include_stats and len(df) > 0:
            result["stats"] = {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "null_counts": df.isnull().sum().to_dict(),
                "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.1f}KB",
            }

            # 数值列统计
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                result["stats"]["numeric_summary"] = df[numeric_cols].describe().to_dict()

        return result

    async def _read_excel(self, file_path: str, preview_rows: int, include_stats: bool) -> Dict[str, Any]:
        """读取 Excel 文件"""
        try:
            import pandas as pd
        except ImportError:
            return {
                "success": False,
                "error": "pandas and openpyxl are required. Install with: pip install pandas openpyxl"
            }

        # 获取所有 sheet 名称
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names

        # 读取第一个 sheet
        df = pd.read_excel(file_path, nrows=preview_rows if not include_stats else None)

        result = {
            "success": True,
            "file_path": file_path,
            "file_type": "excel",
            "sheets": sheet_names,
            "active_sheet": sheet_names[0],
            "columns": list(df.columns),
            "total_rows": len(df),
            "preview": df.head(preview_rows).to_dict(orient="records"),
        }

        if include_stats and len(df) > 0:
            result["stats"] = {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "null_counts": df.isnull().sum().to_dict(),
            }

        return result

    async def _read_json(self, file_path: str, preview_rows: int) -> Dict[str, Any]:
        """读取 JSON 文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 尝试解析 JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            # 尝试 JSONL 格式
            try:
                lines = content.strip().split('\n')
                data = [json.loads(line) for line in lines[:preview_rows]]
                return {
                    "success": True,
                    "file_path": file_path,
                    "file_type": "jsonl",
                    "total_lines": len(lines),
                    "preview": data,
                }
            except:
                return {"success": False, "error": f"JSON 解析失败: {str(e)}"}

        # 处理结果
        if isinstance(data, list):
            return {
                "success": True,
                "file_path": file_path,
                "file_type": "json",
                "data_type": "array",
                "total_items": len(data),
                "preview": data[:preview_rows],
            }
        elif isinstance(data, dict):
            return {
                "success": True,
                "file_path": file_path,
                "file_type": "json",
                "data_type": "object",
                "keys": list(data.keys()),
                "data": data,
            }
        else:
            return {
                "success": True,
                "file_path": file_path,
                "file_type": "json",
                "data_type": type(data).__name__,
                "data": data,
            }
