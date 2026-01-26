"""
Kettle ETL 引擎桥接服务
连接 Alldata 原生 Kettle (Pentaho Data Integration) 能力

支持:
- Kitchen: 执行 Kettle 作业 (.kjb)
- Pan: 执行 Kettle 转换 (.ktr)
- 文件模式和仓库模式
"""

import os
import subprocess
import logging
import tempfile
import json
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Callable, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# 回调类型定义
PostExecutionCallback = Callable[["KettleExecutionResult", Dict[str, Any]], None]
PreExecutionCallback = Callable[[str, Dict[str, Any]], bool]  # 返回 False 取消执行


class KettleExecutionMode(Enum):
    """Kettle 执行模式"""
    FILE = "file"  # 基于文件执行
    REPOSITORY = "repository"  # 基于仓库执行


class KettleJobType(Enum):
    """Kettle 作业类型"""
    JOB = "job"  # 作业 (.kjb)
    TRANSFORMATION = "transformation"  # 转换 (.ktr)


@dataclass
class KettleConfig:
    """Kettle 配置"""
    kettle_home: str = "/opt/kettle"  # Kettle 安装目录
    java_home: Optional[str] = None  # JAVA_HOME
    max_log_lines: int = 1000  # 最大日志行数
    timeout_seconds: int = 3600  # 执行超时时间（秒）

    @classmethod
    def from_env(cls) -> "KettleConfig":
        """从环境变量加载配置"""
        return cls(
            kettle_home=os.getenv("KETTLE_HOME", "/opt/kettle"),
            java_home=os.getenv("JAVA_HOME"),
            max_log_lines=int(os.getenv("KETTLE_MAX_LOG_LINES", "1000")),
            timeout_seconds=int(os.getenv("KETTLE_TIMEOUT_SECONDS", "3600")),
        )


@dataclass
class KettleExecutionResult:
    """Kettle 执行结果"""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    rows_read: int = 0
    rows_written: int = 0
    rows_error: int = 0
    error_message: Optional[str] = None
    # 扩展字段用于元数据同步
    task_id: str = ""
    job_type: str = ""  # job / transformation
    file_path: str = ""
    source_table: str = ""
    target_table: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "rows_read": self.rows_read,
            "rows_written": self.rows_written,
            "rows_error": self.rows_error,
            "error_message": self.error_message,
            "task_id": self.task_id,
            "job_type": self.job_type,
            "file_path": self.file_path,
            "source_table": self.source_table,
            "target_table": self.target_table,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


