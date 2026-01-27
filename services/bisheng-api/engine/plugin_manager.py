"""
Agent 工具插件管理器
Production: 动态工具发现、加载、版本管理和可观测性

功能：
1. 动态工具发现和加载
2. 工具版本管理
3. 工具依赖检查
4. 工具执行可观测性（追踪、统计）
5. 工具生命周期管理
6. 热重载支持
"""

import logging
import os
import sys
import time
import importlib
import inspect
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import json
import hashlib
from collections import defaultdict

# 导入工具基类
from .base_tools import BaseTool, ToolSchema

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """工具状态"""
    LOADED = "loaded"
    ERROR = "error"
    DISABLED = "disabled"
    LOADING = "loading"
    UNLOADED = "unloaded"


class PluginSource(Enum):
    """插件来源"""
    BUILTIN = "builtin"       # 内置工具
    FILESYSTEM = "filesystem"  # 文件系统加载
    DATABASE = "database"      # 数据库加载
    REMOTE = "remote"          # 远程加载
    REGISTRY = "registry"      # 工具注册表


@dataclass
class ToolVersion:
    """工具版本信息"""
    major: int = 1
    minor: int = 0
    patch: int = 0
    pre_release: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            version += f"-{self.pre_release}"
        if self.build:
            version += f"+{self.build}"
        return version

    @classmethod
    def from_string(cls, version_str: str) -> "ToolVersion":
        """从字符串解析版本"""
        parts = version_str.split("+")
        build = parts[1] if len(parts) > 1 else None
        version_str = parts[0]

        parts = version_str.split("-")
        pre_release = parts[1] if len(parts) > 1 else None
        version_str = parts[0]

        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return cls(major, minor, patch, pre_release, build)

    def __gt__(self, other: "ToolVersion") -> bool:
        """版本比较"""
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        if self.patch != other.patch:
            return self.patch > other.patch
        # 简化：忽略 pre_release 和 build 的比较
        return False


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    version: ToolVersion
    author: str = ""
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    source: PluginSource = PluginSource.BUILTIN
    file_path: Optional[str] = None
    checksum: Optional[str] = None
    loaded_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None


