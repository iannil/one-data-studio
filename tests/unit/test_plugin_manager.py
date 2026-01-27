"""
插件管理器单元测试
测试动态工具加载、版本管理、执行追踪、热重载
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, AsyncMock
from engine.plugin_manager import (
    PluginManager,
    ToolVersion,
    ToolMetadata,
    ToolExecutionRecord,
    ToolStatistics,
    ToolStatus,
    PluginSource,
    get_plugin_manager,
    tool,
)
from engine.base_tools import BaseTool, ToolSchema


class MockTool(BaseTool):
    """模拟工具类"""

    name = "mock_tool"
    description = "A mock tool for testing"
    parameters = [
        ToolSchema("input", "string", "Input value", required=True)
    ]

    def __init__(self, config=None):
        super().__init__(config)
        self.call_count = 0

    async def execute(self, input: str):
        self.call_count += 1
        return {
            "success": True,
            "result": f"processed: {input}"
        }


class FailingTool(BaseTool):
    """模拟失败工具类"""

    name = "failing_tool"
    description = "A tool that always fails"
    parameters = []

    async def execute(self):
        raise ValueError("Intentional failure")


class ToolVersionTest:
    """工具版本测试"""

    def test_version_from_string(self):
        """测试从字符串解析版本"""
        v = ToolVersion.from_string("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_version_with_pre_release(self):
        """测试带预发布版本的解析"""
        v = ToolVersion.from_string("1.2.3-alpha.1")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre_release == "alpha.1"

    def test_version_with_build(self):
        """测试带构建元数据的解析"""
        v = ToolVersion.from_string("1.2.3+build.123")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.build == "build.123"

    def test_version_comparison(self):
        """测试版本比较"""
        v1 = ToolVersion.from_string("1.2.3")
        v2 = ToolVersion.from_string("1.2.4")
        v3 = ToolVersion.from_string("2.0.0")

        assert v2 > v1
        assert v3 > v2
        assert v1 >= v1
        assert not (v1 > v2)

    def test_version_to_string(self):
        """测试版本转字符串"""
        v = ToolVersion(1, 2, 3, "alpha", "build")
        assert "1.2.3" in str(v)
        assert "alpha" in str(v)


class ToolMetadataTest:
    """工具元数据测试"""

    def test_metadata_creation(self):
        """测试元数据创建"""
        metadata = ToolMetadata(
            name="test_tool",
            version=ToolVersion(1, 0, 0),
            author="Test Author",
            description="Test tool",
            tags=["test", "example"],
            category="test",
        )
        assert metadata.name == "test_tool"
        assert str(metadata.version) == "1.0.0"
        assert metadata.author == "Test Author"
        assert "test" in metadata.tags


class ToolExecutionRecordTest:
    """工具执行记录测试"""

    def test_record_creation(self):
        """测试记录创建"""
        record = ToolExecutionRecord(
            tool_name="test_tool",
            start_time=1000.0,
            end_time=1001.5,
            duration_ms=1500,
            success=True,
            input_params={"input": "test"},
            output={"result": "ok"},
        )
        assert record.tool_name == "test_tool"
        assert record.duration_ms == 1500
        assert record.success is True

    def test_sensitive_parameter_sanitization(self):
        """测试敏感参数清理"""
        record = ToolExecutionRecord(
            tool_name="test_tool",
            start_time=1000.0,
            end_time=1001.0,
            duration_ms=1000,
            success=True,
            input_params={
                "username": "user1",
                "password": "secret123",
                "api_key": "key123",
            },
            output={},
        )
        sanitized = record._sanitize_params(record.input_params)
        assert sanitized["username"] == "user1"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["api_key"] == "***REDACTED***"

    def test_to_dict(self):
        """测试转换为字典"""
        record = ToolExecutionRecord(
            tool_name="test_tool",
            start_time=1000.0,
            end_time=1001.0,
            duration_ms=1000,
            success=True,
            input_params={"input": "test"},
            output={},
        )
        d = record.to_dict()
        assert d["tool_name"] == "test_tool"
        assert d["duration_ms"] == 1000
        assert d["success"] is True


class ToolStatisticsTest:
    """工具统计测试"""

    def test_statistics_initialization(self):
        """测试统计初始化"""
        stats = ToolStatistics()
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0

    def test_statistics_update_successful(self):
        """测试更新成功统计"""
        stats = ToolStatistics()
        record = ToolExecutionRecord(
            tool_name="test",
            start_time=1000.0,
            end_time=1001.0,
            duration_ms=1000,
            success=True,
            input_params={},
            output={},
        )
        stats.update(record)
        assert stats.total_calls == 1
        assert stats.successful_calls == 1
        assert stats.failed_calls == 0
        assert stats.avg_duration_ms == 1000

    def test_statistics_update_failure(self):
        """测试更新失败统计"""
        stats = ToolStatistics()
        record = ToolExecutionRecord(
            tool_name="test",
            start_time=1000.0,
            end_time=1001.0,
            duration_ms=1000,
            success=False,
            input_params={},
            output=None,
            error="Test error",
        )
        stats.update(record)
        assert stats.total_calls == 1
        assert stats.successful_calls == 0
        assert stats.failed_calls == 1
        assert stats.last_error == "Test error"

    def test_statistics_aggregation(self):
        """测试统计聚合"""
        stats = ToolStatistics()

        for i in range(5):
            record = ToolExecutionRecord(
                tool_name="test",
                start_time=1000.0,
                end_time=1000.0 + i * 100,
                duration_ms=i * 100,
                success=i < 4,
                input_params={},
                output={},
            )
            stats.update(record)

        assert stats.total_calls == 5
        assert stats.successful_calls == 4
        assert stats.failed_calls == 1
        assert stats.max_duration_ms == 400


class PluginManagerTest:
    """插件管理器测试"""

    @pytest.fixture
    def manager(self):
        """创建插件管理器实例（不加载内置工具）"""
        config = {
            "plugin_dirs": [],
            "enable_hot_reload": False,
            "enable_observability": True,
        }
        manager = PluginManager(config)
        # 清空内置工具
        manager._tools.clear()
        manager._tool_metadata.clear()
        manager._tool_status.clear()
        return manager

    def test_register_tool(self, manager):
        """测试注册工具"""
        tool = MockTool()
        metadata = ToolMetadata(
            name="mock_tool",
            version=ToolVersion(1, 0, 0),
            source=PluginSource.BUILTIN,
        )
        manager._register_tool(tool, metadata)

        assert "mock_tool" in manager._tools
        assert manager._tool_status["mock_tool"] == ToolStatus.LOADED

    def test_get_tool(self, manager):
        """测试获取工具"""
        tool = MockTool()
        metadata = ToolMetadata(name="mock_tool", version=ToolVersion(1, 0, 0))
        manager._register_tool(tool, metadata)

        retrieved = manager.get_tool("mock_tool")
        assert retrieved is not None
        assert retrieved.name == "mock_tool"

    def test_get_nonexistent_tool(self, manager):
        """测试获取不存在的工具"""
        retrieved = manager.get_tool("nonexistent")
        assert retrieved is None

    def test_list_tools(self, manager):
        """测试列出工具"""
        tool1 = MockTool()
        tool2 = MockTool()
        tool2.name = "another_tool"

        manager._register_tool(tool1, ToolMetadata(name="mock_tool", version=ToolVersion(1, 0, 0)))
        manager._register_tool(tool2, ToolMetadata(name="another_tool", version=ToolVersion(1, 0, 0)))

        tools = manager.list_tools()
        assert len(tools) == 2

    def test_list_tools_with_filter(self, manager):
        """测试带过滤列出工具"""
        tool1 = MockTool()
        manager._register_tool(tool1, ToolMetadata(
            name="mock_tool",
            version=ToolVersion(1, 0, 0),
            category="test"
        ))

        manager._tool_status["mock_tool"] = ToolStatus.DISABLED

        tools = manager.list_tools(status=ToolStatus.DISABLED)
        assert len(tools) == 1
        assert tools[0]["status"] == "disabled"

    def test_get_tool_info(self, manager):
        """测试获取工具详细信息"""
        tool = MockTool()
        metadata = ToolMetadata(
            name="mock_tool",
            version=ToolVersion(1, 0, 0),
            author="Test",
            category="test",
        )
        manager._register_tool(tool, metadata)

        info = manager.get_tool_info("mock_tool")
        assert info is not None
        assert info["name"] == "mock_tool"
        assert info["metadata"]["author"] == "Test"

    def test_unload_tool(self, manager):
        """测试卸载工具"""
        tool = MockTool()
        manager._register_tool(tool, ToolMetadata(name="mock_tool", version=ToolVersion(1, 0, 0)))

        result = manager.unload_tool("mock_tool")
        assert result is True
        assert manager._tool_status["mock_tool"] == ToolStatus.UNLOADED

    def test_unload_nonexistent_tool(self, manager):
        """测试卸载不存在的工具"""
        result = manager.unload_tool("nonexistent")
        assert result is False

    def test_disable_enable_tool(self, manager):
        """测试禁用/启用工具"""
        tool = MockTool()
        manager._register_tool(tool, ToolMetadata(name="mock_tool", version=ToolVersion(1, 0, 0)))

        # 禁用
        result = manager.disable_tool("mock_tool")
        assert result is True
        assert manager._tool_status["mock_tool"] == ToolStatus.DISABLED

        # 启用
        result = manager.enable_tool("mock_tool")
        assert result is True
        assert manager._tool_status["mock_tool"] == ToolStatus.LOADED

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, manager):
        """测试成功执行工具"""
        tool = MockTool()
        manager._register_tool(tool, ToolMetadata(name="mock_tool", version=ToolVersion(1, 0, 0)))

        result = await manager.execute_tool("mock_tool", input="test")
        assert result["success"] is True
        assert "processed: test" in result["result"]

    @pytest.mark.asyncio
    async def test_execute_tool_failure(self, manager):
        """测试执行工具失败"""
        tool = FailingTool()
        manager._register_tool(tool, ToolMetadata(name="failing_tool", version=ToolVersion(1, 0, 0)))

        result = await manager.execute_tool("failing_tool")
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, manager):
        """测试执行不存在的工具"""
        result = await manager.execute_tool("nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_tool_with_observability(self, manager):
        """测试带可观测性的工具执行"""
        tool = MockTool()
        manager._register_tool(tool, ToolMetadata(name="mock_tool", version=ToolVersion(1, 0, 0)))

        await manager.execute_tool("mock_tool", input="test")

        records = manager.get_execution_records("mock_tool")
        assert len(records) > 0
        assert records[0]["success"] is True

    def test_get_statistics(self, manager):
        """测试获取统计信息"""
        tool = MockTool()
        manager._register_tool(tool, ToolMetadata(name="mock_tool", version=ToolVersion(1, 0, 0)))

        # 添加执行记录
        record = ToolExecutionRecord(
            tool_name="mock_tool",
            start_time=1000.0,
            end_time=1001.0,
            duration_ms=1000,
            success=True,
            input_params={},
            output={},
        )
        manager._add_execution_record(record)
        manager._update_statistics("mock_tool", record)

        stats = manager.get_statistics("mock_tool")
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["success_rate"] == 1.0

    def test_get_all_statistics(self, manager):
        """测试获取所有工具统计"""
        tool1 = MockTool()
        tool2 = MockTool()
        tool2.name = "tool2"

        manager._register_tool(tool1, ToolMetadata(name="mock_tool", version=ToolVersion(1, 0, 0)))
        manager._register_tool(tool2, ToolMetadata(name="tool2", version=ToolVersion(1, 0, 0)))

        all_stats = manager.get_statistics()
        assert "mock_tool" in all_stats
        assert "tool2" in all_stats

    def test_version_upgrade(self, manager):
        """测试版本升级"""
        tool1 = MockTool()
        tool2 = MockTool()

        # 注册旧版本
        manager._register_tool(tool1, ToolMetadata(
            name="mock_tool",
            version=ToolVersion(1, 0, 0),
        ))

        # 注册新版本
        manager._register_tool(tool2, ToolMetadata(
            name="mock_tool",
            version=ToolVersion(2, 0, 0),
        ))

        metadata = manager._tool_metadata["mock_tool"]
        assert str(metadata.version) == "2.0.0"

    def test_version_downgrade_prevented(self, manager):
        """测试防止版本降级"""
        tool1 = MockTool()
        tool2 = MockTool()

        # 注册新版本
        manager._register_tool(tool1, ToolMetadata(
            name="mock_tool",
            version=ToolVersion(2, 0, 0),
        ))

        # 尝试注册旧版本
        manager._register_tool(tool2, ToolMetadata(
            name="mock_tool",
            version=ToolVersion(1, 0, 0),
        ))

        metadata = manager._tool_metadata["mock_tool"]
        assert str(metadata.version) == "2.0.0"

    def test_dependency_check(self, manager):
        """测试依赖检查"""
        tool = MockTool()
        metadata = ToolMetadata(
            name="mock_tool",
            version=ToolVersion(1, 0, 0),
            dependencies=["nonexistent_tool"],
        )
        manager._register_tool(tool, metadata)

        # 依赖不满足，工具应该处于 ERROR 状态
        assert manager._tool_status.get("mock_tool") in (ToolStatus.ERROR, ToolStatus.UNLOADED)

    def test_execution_records_limit(self, manager):
        """测试执行记录限制"""
        manager._max_execution_records = 5

        for i in range(10):
            record = ToolExecutionRecord(
                tool_name="test",
                start_time=float(i),
                end_time=float(i + 1),
                duration_ms=1000,
                success=True,
                input_params={},
                output={},
            )
            manager._add_execution_record(record)

        # 应该只保留最新的 5 条
        assert len(manager._execution_records) <= 5


class TestPluginManagerSingleton:
    """插件管理器单例测试"""

    def test_get_plugin_manager_singleton(self):
        """测试获取单例实例"""
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        assert manager1 is manager2

    def test_get_plugin_manager_with_config(self):
        """测试带配置获取实例"""
        manager = get_plugin_manager({"enable_observability": False})
        assert manager is not None


class TestToolDecorator:
    """工具装饰器测试"""

    def test_tool_decorator(self):
        """测试 @tool 装饰器"""
        manager = get_plugin_manager()

        @tool(name="decorated_tool", version="1.0.0", tags=["test"])
        async def my_tool(x: int, y: int) -> int:
            return x + y

        # 工具应该被注册
        tool = manager.get_tool("decorated_tool")
        assert tool is not None


class TestHotReload:
    """热重载测试"""

    def test_file_watcher_not_started_by_default(self):
        """测试默认不启动文件监控"""
        manager = PluginManager({"enable_hot_reload": False})
        assert manager._watch_running is False

    def test_stop_file_watcher(self):
        """测试停止文件监控"""
        manager = PluginManager({"enable_hot_reload": False})
        manager._watch_running = True
        manager._watch_thread = threading.Thread(target=lambda: None)

        manager.stop_file_watcher()
        assert manager._watch_running is False


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_plugin_manager(self):
        """测试空插件管理器"""
        manager = PluginManager({"plugin_dirs": [], "enable_hot_reload": False})
        manager._tools.clear()
        manager._tool_metadata.clear()
        manager._tool_status.clear()

        tools = manager.list_tools()
        assert len(tools) == 0

    def test_execute_with_invalid_params(self):
        """测试使用无效参数执行"""
        manager = PluginManager({"plugin_dirs": [], "enable_hot_reload": False})
        manager._tools.clear()

        tool = MockTool()
        manager._register_tool(tool, ToolMetadata(name="mock_tool", version=ToolVersion(1, 0, 0)))

        # 缺少必需参数
        async def run():
            return await manager.execute_tool("mock_tool")  # 缺少 'input'

        import asyncio
        result = asyncio.run(run())
        # 参数验证应该失败
        assert "error" in result or result.get("success") is False


@pytest.mark.parametrize("version_str,expected_major,expected_minor,expected_patch", [
    ("1.0.0", 1, 0, 0),
    ("2.5.10", 2, 5, 10),
    ("0.0.1", 0, 0, 1),
    ("10.20.30", 10, 20, 30),
])
def test_version_parsing(version_str, expected_major, expected_minor, expected_patch):
    """参数化测试版本解析"""
    v = ToolVersion.from_string(version_str)
    assert v.major == expected_major
    assert v.minor == expected_minor
    assert v.patch == expected_patch


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services/bisheng_api/engine/plugin_manager", "--cov-report=term-missing"])
