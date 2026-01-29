"""
工作流扩展节点
Phase 6: Sprint 6.1

扩展节点模块，提供 HTTP 请求、数据过滤、数据库查询等功能。
"""

# 使用延迟导入避免循环依赖
# 节点在执行时会动态继承 BaseNode


class ExtensionNodeProxy:
    """扩展节点代理类，避免循环导入"""

    def __init__(self, node_id: str, node_type: str, config=None):
        self.node_id = node_id
        self.node_type = node_type
        self.config = config or {}
        self._wrapped = None

    def _wrap(self):
        """延迟包装为实际的节点类"""
        if self._wrapped is not None:
            return self._wrapped

        from ..nodes import BaseNode

        # 创建实际的节点类
        if self.node_type == "http":
            from .http import HTTPNodeImpl
            cls = type("HTTPNode", (HTTPNodeImpl, BaseNode), {})
        elif self.node_type == "filter":
            from .filter import FilterNodeImpl
            cls = type("FilterNode", (FilterNodeImpl, BaseNode), {})
        elif self.node_type == "database":
            from .database import DatabaseNodeImpl
            cls = type("DatabaseNode", (DatabaseNodeImpl, BaseNode), {})
        else:
            raise ValueError(f"Unknown extension node type: {self.node_type}")

        # 创建实例
        self._wrapped = cls(self.node_id, self.config)
        return self._wrapped

    async def execute(self, context):
        return await self._wrap().execute(context)

    def validate(self):
        return self._wrap().validate()


# 工厂函数
def create_extension_node(node_type: str, node_id: str, config=None):
    """创建扩展节点实例"""
    from .http import HTTPNodeImpl
    from .filter import FilterNodeImpl
    from .database import DatabaseNodeImpl

    # 获取实现类
    impl_classes = {
        "http": HTTPNodeImpl,
        "filter": FilterNodeImpl,
        "database": DatabaseNodeImpl,
    }

    impl_class = impl_classes.get(node_type)
    if not impl_class:
        raise ValueError(f"Unknown extension node type: {node_type}")

    # 动态创建继承自 BaseNode 的类
    from ..nodes import BaseNode
    node_class = type(
        f"{impl_class.__name__}",
        (impl_class, BaseNode),
        {}
    )

    return node_class(node_id, config)


# 扩展节点注册表（使用工厂函数）
EXTENSION_NODES = {
    "http": lambda node_id, config=None: create_extension_node("http", node_id, config),
    "filter": lambda node_id, config=None: create_extension_node("filter", node_id, config),
    "database": lambda node_id, config=None: create_extension_node("database", node_id, config),
}


__all__ = [
    "HTTPNode",
    "FilterNode",
    "DatabaseNode",
    "EXTENSION_NODES",
    "create_extension_node",
]
