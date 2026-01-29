"""
tests/unit/conftest.py
单元测试配置 - 处理 agent-api 模块导入路径

由于 agent-api 目录使用连字符，无法作为 Python 包直接导入。
此配置文件为需要 agent-api 模块的测试添加正确的 sys.path。

注意：路径添加顺序很重要！项目根目录必须在最前面，
这样 `from services.shared import ...` 才能找到正确的 services 包。
不添加包含 services/ 子目录的路径，避免命名空间冲突。
"""

import sys
from pathlib import Path

# 项目根目录 - 必须在最前面
_project_root = Path(__file__).parent.parent.parent

# 先添加服务特定路径（使用 append 以便它们在项目根目录之后）
# 注意：不添加 data-api 目录，因为它包含 services/ 子目录，会导致命名空间冲突
_service_paths = [
    _project_root / "services" / "agent-api",
    # 不添加 services/data-api - 会导致 services 命名空间冲突
    _project_root / "services" / "data-api" / "src",
    _project_root / "services" / "model-api",
    _project_root / "services" / "openai-proxy",
    _project_root / "services" / "shared",
]

for path in _service_paths:
    if str(path) not in sys.path:
        sys.path.append(str(path))  # 使用 append 而不是 insert(0)

# 确保项目根目录在最前面（在 sys.path[0] 位置）
if str(_project_root) in sys.path:
    sys.path.remove(str(_project_root))
sys.path.insert(0, str(_project_root))