@dataclass
class ToolExecutionRecord:
    """工具执行记录"""
    tool_name: str
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    input_params: Dict[str, Any]
    output: Any
    error: Optional[str] = None
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "input_params": self._sanitize_params(self.input_params),
            "error": self.error,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
        }

    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """清理敏感参数"""
        sensitive_keys = {"password", "token", "secret", "key", "auth"}
        sanitized = {}
        for k, v in params.items():
            if any(skw in k.lower() for skw in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized


@dataclass
class ToolStatistics:
    """工具统计信息"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: float = 0
    avg_duration_ms: float = 0
    max_duration_ms: float = 0
    min_duration_ms: float = float('inf')
    last_called_at: Optional[datetime] = None
    last_error: Optional[str] = None

    def update(self, record: ToolExecutionRecord) -> None:
        """更新统计"""
        self.total_calls += 1
        if record.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
            self.last_error = record.error

        self.total_duration_ms += record.duration_ms
        self.avg_duration_ms = self.total_duration_ms / self.total_calls
        self.max_duration_ms = max(self.max_duration_ms, record.duration_ms)
        self.min_duration_ms = min(self.min_duration_ms, record.duration_ms)
        self.last_called_at = datetime.fromtimestamp(record.end_time)


class PluginManager:
    """
    工具插件管理器

    功能：
    - 动态发现和加载工具
    - 版本管理
    - 依赖检查
    - 执行追踪和统计
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化插件管理器

        Args:
            config: 配置字典
                - plugin_dirs: 插件目录列表
                - enable_hot_reload: 是否启用热重载
                - max_execution_records: 最大执行记录数
                - enable_observability: 是否启用可观测性
        """
        self.config = config or {}
        self.plugin_dirs = self.config.get("plugin_dirs", [])
        self.enable_hot_reload = self.config.get("enable_hot_reload", False)
        self.max_execution_records = self.config.get("max_execution_records", 10000)
        self.enable_observability = self.config.get("enable_observability", True)

        # 工具存储
        self._tools: Dict[str, BaseTool] = {}
        self._tool_metadata: Dict[str, ToolMetadata] = {}
        self._tool_status: Dict[str, ToolStatus] = {}

        # 执行记录和统计
        self._execution_records: List[ToolExecutionRecord] = []
        self._statistics: Dict[str, ToolStatistics] = defaultdict(ToolStatistics)
        self._records_lock = threading.Lock()

        # 文件监控（用于热重载）
        self._file_mtimes: Dict[str, float] = {}
        self._watch_thread: Optional[threading.Thread] = None
        self._watch_running = False

        # 初始化
        self._initialize()

    def _initialize(self) -> None:
        """初始化插件管理器"""
        # 添加默认插件目录
        default_plugin_dir = Path(__file__).parent.parent / "plugins"
        if default_plugin_dir.exists() and str(default_plugin_dir) not in self.plugin_dirs:
            self.plugin_dirs.append(str(default_plugin_dir))

        # 自动发现和加载插件
        self._discover_plugins()

        # 启动文件监控
        if self.enable_hot_reload:
            self._start_file_watcher()

    def _discover_plugins(self) -> None:
        """发现插件"""
        logger.info("Discovering plugins...")

        # 1. 加载内置工具（从 tools.py）
        self._load_builtin_tools()

        # 2. 从插件目录加载
        for plugin_dir in self.plugin_dirs:
            self._load_from_directory(plugin_dir)

        logger.info(f"Plugin discovery complete. Loaded {len(self._tools)} tools.")

    def _load_builtin_tools(self) -> None:
        """加载内置工具"""
        from .tools import DEFAULT_TOOLS

        for tool_class in DEFAULT_TOOLS:
            try:
                tool = tool_class()
                self._register_tool(
                    tool,
                    ToolMetadata(
                        name=tool.name,
                        version=ToolVersion(1, 0, 0),
                        author="Bisheng Team",
                        description=tool.description,
                        source=PluginSource.BUILTIN,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to load builtin tool {tool_class.__name__}: {e}")

    def _load_from_directory(self, directory: str) -> None:
        """从目录加载插件"""
        plugin_path = Path(directory)

        if not plugin_path.exists():
            logger.warning(f"Plugin directory does not exist: {directory}")
            return

        # 遍历 Python 文件
        for py_file in plugin_path.glob("**/*.py"):
            if py_file.name.startswith("_"):
                continue

            self._load_plugin_file(py_file)

    def _load_plugin_file(self, file_path: Path) -> None:
        """从单个文件加载插件"""
        try:
            # 计算模块路径
            file_path_str = str(file_path)
            self._file_mtimes[file_path_str] = os.path.getmtime(file_path_str)

            # 动态导入模块
            module_path = self._get_module_path(file_path)
            if module_path is None:
                return

            spec = importlib.util.spec_from_file_location(module_path, file_path)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load spec for {file_path}")
                return

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_path] = module
            spec.loader.exec_module(module)

            # 查找 BaseTool 子类
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseTool) and
                    obj is not BaseTool):

                    tool = obj()
                    metadata = self._extract_metadata(tool, file_path_str)
                    self._register_tool(tool, metadata)

                    logger.debug(f"Loaded tool: {tool.name} from {file_path.name}")

        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {e}")

    def _get_module_path(self, file_path: Path) -> Optional[str]:
        """获取模块路径"""
        # 将文件路径转换为 Python 模块路径
        parts = file_path.with_suffix('').parts
        try:
            # 找到插件目录的索引
            for plugin_dir in self.plugin_dirs:
                dir_parts = Path(plugin_dir).parts
                if parts[:len(dir_parts)] == dir_parts:
                    module_parts = parts[len(dir_parts):]
                    return ".".join(module_parts)
        except Exception:
            pass

        return None

    def _extract_metadata(self, tool: BaseTool, file_path: str) -> ToolMetadata:
        """从工具提取元数据"""
        # 尝试从工具类获取元数据
        version = ToolVersion(1, 0, 0)
        author = ""
        tags = []

        if hasattr(tool, "__version__"):
            version = ToolVersion.from_string(tool.__version__)
        if hasattr(tool, "__author__"):
            author = tool.__author__
        if hasattr(tool, "__tags__"):
            tags = tool.__tags__

        # 计算文件校验和
        checksum = None
        try:
            with open(file_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception:
            pass

        return ToolMetadata(
            name=tool.name,
            version=version,
            author=author,
            description=tool.description,
            tags=tags,
            source=PluginSource.FILESYSTEM,
            file_path=file_path,
            checksum=checksum,
            loaded_at=datetime.now(),
            last_modified=datetime.fromtimestamp(os.path.getmtime(file_path)),
        )

    def _register_tool(
        self,
        tool: BaseTool,
        metadata: ToolMetadata,
    ) -> None:
        """
        注册工具

        Args:
            tool: 工具实例
            metadata: 工具元数据
        """
        tool_name = tool.name

        # 检查依赖
        if not self._check_dependencies(metadata):
            logger.warning(f"Tool {tool_name} dependencies not satisfied, skipping")
            self._tool_status[tool_name] = ToolStatus.ERROR
            return

        # 版本冲突检查
        if tool_name in self._tools:
            existing_version = self._tool_metadata[tool_name].version
            if metadata.version <= existing_version:
                logger.debug(
                    f"Tool {tool_name} version {metadata.version} <= {existing_version}, skipping"
                )
                return
            logger.info(f"Upgrading tool {tool_name} from {existing_version} to {metadata.version}")

        self._tools[tool_name] = tool
        self._tool_metadata[tool_name] = metadata
        self._tool_status[tool_name] = ToolStatus.LOADED

        logger.info(f"Registered tool: {tool_name} v{metadata.version}")

    def _check_dependencies(self, metadata: ToolMetadata) -> bool:
        """检查工具依赖"""
        for dep in metadata.dependencies:
            # 检查其他工具
            if dep.startswith("tool:"):
                tool_name = dep[5:]
                if tool_name not in self._tools:
                    logger.warning(f"Missing tool dependency: {tool_name}")
                    return False

            # 检查 Python 包
            else:
                try:
                    importlib.import_module(dep)
                except ImportError:
                    logger.warning(f"Missing Python dependency: {dep}")
                    return False

        return True

    # ==================== 工具查询 ====================

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(
        self,
        status: Optional[ToolStatus] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出工具

        Args:
            status: 按状态过滤
            category: 按分类过滤
            tags: 按标签过滤

        Returns:
            工具信息列表
        """
        result = []

        for name, tool in self._tools.items():
            tool_status = self._tool_status.get(name, ToolStatus.UNLOADED)
            metadata = self._tool_metadata.get(name)

            if status and tool_status != status:
                continue
            if category and metadata and metadata.category != category:
                continue
            if tags and metadata and not any(t in metadata.tags for t in tags):
                continue

            result.append({
                "name": name,
                "description": tool.description,
                "status": tool_status.value,
                "version": str(metadata.version) if metadata else "unknown",
                "author": metadata.author if metadata else "",
                "category": metadata.category if metadata else "",
                "tags": metadata.tags if metadata else [],
                "source": metadata.source.value if metadata else "",
            })

        return result

    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具详细信息"""
        tool = self.get_tool(name)
        if not tool:
            return None

        metadata = self._tool_metadata.get(name)
        statistics = self._statistics.get(name)

        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": [p.to_dict() for p in tool.parameters],
            "status": self._tool_status.get(name, ToolStatus.UNLOADED).value,
            "metadata": {
                "version": str(metadata.version) if metadata else "unknown",
                "author": metadata.author if metadata else "",
                "category": metadata.category if metadata else "",
                "tags": metadata.tags if metadata else [],
                "source": metadata.source.value if metadata else "",
                "file_path": metadata.file_path if metadata else "",
                "loaded_at": metadata.loaded_at.isoformat() if metadata and metadata.loaded_at else "",
            },
            "statistics": {
                "total_calls": statistics.total_calls if statistics else 0,
                "successful_calls": statistics.successful_calls if statistics else 0,
                "failed_calls": statistics.failed_calls if statistics else 0,
                "avg_duration_ms": statistics.avg_duration_ms if statistics else 0,
                "last_called_at": statistics.last_called_at.isoformat() if statistics and statistics.last_called_at else "",
            },
        }

    # ==================== 工具执行（带可观测性） ====================

    async def execute_tool(
        self,
        name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行工具（带追踪和统计）

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            执行结果
        """
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool not found: {name}"
            }

        # 生成追踪 ID
        trace_id = hashlib.md5(f"{name}:{time.time()}".encode()).hexdigest()[:16]

        start_time = time.time()
        result = None
        error = None
        success = False

        try:
            # 验证参数
            is_valid, errors = tool.validate_params(kwargs)
            if not is_valid:
                error = f"Parameter validation failed: {', '.join(errors)}"
            else:
                # 执行工具
                result = await tool.execute(**kwargs)
                success = result.get("success", True) if isinstance(result, dict) else True

        except Exception as e:
            error = str(e)
            success = False
            logger.error(f"Tool {name} execution failed: {e}", exc_info=True)

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # 记录执行
        if self.enable_observability:
            record = ToolExecutionRecord(
                tool_name=name,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                success=success,
                input_params=kwargs,
                output=result if success else None,
                error=error,
                trace_id=trace_id,
            )
            self._add_execution_record(record)
            self._update_statistics(name, record)

        return result if success else {
            "success": False,
            "error": error,
            "trace_id": trace_id,
        }

    def _add_execution_record(self, record: ToolExecutionRecord) -> None:
        """添加执行记录"""
        with self._records_lock:
            self._execution_records.append(record)

            # 限制记录数量
            if len(self._execution_records) > self.max_execution_records:
                self._execution_records.pop(0)

    def _update_statistics(self, tool_name: str, record: ToolExecutionRecord) -> None:
        """更新工具统计"""
        self._statistics[tool_name].update(record)

    # ==================== 执行记录查询 ====================

    def get_execution_records(
        self,
        tool_name: Optional[str] = None,
        limit: int = 100,
        success_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        获取执行记录

        Args:
            tool_name: 工具名称过滤
            limit: 返回数量
            success_only: 只返回成功的记录

        Returns:
            执行记录列表
        """
        records = self._execution_records

        if tool_name:
            records = [r for r in records if r.tool_name == tool_name]
        if success_only:
            records = [r for r in records if r.success]

        # 按时间倒序
        records = sorted(records, key=lambda r: r.start_time, reverse=True)

        return [r.to_dict() for r in records[:limit]]

    def get_statistics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        if tool_name:
            stats = self._statistics.get(tool_name, ToolStatistics())
            return {
                "tool_name": tool_name,
                "total_calls": stats.total_calls,
                "successful_calls": stats.successful_calls,
                "failed_calls": stats.failed_calls,
                "success_rate": (
                    stats.successful_calls / stats.total_calls
                    if stats.total_calls > 0 else 0
                ),
                "avg_duration_ms": stats.avg_duration_ms,
                "max_duration_ms": stats.max_duration_ms,
                "min_duration_ms": (
                    stats.min_duration_ms
                    if stats.min_duration_ms != float('inf') else 0
                ),
                "last_called_at": (
                    stats.last_called_at.isoformat()
                    if stats.last_called_at else ""
                ),
                "last_error": stats.last_error,
            }

        return {
            name: self.get_statistics(name)
            for name in self._tools.keys()
        }

    # ==================== 热重载 ====================

    def _start_file_watcher(self) -> None:
        """启动文件监控线程"""
        self._watch_running = True
        self._watch_thread = threading.Thread(
            target=self._file_watcher_loop,
            daemon=True,
            name="PluginFileWatcher",
        )
        self._watch_thread.start()
        logger.info("Plugin file watcher started")

    def _file_watcher_loop(self) -> None:
        """文件监控循环"""
        while self._watch_running:
            try:
                time.sleep(5)  # 每 5 秒检查一次
                self._check_file_changes()
            except Exception as e:
                logger.error(f"File watcher error: {e}")

    def _check_file_changes(self) -> None:
        """检查文件变化"""
        for file_path, old_mtime in list(self._file_mtimes.items()):
            try:
                new_mtime = os.path.getmtime(file_path)
                if new_mtime > old_mtime:
                    logger.info(f"Detected change in {file_path}, reloading...")
                    self._reload_plugin(file_path)
                    self._file_mtimes[file_path] = new_mtime
            except FileNotFoundError:
                logger.warning(f"Plugin file removed: {file_path}")
                del self._file_mtimes[file_path]

    def _reload_plugin(self, file_path: str) -> None:
        """重新加载插件"""
        try:
            # 移除旧模块
            module_path = self._get_module_path(Path(file_path))
            if module_path and module_path in sys.modules:
                del sys.modules[module_path]

            # 重新加载
            self._load_plugin_file(Path(file_path))

            logger.info(f"Reloaded plugin from {file_path}")

        except Exception as e:
            logger.error(f"Failed to reload plugin {file_path}: {e}")

    def stop_file_watcher(self) -> None:
        """停止文件监控"""
        self._watch_running = False
        if self._watch_thread:
            self._watch_thread.join(timeout=5)
        logger.info("Plugin file watcher stopped")

    # ==================== 生命周期管理 ====================

    def reload_all(self) -> None:
        """重新加载所有插件"""
        logger.info("Reloading all plugins...")

        # 清空现有工具
        self._tools.clear()
        self._tool_metadata.clear()
        self._tool_status.clear()

        # 重新发现
        self._discover_plugins()

    def unload_tool(self, name: str) -> bool:
        """卸载工具"""
        if name in self._tools:
            del self._tools[name]
            self._tool_status[name] = ToolStatus.UNLOADED
            logger.info(f"Unloaded tool: {name}")
            return True
        return False

    def enable_tool(self, name: str) -> bool:
        """启用工具"""
        if name in self._tools and self._tool_status.get(name) == ToolStatus.DISABLED:
            self._tool_status[name] = ToolStatus.LOADED
            return True
        return False

    def disable_tool(self, name: str) -> bool:
        """禁用工具"""
        if name in self._tools:
            self._tool_status[name] = ToolStatus.DISABLED
            return True
        return False

    def shutdown(self) -> None:
        """关闭插件管理器"""
        logger.info("Shutting down plugin manager...")
        self.stop_file_watcher()


# ==================== 全局实例 ====================

_plugin_manager: Optional[PluginManager] = None
_manager_lock = threading.Lock()


def get_plugin_manager(config: Dict[str, Any] = None) -> PluginManager:
    """获取全局插件管理器实例"""
    global _plugin_manager

    if _plugin_manager is None:
        with _manager_lock:
            if _plugin_manager is None:
                _plugin_manager = PluginManager(config)

    return _plugin_manager


# ==================== 装饰器 ====================

def tool(
    name: str,
    version: str = "1.0.0",
    author: str = "",
    category: str = "general",
    tags: List[str] = None,
    dependencies: List[str] = None,
):
    """
    工具装饰器

    用于将函数转换为工具的装饰器。

    Args:
        name: 工具名称
        version: 工具版本
        author: 作者
        category: 分类
        tags: 标签
        dependencies: 依赖列表

    Usage:
        @tool(name="my_tool", version="1.0.0", tags=["math"])
        async def my_function(x: int, y: int) -> int:
            return x + y
    """
    def decorator(func: Callable) -> Callable:
        # 创建工具类
        class DecoratedTool(BaseTool):
            name = name
            description = func.__doc__ or f"Tool generated from function {func.__name__}"
            parameters = []  # TODO: 从类型注解提取参数
            __version__ = version
            __author__ = author
            __tags__ = tags or []
            __category__ = category

            async def execute(self, **kwargs):
                return await func(**kwargs)

        # 注册到插件管理器
        manager = get_plugin_manager()
        metadata = ToolMetadata(
            name=name,
            version=ToolVersion.from_string(version),
            author=author,
            description=func.__doc__ or "",
            tags=tags or [],
            category=category,
            dependencies=dependencies or [],
            source=PluginSource.BUILTIN,
        )

        manager._register_tool(DecoratedTool(), metadata)

        return func

    return decorator
