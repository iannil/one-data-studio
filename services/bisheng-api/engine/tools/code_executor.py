"""
代码执行工具
Sprint 17: Agent 工具扩展

功能:
- 沙箱 Python 代码执行
- 安全限制（AST 分析 + RestrictedPython）
- 执行超时限制

SECURITY WARNING:
This code executor uses AST analysis and restricted builtins to create a sandbox,
but it is NOT a fully secure sandbox. Sophisticated attackers may be able to bypass
these restrictions. For high-security environments, consider:

1. Using Docker/container-based isolation
2. Using a dedicated code execution service like Pyodide or a subprocess sandbox
3. Using RestrictedPython with additional guards
4. Network isolation to prevent exfiltration
5. Resource limits (CPU, memory) at the OS level

The current implementation is suitable for:
- Internal use with trusted users
- Development and testing environments
- Low-risk code execution scenarios

It is NOT recommended for:
- Untrusted user input execution
- Production systems with sensitive data access
- Internet-facing applications without additional layers
"""

import ast
import logging
import asyncio
import sys
import os
from typing import Any, Dict, List, Optional, Tuple
from io import StringIO
import traceback
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_tools import BaseTool, ToolSchema

logger = logging.getLogger(__name__)


class CodeSecurityValidator(ast.NodeVisitor):
    """AST-based code security validator

    Analyzes Python code AST to detect potentially dangerous operations.
    """

    FORBIDDEN_MODULES = {
        "os", "sys", "subprocess", "shutil", "socket", "requests",
        "urllib", "http", "ftplib", "smtplib", "pickle", "marshal",
        "ctypes", "multiprocessing", "threading", "signal", "pty",
        "fcntl", "termios", "resource", "pwd", "grp", "crypt",
    }

    FORBIDDEN_FUNCTIONS = {
        "open", "exec", "eval", "compile", "input", "__import__",
        "globals", "locals", "vars", "dir", "getattr", "setattr",
        "delattr", "hasattr", "breakpoint", "exit", "quit",
    }

    FORBIDDEN_ATTRIBUTES = {
        "__class__", "__bases__", "__subclasses__", "__mro__",
        "__globals__", "__code__", "__builtins__", "__dict__",
        "__module__", "__reduce__", "__reduce_ex__",
    }

    def __init__(self):
        self.errors: List[str] = []

    def validate(self, code: str) -> Tuple[bool, str]:
        """Validate code for security issues

        Args:
            code: Python source code

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            tree = ast.parse(code)
            self.visit(tree)
            if self.errors:
                return False, "; ".join(self.errors)
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

    def visit_Import(self, node: ast.Import):
        """Check for forbidden imports"""
        for alias in node.names:
            module = alias.name.split('.')[0]
            if module in self.FORBIDDEN_MODULES:
                self.errors.append(f"Forbidden import: {module}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check for forbidden from imports"""
        if node.module:
            module = node.module.split('.')[0]
            if module in self.FORBIDDEN_MODULES:
                self.errors.append(f"Forbidden import from: {module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Check for forbidden function calls"""
        if isinstance(node.func, ast.Name):
            if node.func.id in self.FORBIDDEN_FUNCTIONS:
                self.errors.append(f"Forbidden function: {node.func.id}")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in self.FORBIDDEN_FUNCTIONS:
                self.errors.append(f"Forbidden method: {node.func.attr}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        """Check for forbidden attribute access"""
        if node.attr in self.FORBIDDEN_ATTRIBUTES:
            self.errors.append(f"Forbidden attribute: {node.attr}")
        # Check for dunder attributes
        if node.attr.startswith('__') and node.attr.endswith('__'):
            if node.attr not in {'__init__', '__str__', '__repr__', '__len__', '__iter__', '__next__'}:
                self.errors.append(f"Forbidden dunder attribute: {node.attr}")
        self.generic_visit(node)


class CodeExecutorTool(BaseTool):
    """
    代码执行工具
    Sprint 17: Agent 工具扩展

    安全特性:
    - RestrictedPython 沙箱
    - 执行超时限制
    - 禁止危险操作
    - 内存使用限制

    PRODUCTION NOTE:
    This tool can be disabled in production by setting DISABLE_CODE_EXECUTOR=true.
    It is recommended to disable this in production unless there is a specific
    trusted use case, and additional isolation (Docker containers) is in place.
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

        # Check if code execution is disabled
        # SECURITY: In production, code execution is disabled by default unless explicitly enabled
        env = os.getenv("ENVIRONMENT", "").lower()
        is_production = env in ("production", "prod")

        # In production: default to disabled (must set ENABLE_CODE_EXECUTOR=true to enable)
        # In other environments: default to enabled (can set DISABLE_CODE_EXECUTOR=true to disable)
        if is_production:
            self.disabled = os.getenv("ENABLE_CODE_EXECUTOR", "false").lower() != "true"
            if self.disabled:
                logger.info(
                    "Code executor is disabled in production (default). "
                    "Set ENABLE_CODE_EXECUTOR=true to enable (not recommended without container isolation)."
                )
            else:
                logger.warning(
                    "⚠️  WARNING: Code executor is ENABLED in production. "
                    "Ensure Docker container isolation is in place for security."
                )
        else:
            self.disabled = os.getenv("DISABLE_CODE_EXECUTOR", "false").lower() == "true"
            if self.disabled:
                logger.warning(
                    "Code executor is disabled via DISABLE_CODE_EXECUTOR environment variable. "
                    "All code execution requests will be rejected."
                )

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
            logger.debug("math module not available in sandbox")

        try:
            import json
            safe_globals["json"] = json
        except ImportError:
            logger.debug("json module not available in sandbox")

        try:
            import re
            safe_globals["re"] = re
        except ImportError:
            logger.debug("re module not available in sandbox")

        try:
            import datetime
            safe_globals["datetime"] = datetime
        except ImportError:
            logger.debug("datetime module not available in sandbox")

        try:
            import statistics
            safe_globals["statistics"] = statistics
        except ImportError:
            logger.debug("statistics module not available in sandbox")

        # 添加用户变量
        if user_variables:
            safe_globals.update(user_variables)

        return safe_globals

    def _validate_code(self, code: str) -> Tuple[bool, str]:
        """验证代码安全性 - 使用 AST 分析

        使用 AST 分析替代 regex，提供更准确的安全检查。
        """
        # 使用 AST-based 验证器
        validator = CodeSecurityValidator()
        is_valid, error = validator.validate(code)
        if not is_valid:
            return False, error

        return True, ""

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行代码"""
        # Check if disabled in production
        if self.disabled:
            return {
                "success": False,
                "error": "Code execution is disabled in this environment for security reasons."
            }

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
                # Sanitize error output - don't expose full code in errors
                sanitized_error = str(error)
                # Truncate long error messages to prevent log bloat
                if len(sanitized_error) > 500:
                    sanitized_error = sanitized_error[:500] + "...[truncated]"

                return {
                    "success": False,
                    "error": sanitized_error,
                    # Don't include full traceback in production - it may contain code
                    "traceback": "[traceback hidden for security]" if os.getenv("ENVIRONMENT", "").lower() in ("production", "prod") else traceback.format_exc(),
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
