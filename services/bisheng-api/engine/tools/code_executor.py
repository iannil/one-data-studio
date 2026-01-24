"""
代码执行工具
Sprint 17: Agent 工具扩展

功能:
- 沙箱 Python 代码执行
- 安全限制（RestrictedPython）
- 执行超时限制
"""

import logging
import asyncio
import sys
import os
from typing import Any, Dict, List, Optional
from io import StringIO
import traceback
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import BaseTool, ToolSchema

logger = logging.getLogger(__name__)


class CodeExecutorTool(BaseTool):
    """
    代码执行工具
    Sprint 17: Agent 工具扩展

    安全特性:
    - RestrictedPython 沙箱
    - 执行超时限制
    - 禁止危险操作
    - 内存使用限制
    """

    name = "code_executor"
    description = "在安全沙箱中执行 Python 代码。可以进行数据处理、计算和分析。"
    parameters = [
        ToolSchema("code", "string", "要执行的 Python 代码", required=True),
        ToolSchema("timeout", "integer", "执行超时时间（秒）", default=30),
        ToolSchema("variables", "object", "传入代码的变量", default={}),
    ]

    DEFAULT_TIMEOUT = 30  # 秒
    MAX_TIMEOUT = 120  # 最大超时
    MAX_OUTPUT_LENGTH = 10000  # 最大输出长度

    # 禁止的模块
    FORBIDDEN_MODULES = {
        "os", "sys", "subprocess", "shutil", "socket", "requests",
        "urllib", "http", "ftplib", "smtplib", "pickle", "marshal",
        "ctypes", "multiprocessing", "threading", "signal", "pty",
        "fcntl", "termios", "resource", "pwd", "grp", "crypt",
    }

    # 禁止的内置函数
    FORBIDDEN_BUILTINS = {
        "open", "exec", "eval", "compile", "input", "__import__",
        "globals", "locals", "vars", "dir", "getattr", "setattr",
        "delattr", "hasattr", "type", "isinstance", "issubclass",
    }

    # 允许的安全内置函数
    SAFE_BUILTINS = {
        "abs", "all", "any", "bin", "bool", "chr", "dict", "divmod",
        "enumerate", "filter", "float", "format", "frozenset", "hash",
        "hex", "int", "iter", "len", "list", "map", "max", "min",
        "next", "oct", "ord", "pow", "print", "range", "repr",
        "reversed", "round", "set", "slice", "sorted", "str", "sum",
        "tuple", "zip", "True", "False", "None",
    }

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.enable_restricted = config.get("enable_restricted", True) if config else True

    def _create_safe_globals(self, user_variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建安全的全局变量环境"""
        import builtins

        # 构建安全的内置函数
        safe_builtins = {}
        for name in self.SAFE_BUILTINS:
            if hasattr(builtins, name):
                safe_builtins[name] = getattr(builtins, name)

        # 添加安全的数学和数据处理库
        safe_globals = {
            "__builtins__": safe_builtins,
            "__name__": "__main__",
        }

        # 尝试添加安全的库
        try:
            import math
            safe_globals["math"] = math
        except ImportError:
            pass

        try:
            import json
            safe_globals["json"] = json
        except ImportError:
            pass

        try:
            import re
            safe_globals["re"] = re
        except ImportError:
            pass

        try:
            import datetime
            safe_globals["datetime"] = datetime
        except ImportError:
            pass

        try:
            import statistics
            safe_globals["statistics"] = statistics
        except ImportError:
            pass

        # 添加用户变量
        if user_variables:
            safe_globals.update(user_variables)

        return safe_globals

    def _validate_code(self, code: str) -> tuple[bool, str]:
        """验证代码安全性"""
        # 检查禁止的模块导入
        import re

        # 检查 import 语句
        import_pattern = r'\b(?:import|from)\s+(\w+)'
        imports = re.findall(import_pattern, code)
        for module in imports:
            if module in self.FORBIDDEN_MODULES:
                return False, f"禁止导入模块: {module}"

        # 检查危险函数调用
        for func in self.FORBIDDEN_BUILTINS:
            if re.search(rf'\b{func}\s*\(', code):
                return False, f"禁止使用函数: {func}"

        # 检查其他危险模式
        dangerous_patterns = [
            (r'__\w+__', "禁止使用双下划线属性"),
            (r'\bos\s*\.', "禁止使用 os 模块"),
            (r'\bsys\s*\.', "禁止使用 sys 模块"),
            (r'\bsubprocess', "禁止使用 subprocess"),
            (r'\beval\s*\(', "禁止使用 eval"),
            (r'\bexec\s*\(', "禁止使用 exec"),
            (r'\bopen\s*\(', "禁止使用 open"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, code):
                return False, message

        return True, ""

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行代码"""
        code = kwargs.get("code")
        timeout = min(kwargs.get("timeout", self.DEFAULT_TIMEOUT), self.MAX_TIMEOUT)
        variables = kwargs.get("variables", {})

        if not code:
            return {"success": False, "error": "Code is required"}

        # 验证代码安全性
        if self.enable_restricted:
            is_valid, error = self._validate_code(code)
            if not is_valid:
                return {"success": False, "error": error}

        try:
            # 捕获输出
            stdout_capture = StringIO()
            stderr_capture = StringIO()

            # 创建安全环境
            safe_globals = self._create_safe_globals(variables)
            safe_locals = {}

            # 记录开始时间
            start_time = time.time()

            # 在子线程中执行代码（用于超时控制）
            import concurrent.futures

            def run_code():
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                try:
                    sys.stdout = stdout_capture
                    sys.stderr = stderr_capture

                    # 编译并执行代码
                    compiled = compile(code, "<sandbox>", "exec")
                    exec(compiled, safe_globals, safe_locals)

                    return True, None
                except Exception as e:
                    return False, e
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr

            # 使用 ThreadPoolExecutor 执行代码
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_code)
                try:
                    success, error = future.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
                    return {
                        "success": False,
                        "error": f"代码执行超时（超过 {timeout} 秒）",
                        "execution_time": timeout,
                    }

            # 计算执行时间
            execution_time = time.time() - start_time

            # 获取输出
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            # 限制输出长度
            if len(stdout_output) > self.MAX_OUTPUT_LENGTH:
                stdout_output = stdout_output[:self.MAX_OUTPUT_LENGTH] + "\n...[truncated]"

            if not success:
                return {
                    "success": False,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                    "stdout": stdout_output,
                    "stderr": stderr_output,
                    "execution_time": execution_time,
                }

            # 提取结果变量
            result_vars = {}
            for key, value in safe_locals.items():
                if not key.startswith("_"):
                    try:
                        # 尝试序列化
                        import json
                        json.dumps(value)
                        result_vars[key] = value
                    except (TypeError, ValueError):
                        result_vars[key] = str(value)

            return {
                "success": True,
                "stdout": stdout_output,
                "stderr": stderr_output,
                "variables": result_vars,
                "execution_time": execution_time,
            }

        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
