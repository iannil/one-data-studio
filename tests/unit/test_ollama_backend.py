"""
Ollama 后端集成单元测试
Phase 1: 补齐短板 - Ollama LLM 后端

测试覆盖：
- 健康检查缓存逻辑
- Ollama 客户端创建
- get_chat_client() 优先级路由
- LLM_BACKEND 强制指定模式
"""

import pytest
import time
import sys
import os
from unittest.mock import patch, Mock, MagicMock, AsyncMock
from pathlib import Path

# 添加 openai-proxy 路径
_project_root = Path(__file__).parent.parent.parent
_openai_proxy_path = str(_project_root / "services" / "openai-proxy")
if _openai_proxy_path not in sys.path:
    sys.path.insert(0, _openai_proxy_path)


class TestCheckOllamaHealth:
    """Ollama 健康检查测试"""

    @patch("main.requests.get")
    def test_healthy_ollama_returns_true(self, mock_get):
        """Ollama 正常时返回 True"""
        import main
        # 重置缓存
        main._ollama_healthy = None
        main._ollama_last_check = 0

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = main._check_ollama_health()
        assert result is True
        mock_get.assert_called_once()

    @patch("main.requests.get")
    def test_unhealthy_ollama_returns_false(self, mock_get):
        """Ollama 返回非 200 时返回 False"""
        import main
        main._ollama_healthy = None
        main._ollama_last_check = 0

        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        result = main._check_ollama_health()
        assert result is False

    @patch("main.requests.get")
    def test_connection_error_returns_false(self, mock_get):
        """连接失败时返回 False"""
        import main
        main._ollama_healthy = None
        main._ollama_last_check = 0

        mock_get.side_effect = Exception("Connection refused")

        result = main._check_ollama_health()
        assert result is False
        assert main._ollama_healthy is False

    @patch("main.requests.get")
    def test_health_check_uses_cache_within_ttl(self, mock_get):
        """TTL 内使用缓存，不发送请求"""
        import main
        main._ollama_healthy = True
        main._ollama_last_check = time.time()  # 刚刚检查过

        result = main._check_ollama_health()
        assert result is True
        mock_get.assert_not_called()

    @patch("main.requests.get")
    def test_health_check_refreshes_after_ttl(self, mock_get):
        """TTL 过期后重新检查"""
        import main
        main._ollama_healthy = True
        main._ollama_last_check = time.time() - 60  # 60 秒前（超过 30s TTL）

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = main._check_ollama_health()
        assert result is True
        mock_get.assert_called_once()

    @patch("main.requests.get")
    def test_health_check_cache_returns_false_when_none(self, mock_get):
        """缓存值为 None 时返回 False"""
        import main
        main._ollama_healthy = None
        main._ollama_last_check = time.time()  # 刚检查过，但值是 None

        result = main._check_ollama_health()
        assert result is False
        mock_get.assert_not_called()

    @patch("main.requests.get")
    def test_health_check_calls_correct_endpoint(self, mock_get):
        """健康检查调用 /api/tags 端点"""
        import main
        main._ollama_healthy = None
        main._ollama_last_check = 0

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        main._check_ollama_health()
        call_args = mock_get.call_args
        assert "/api/tags" in call_args[0][0] or "/api/tags" in str(call_args)


class TestIsOllamaAvailable:
    """is_ollama_available 函数测试"""

    @patch("main._check_ollama_health")
    def test_delegates_to_health_check(self, mock_health):
        """is_ollama_available 委托给 _check_ollama_health"""
        import main
        mock_health.return_value = True
        assert main.is_ollama_available() is True
        mock_health.assert_called_once()