class KettleBridge:
    """
    Kettle 桥接服务

    通过调用 Kitchen (作业) 和 Pan (转换) 命令与 Kettle 交互
    支持执行前后回调钩子，用于元数据同步等场景
    """

    def __init__(self, config: Optional[KettleConfig] = None):
        self.config = config or KettleConfig.from_env()
        self._validate_installation()

        # 回调列表
        self._pre_execution_callbacks: List[PreExecutionCallback] = []
        self._post_execution_callbacks: List[PostExecutionCallback] = []

    def register_pre_execution_callback(self, callback: PreExecutionCallback) -> None:
        """
        注册执行前回调

        回调函数签名: (file_path: str, context: Dict) -> bool
        返回 False 将取消执行

        Args:
            callback: 回调函数
        """
        self._pre_execution_callbacks.append(callback)

    def register_post_execution_callback(self, callback: PostExecutionCallback) -> None:
        """
        注册执行后回调

        回调函数签名: (result: KettleExecutionResult, context: Dict) -> None
        用于元数据同步、通知发送等

        Args:
            callback: 回调函数
        """
        self._post_execution_callbacks.append(callback)

    def unregister_pre_execution_callback(self, callback: PreExecutionCallback) -> None:
        """移除执行前回调"""
        if callback in self._pre_execution_callbacks:
            self._pre_execution_callbacks.remove(callback)

    def unregister_post_execution_callback(self, callback: PostExecutionCallback) -> None:
        """移除执行后回调"""
        if callback in self._post_execution_callbacks:
            self._post_execution_callbacks.remove(callback)

    def _execute_pre_callbacks(self, file_path: str, context: Dict[str, Any]) -> bool:
        """执行前置回调，返回是否继续执行"""
        for callback in self._pre_execution_callbacks:
            try:
                result = callback(file_path, context)
                if result is False:
                    logger.info(f"执行被前置回调取消: {file_path}")
                    return False
            except Exception as e:
                logger.warning(f"前置回调执行失败: {e}")
        return True

    def _execute_post_callbacks(
        self,
        result: KettleExecutionResult,
        context: Dict[str, Any],
    ) -> None:
        """执行后置回调"""
        for callback in self._post_execution_callbacks:
            try:
                callback(result, context)
            except Exception as e:
                logger.warning(f"后置回调执行失败: {e}")

    def _validate_installation(self) -> None:
        """验证 Kettle 安装"""
        kitchen_path = self._get_kitchen_path()
        pan_path = self._get_pan_path()

        if not os.path.exists(self.config.kettle_home):
            logger.warning(f"Kettle home not found: {self.config.kettle_home}")
            logger.warning("Kettle commands will fail. Set KETTLE_HOME environment variable.")
        elif not os.path.exists(kitchen_path):
            logger.warning(f"Kitchen script not found: {kitchen_path}")
        elif not os.path.exists(pan_path):
            logger.warning(f"Pan script not found: {pan_path}")
        else:
            logger.info(f"Kettle installation validated at: {self.config.kettle_home}")

    def _get_kitchen_path(self) -> str:
        """获取 Kitchen 脚本路径"""
        if os.name == "nt":  # Windows
            return os.path.join(self.config.kettle_home, "kitchen.bat")
        return os.path.join(self.config.kettle_home, "kitchen.sh")

    def _get_pan_path(self) -> str:
        """获取 Pan 脚本路径"""
        if os.name == "nt":  # Windows
            return os.path.join(self.config.kettle_home, "pan.bat")
        return os.path.join(self.config.kettle_home, "pan.sh")

    def _build_env(self) -> Dict[str, str]:
        """构建执行环境变量"""
        env = os.environ.copy()
        env["KETTLE_HOME"] = self.config.kettle_home
        if self.config.java_home:
            env["JAVA_HOME"] = self.config.java_home
        return env

    def _parse_kettle_output(self, stdout: str) -> Tuple[int, int, int]:
        """
        解析 Kettle 输出获取行数统计

        Returns:
            Tuple[rows_read, rows_written, rows_error]
        """
        rows_read = 0
        rows_written = 0
        rows_error = 0

        for line in stdout.split("\n"):
            line_lower = line.lower()
            # 尝试解析各种格式的统计信息
            if "read" in line_lower and "rows" in line_lower:
                try:
                    # 格式: "Step X read 1000 rows"
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p.lower() == "read" and i + 1 < len(parts):
                            rows_read += int(parts[i + 1].replace(",", ""))
                except (ValueError, IndexError):
                    pass

            if "written" in line_lower and "rows" in line_lower:
                try:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p.lower() == "written" and i + 1 < len(parts):
                            rows_written += int(parts[i + 1].replace(",", ""))
                except (ValueError, IndexError):
                    pass

            if "error" in line_lower and "rows" in line_lower:
                try:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p.lower() == "error" and i + 1 < len(parts):
                            rows_error += int(parts[i + 1].replace(",", ""))
                except (ValueError, IndexError):
                    pass

        return rows_read, rows_written, rows_error

    def execute_job(
        self,
        job_path: Optional[str] = None,
        repository: Optional[str] = None,
        directory: Optional[str] = None,
        job_name: Optional[str] = None,
        params: Optional[Dict[str, str]] = None,
        log_level: str = "Basic",
        context: Optional[Dict[str, Any]] = None,
        task_id: str = "",
        source_table: str = "",
        target_table: str = "",
    ) -> KettleExecutionResult:
        """
        执行 Kettle 作业 (.kjb)

        Args:
            job_path: 作业文件路径（文件模式）
            repository: 仓库名称（仓库模式）
            directory: 目录路径（仓库模式）
            job_name: 作业名称（仓库模式）
            params: 参数字典
            log_level: 日志级别 (Nothing, Error, Minimal, Basic, Detailed, Debug, Rowlevel)
            context: 执行上下文（传递给回调）
            task_id: 任务 ID（用于追踪）
            source_table: 源表名（用于元数据同步）
            target_table: 目标表名（用于元数据同步）

        Returns:
            KettleExecutionResult
        """
        context = context or {}
        context.update({
            "job_type": "job",
            "job_path": job_path,
            "repository": repository,
            "job_name": job_name,
            "task_id": task_id,
            "source_table": source_table,
            "target_table": target_table,
        })

        # 执行前置回调
        if job_path and not self._execute_pre_callbacks(job_path, context):
            return KettleExecutionResult(
                success=False,
                exit_code=-2,
                stdout="",
                stderr="Execution cancelled by pre-execution callback",
                duration_seconds=0,
                error_message="Cancelled by callback",
                task_id=task_id,
                job_type="job",
                file_path=job_path or "",
                source_table=source_table,
                target_table=target_table,
            )

        kitchen_path = self._get_kitchen_path()

        if not os.path.exists(kitchen_path):
            return KettleExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Kitchen script not found: {kitchen_path}",
                duration_seconds=0,
                error_message="Kettle not installed",
                task_id=task_id,
                job_type="job",
                file_path=job_path or "",
            )

        # 构建命令
        cmd = [kitchen_path]

        if job_path:
            # 文件模式
            cmd.extend(["-file", job_path])
        elif repository and job_name:
            # 仓库模式
            cmd.extend(["-rep", repository])
            if directory:
                cmd.extend(["-dir", directory])
            cmd.extend(["-job", job_name])
        else:
            return KettleExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Must specify either job_path or repository/job_name",
                duration_seconds=0,
                error_message="Invalid parameters",
                task_id=task_id,
                job_type="job",
            )

        # 日志级别
        cmd.extend(["-level", log_level])

        # 参数
        if params:
            for key, value in params.items():
                cmd.extend([f"-param:{key}={value}"])

        # 执行
        result = self._execute_command(cmd)

        # 填充扩展字段
        result.task_id = task_id
        result.job_type = "job"
        result.file_path = job_path or ""
        result.source_table = source_table
        result.target_table = target_table

        # 执行后置回调
        self._execute_post_callbacks(result, context)

        return result

    def execute_transformation(
        self,
        trans_path: Optional[str] = None,
        repository: Optional[str] = None,
        directory: Optional[str] = None,
        trans_name: Optional[str] = None,
        params: Optional[Dict[str, str]] = None,
        log_level: str = "Basic",
        context: Optional[Dict[str, Any]] = None,
        task_id: str = "",
        source_table: str = "",
        target_table: str = "",
    ) -> KettleExecutionResult:
        """
        执行 Kettle 转换 (.ktr)

        Args:
            trans_path: 转换文件路径（文件模式）
            repository: 仓库名称（仓库模式）
            directory: 目录路径（仓库模式）
            trans_name: 转换名称（仓库模式）
            params: 参数字典
            log_level: 日志级别
            context: 执行上下文（传递给回调）
            task_id: 任务 ID（用于追踪）
            source_table: 源表名（用于元数据同步）
            target_table: 目标表名（用于元数据同步）

        Returns:
            KettleExecutionResult
        """
        context = context or {}
        context.update({
            "job_type": "transformation",
            "trans_path": trans_path,
            "repository": repository,
            "trans_name": trans_name,
            "task_id": task_id,
            "source_table": source_table,
            "target_table": target_table,
        })

        # 执行前置回调
        if trans_path and not self._execute_pre_callbacks(trans_path, context):
            return KettleExecutionResult(
                success=False,
                exit_code=-2,
                stdout="",
                stderr="Execution cancelled by pre-execution callback",
                duration_seconds=0,
                error_message="Cancelled by callback",
                task_id=task_id,
                job_type="transformation",
                file_path=trans_path or "",
                source_table=source_table,
                target_table=target_table,
            )

        pan_path = self._get_pan_path()

        if not os.path.exists(pan_path):
            return KettleExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Pan script not found: {pan_path}",
                duration_seconds=0,
                error_message="Kettle not installed",
                task_id=task_id,
                job_type="transformation",
                file_path=trans_path or "",
            )

        # 构建命令
        cmd = [pan_path]

        if trans_path:
            # 文件模式
            cmd.extend(["-file", trans_path])
        elif repository and trans_name:
            # 仓库模式
            cmd.extend(["-rep", repository])
            if directory:
                cmd.extend(["-dir", directory])
            cmd.extend(["-trans", trans_name])
        else:
            return KettleExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Must specify either trans_path or repository/trans_name",
                duration_seconds=0,
                error_message="Invalid parameters",
                task_id=task_id,
                job_type="transformation",
            )

        # 日志级别
        cmd.extend(["-level", log_level])

        # 参数
        if params:
            for key, value in params.items():
                cmd.extend([f"-param:{key}={value}"])

        # 执行
        result = self._execute_command(cmd)

        # 填充扩展字段
        result.task_id = task_id
        result.job_type = "transformation"
        result.file_path = trans_path or ""
        result.source_table = source_table
        result.target_table = target_table

        # 执行后置回调
        self._execute_post_callbacks(result, context)

        return result

    def _execute_command(self, cmd: list) -> KettleExecutionResult:
        """执行命令并返回结果"""
        logger.info(f"Executing Kettle command: {' '.join(cmd)}")

        start_time = datetime.utcnow()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                env=self._build_env(),
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            # 截断日志
            stdout = result.stdout
            stderr = result.stderr
            if len(stdout.split("\n")) > self.config.max_log_lines:
                lines = stdout.split("\n")
                stdout = "\n".join(lines[:self.config.max_log_lines])
                stdout += f"\n... (truncated, {len(lines) - self.config.max_log_lines} more lines)"

            # 解析统计信息
            rows_read, rows_written, rows_error = self._parse_kettle_output(stdout)

            # Kettle 退出码: 0=成功, 1=处理过程有错误, 2=参数错误, 7=无法初始化, 8=内存不足, 9=超时
            success = result.returncode == 0
            error_message = None
            if not success:
                if result.returncode == 1:
                    error_message = "Processing errors occurred"
                elif result.returncode == 2:
                    error_message = "Invalid arguments"
                elif result.returncode == 7:
                    error_message = "Initialization failed"
                elif result.returncode == 8:
                    error_message = "Out of memory"
                elif result.returncode == 9:
                    error_message = "Timeout"
                else:
                    error_message = f"Unknown error (exit code: {result.returncode})"

            return KettleExecutionResult(
                success=success,
                exit_code=result.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                rows_read=rows_read,
                rows_written=rows_written,
                rows_error=rows_error,
                error_message=error_message,
            )

        except subprocess.TimeoutExpired:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return KettleExecutionResult(
                success=False,
                exit_code=9,
                stdout="",
                stderr=f"Execution timed out after {self.config.timeout_seconds} seconds",
                duration_seconds=duration,
                error_message="Timeout",
            )
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Kettle execution failed: {e}")
            return KettleExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_seconds=duration,
                error_message=str(e),
            )

    def validate_job_file(self, job_path: str) -> Tuple[bool, Optional[str]]:
        """
        验证作业文件

        Returns:
            Tuple[is_valid, error_message]
        """
        if not os.path.exists(job_path):
            return False, f"File not found: {job_path}"

        if not job_path.endswith(".kjb"):
            return False, "Job file must have .kjb extension"

        # 检查文件是否为有效的 XML
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(job_path)
            root = tree.getroot()
            if root.tag != "job":
                return False, "Invalid Kettle job file: root element must be 'job'"
        except ET.ParseError as e:
            return False, f"Invalid XML: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"

        return True, None

    def validate_transformation_file(self, trans_path: str) -> Tuple[bool, Optional[str]]:
        """
        验证转换文件

        Returns:
            Tuple[is_valid, error_message]
        """
        if not os.path.exists(trans_path):
            return False, f"File not found: {trans_path}"

        if not trans_path.endswith(".ktr"):
            return False, "Transformation file must have .ktr extension"

        # 检查文件是否为有效的 XML
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(trans_path)
            root = tree.getroot()
            if root.tag != "transformation":
                return False, "Invalid Kettle transformation file: root element must be 'transformation'"
        except ET.ParseError as e:
            return False, f"Invalid XML: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"

        return True, None

    def get_status(self) -> Dict[str, Any]:
        """获取 Kettle 服务状态"""
        kitchen_path = self._get_kitchen_path()
        pan_path = self._get_pan_path()

        return {
            "kettle_home": self.config.kettle_home,
            "kettle_installed": os.path.exists(self.config.kettle_home),
            "kitchen_available": os.path.exists(kitchen_path),
            "pan_available": os.path.exists(pan_path),
            "java_home": self.config.java_home,
            "timeout_seconds": self.config.timeout_seconds,
            "max_log_lines": self.config.max_log_lines,
        }


# 全局实例
_kettle_bridge: Optional[KettleBridge] = None


def get_kettle_bridge() -> KettleBridge:
    """获取 Kettle 桥接服务实例（单例）"""
    global _kettle_bridge
    if _kettle_bridge is None:
        _kettle_bridge = KettleBridge()
    return _kettle_bridge