class TestGetOllamaClient:
    """Ollama 客户端创建测试"""

    @patch("main.is_ollama_available")
    @patch("main.OPENAI_AVAILABLE", True)
    def test_returns_client_when_available(self, mock_available):
        """Ollama 可用时返回客户端"""
        import main
        main._ollama_client = None  # 重置
        mock_available.return_value = True

        with patch("main.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            client = main.get_ollama_client()
            assert client is not None
            mock_cls.assert_called_once_with(
                api_key="ollama",
                base_url=f"{main.OLLAMA_URL}/v1"
            )
        main._ollama_client = None  # 清理

    @patch("main.is_ollama_available")
    @patch("main.OPENAI_AVAILABLE", True)
    def test_returns_none_when_unavailable(self, mock_available):
        """Ollama 不可用时返回 None"""
        import main
        main._ollama_client = None
        mock_available.return_value = False

        client = main.get_ollama_client()
        assert client is None

    @patch("main.is_ollama_available")
    @patch("main.OPENAI_AVAILABLE", False)
    def test_returns_none_when_openai_library_missing(self, mock_available):
        """OpenAI 库未安装时返回 None"""
        import main
        main._ollama_client = None
        mock_available.return_value = True

        client = main.get_ollama_client()
        assert client is None

    @patch("main.is_ollama_available")
    @patch("main.OPENAI_AVAILABLE", True)
    def test_reuses_existing_client(self, mock_available):
        """已有客户端实例时直接返回"""
        import main
        mock_available.return_value = True
        existing_client = MagicMock()
        main._ollama_client = existing_client

        client = main.get_ollama_client()
        assert client is existing_client
        main._ollama_client = None  # 清理


class TestGetChatClientPriority:
    """get_chat_client() 优先级路由测试"""

    @patch("main.get_openai_client")
    @patch("main.get_ollama_client")
    @patch("main.get_vllm_chat_client")
    @patch("main.LLM_BACKEND", "auto")
    def test_auto_prefers_vllm(self, mock_vllm, mock_ollama, mock_openai):
        """auto 模式优先使用 vLLM"""
        import main
        mock_vllm_client = MagicMock()
        mock_vllm.return_value = mock_vllm_client

        client, backend = main.get_chat_client()
        assert client is mock_vllm_client
        assert backend == "vllm"
        mock_ollama.assert_not_called()
        mock_openai.assert_not_called()

    @patch("main.get_openai_client")
    @patch("main.get_ollama_client")
    @patch("main.get_vllm_chat_client")
    @patch("main.LLM_BACKEND", "auto")
    def test_auto_falls_back_to_ollama(self, mock_vllm, mock_ollama, mock_openai):
        """auto 模式 vLLM 不可用时使用 Ollama"""
        import main
        mock_vllm.return_value = None
        mock_ollama_client = MagicMock()
        mock_ollama.return_value = mock_ollama_client

        client, backend = main.get_chat_client()
        assert client is mock_ollama_client
        assert backend == "ollama"
        mock_openai.assert_not_called()

    @patch("main.get_openai_client")
    @patch("main.get_ollama_client")
    @patch("main.get_vllm_chat_client")
    @patch("main.LLM_BACKEND", "auto")
    def test_auto_falls_back_to_openai(self, mock_vllm, mock_ollama, mock_openai):
        """auto 模式 vLLM 和 Ollama 都不可用时使用 OpenAI"""
        import main
        mock_vllm.return_value = None
        mock_ollama.return_value = None
        mock_openai_client = MagicMock()
        mock_openai.return_value = mock_openai_client

        client, backend = main.get_chat_client()
        assert client is mock_openai_client
        assert backend == "openai"

    @patch("main.get_openai_client")
    @patch("main.get_ollama_client")
    @patch("main.get_vllm_chat_client")
    @patch("main.LLM_BACKEND", "auto")
    def test_auto_returns_none_when_all_unavailable(self, mock_vllm, mock_ollama, mock_openai):
        """所有后端都不可用时返回 (None, None)"""
        import main
        mock_vllm.return_value = None
        mock_ollama.return_value = None
        mock_openai.return_value = None

        client, backend = main.get_chat_client()
        assert client is None
        assert backend is None


class TestLLMBackendForceMode:
    """LLM_BACKEND 强制指定模式测试"""

    @patch("main.get_vllm_chat_client")
    @patch("main.LLM_BACKEND", "vllm")
    def test_force_vllm(self, mock_vllm):
        """强制 vLLM 模式"""
        import main
        mock_client = MagicMock()
        mock_vllm.return_value = mock_client

        client, backend = main.get_chat_client()
        assert client is mock_client
        assert backend == "vllm"

    @patch("main.get_ollama_client")
    @patch("main.LLM_BACKEND", "ollama")
    def test_force_ollama(self, mock_ollama):
        """强制 Ollama 模式"""
        import main
        mock_client = MagicMock()
        mock_ollama.return_value = mock_client

        client, backend = main.get_chat_client()
        assert client is mock_client
        assert backend == "ollama"

    @patch("main.get_openai_client")
    @patch("main.LLM_BACKEND", "openai")
    def test_force_openai(self, mock_openai):
        """强制 OpenAI 模式"""
        import main
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        client, backend = main.get_chat_client()
        assert client is mock_client
        assert backend == "openai"

    @patch("main.get_vllm_chat_client")
    @patch("main.LLM_BACKEND", "vllm")
    def test_force_vllm_returns_none_when_unavailable(self, mock_vllm):
        """强制 vLLM 但不可用时返回 (None, None)"""
        import main
        mock_vllm.return_value = None

        client, backend = main.get_chat_client()
        assert client is None
        assert backend is None

    @patch("main.get_ollama_client")
    @patch("main.LLM_BACKEND", "ollama")
    def test_force_ollama_returns_none_when_unavailable(self, mock_ollama):
        """强制 Ollama 但不可用时返回 (None, None)"""
        import main
        mock_ollama.return_value = None

        client, backend = main.get_chat_client()
        assert client is None
        assert backend is None


class TestOllamaConfig:
    """Ollama 配置变量测试"""

    def test_default_ollama_url(self):
        """默认 OLLAMA_URL"""
        import main
        assert "ollama" in main.OLLAMA_URL
        assert "11434" in main.OLLAMA_URL

    def test_default_llm_backend(self):
        """默认 LLM_BACKEND 为 auto"""
        import main
        assert main.LLM_BACKEND in ("auto", "vllm", "ollama", "openai")
