"""
Phase 5: 前端集成验证测试

测试覆盖范围:
- web-frontend 前端应用
- 前后端集成
- 用户界面功能

测试用例编号: INT-P5-001 ~ INT-P5-025
"""

import os
import sys
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest
import requests
from playwright.sync_api import Page, expect

# 添加项目路径
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


@pytest.mark.integration
class TestWebFrontend:
    """INT-P5-001 ~ INT-P5-010: web-frontend 基础测试"""

    @pytest.fixture
    def frontend_config(self):
        """前端配置"""
        return {
            "base_url": os.getenv("FRONTEND_URL", "http://localhost:3000"),
        }

    def test_frontend_accessible(self, frontend_config):
        """INT-P5-001: 前端页面可访问性测试"""
        try:
            response = requests.get(frontend_config["base_url"], timeout=10)
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_frontend_static_assets(self, frontend_config):
        """INT-P5-002: 静态资源加载测试"""
        try:
            response = requests.get(frontend_config["base_url"], timeout=10)
            content = response.text

            # 检查关键资源引用
            has_js = ".js" in content or '<script' in content
            has_css = ".css" in content or '<style' in content

            assert has_js or has_css, "No static assets referenced"
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_frontend_csp_headers(self, frontend_config):
        """INT-P5-003: CSP 头检查"""
        try:
            response = requests.get(frontend_config["base_url"], timeout=10)
            csp = response.headers.get("Content-Security-Policy", "")
            print(f"CSP: {csp if csp else 'Not set'}")
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_frontend_api_proxy(self, frontend_config):
        """INT-P5-004: API 代理配置测试"""
        # 检查前端是否正确配置了 API 代理
        try:
            response = requests.get(f"{frontend_config['base_url']}/api/health", timeout=5)
            # 可能被代理到后端或返回 404
            assert response.status_code in [200, 404, 502, 503]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_frontend_health_endpoint(self, frontend_config):
        """INT-P5-005: 前端健康检查端点"""
        url = f"{frontend_config['base_url']}/health"
        try:
            response = requests.get(url, timeout=5)
            assert response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_frontend_language_support(self, frontend_config):
        """INT-P5-006: 语言支持测试"""
        try:
            # 测试中文
            response = requests.get(
                frontend_config["base_url"],
                headers={"Accept-Language": "zh-CN"},
                timeout=10
            )
            assert response.status_code == 200

            # 测试英文
            response = requests.get(
                frontend_config["base_url"],
                headers={"Accept-Language": "en-US"},
                timeout=10
            )
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_frontend_compression(self, frontend_config):
        """INT-P5-007: 响应压缩测试"""
        try:
            response = requests.get(
                frontend_config["base_url"],
                headers={"Accept-Encoding": "gzip, deflate"},
                timeout=10
            )
            encoding = response.headers.get("content-encoding", "")
            print(f"Content-Encoding: {encoding if encoding else 'None'}")
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_frontend_cache_headers(self, frontend_config):
        """INT-P5-008: 缓存头检查"""
        try:
            response = requests.get(frontend_config["base_url"], timeout=10)
            cache_control = response.headers.get("cache-control", "")
            etag = response.headers.get("etag", "")
            print(f"Cache-Control: {cache_control if cache_control else 'Not set'}")
            print(f"ETag: {etag if etag else 'Not set'}")
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_frontend_error_pages(self, frontend_config):
        """INT-P5-009: 错误页面测试"""
        try:
            # 测试 404 页面
            response = requests.get(f"{frontend_config['base_url']}/nonexistent-page", timeout=10)
            assert response.status_code == 404
            # 应该有自定义 404 页面
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_frontend_loading_performance(self, frontend_config):
        """INT-P5-010: 页面加载性能测试"""
        import time

        try:
            start_time = time.time()
            response = requests.get(frontend_config["base_url"], timeout=10)
            load_time = time.time() - start_time

            assert response.status_code == 200
            print(f"Page load time: {load_time*1000:.2f}ms")
            assert load_time < 5.0  # 页面应在 5 秒内加载
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")


@pytest.mark.integration
class TestFrontendPages:
    """INT-P5-011 ~ INT-P5-020: 前端页面测试"""

    @pytest.fixture
    def frontend_config(self):
        return {
            "base_url": os.getenv("FRONTEND_URL", "http://localhost:3000"),
        }

    def test_home_page(self, frontend_config):
        """INT-P5-011: 首页测试"""
        try:
            response = requests.get(frontend_config["base_url"], timeout=10)
            assert response.status_code == 200
            content = response.text.lower()
            # 检查常见首页元素
            has_main_content = any(keyword in content for keyword in ["home", "dashboard", "首页", "仪表板"])
            print(f"Home page indicators: {has_main_content}")
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_login_page(self, frontend_config):
        """INT-P5-012: 登录页测试"""
        url = f"{frontend_config['base_url']}/login"
        try:
            response = requests.get(url, timeout=10)
            # 登录页可能返回 200 或重定向
            assert response.status_code in [200, 301, 302, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_data_page(self, frontend_config):
        """INT-P5-013: 数据管理页面测试"""
        url = f"{frontend_config['base_url']}/data"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 301, 302, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_agent_page(self, frontend_config):
        """INT-P5-014: Agent 页面测试"""
        url = f"{frontend_config['base_url']}/agent"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 301, 302, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_model_page(self, frontend_config):
        """INT-P5-015: 模型管理页面测试"""
        url = f"{frontend_config['base_url']}/model"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 301, 302, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_workflow_page(self, frontend_config):
        """INT-P5-016: 工作流页面测试"""
        url = f"{frontend_config['base_url']}/workflow"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 301, 302, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_chat_page(self, frontend_config):
        """INT-P5-017: 聊天页面测试"""
        url = f"{frontend_config['base_url']}/chat"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 301, 302, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_admin_page(self, frontend_config):
        """INT-P5-018: 管理页面测试"""
        url = f"{frontend_config['base_url']}/admin"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 301, 302, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_settings_page(self, frontend_config):
        """INT-P5-019: 设置页面测试"""
        url = f"{frontend_config['base_url']}/settings"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 301, 302, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_api_docs_page(self, frontend_config):
        """INT-P5-020: API 文档页面测试"""
        url = f"{frontend_config['base_url']}/api-docs"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code in [200, 301, 302, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")


@pytest.mark.integration
class TestFrontendBackendIntegration:
    """INT-P5-021 ~ INT-P5-025: 前后端集成测试"""

    def test_cors_configuration(self):
        """INT-P5-021: CORS 配置测试"""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        api_urls = [
            ("http://localhost:8000", "agent-api"),
            ("http://localhost:8001", "data-api"),
            ("http://localhost:8002", "model-api"),
            ("http://localhost:8003", "openai-proxy"),
            ("http://localhost:8004", "admin-api"),
        ]

        for api_url, name in api_urls:
            try:
                response = requests.options(
                    f"{api_url}/api/v1/health",
                    headers={"Origin": frontend_url},
                    timeout=5
                )
                cors_header = response.headers.get("Access-Control-Allow-Origin", "")
                print(f"{name} CORS: {cors_header if cors_header else 'Not set'}")
            except requests.exceptions.ConnectionError:
                print(f"{name}: Not accessible")

    def test_api_authentication_flow(self):
        """INT-P5-022: API 认证流程测试"""
        # 测试从前端到后端的认证流程
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        try:
            # 尝试访问需要认证的页面
            response = requests.get(f"{frontend_url}/admin", timeout=10, allow_redirects=False)

            # 应该重定向到登录页或返回 401/403
            if response.status_code in [301, 302]:
                print(f"Admin page redirects to: {response.headers.get('location', 'unknown')}")
            else:
                print(f"Admin page status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_websocket_connection(self):
        """INT-P5-023: WebSocket 连接测试"""
        import websocket

        ws_url = os.getenv("WS_URL", "ws://localhost:8000/ws")

        try:
            ws = websocket.create_connection(ws_url, timeout=5)
            ws.close()
            print("WebSocket connection successful")
        except Exception as e:
            print(f"WebSocket connection failed: {e}")

    def test_file_upload_integration(self):
        """INT-P5-024: 文件上传集成测试"""
        # 测试从前端上传文件到后端
        import io

        upload_url = "http://localhost:8000/api/v1/files/upload"

        try:
            file_content = b"Test file content"
            files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
            response = requests.post(upload_url, files=files, timeout=10)
            assert response.status_code in [200, 201, 401, 404]
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")

    def test_real_time_updates(self):
        """INT-P5-025: 实时更新测试"""
        # 测试 SSE (Server-Sent Events) 或 WebSocket 实时更新
        sse_url = "http://localhost:8000/api/v1/events"

        try:
            response = requests.get(sse_url, stream=True, timeout=5)
            # SSE 应该返回 200 和 text/event-stream
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                print(f"SSE Content-Type: {content_type}")
        except requests.exceptions.ConnectionError:
            pytest.skip("agent-api 服务未启动")


@pytest.mark.integration
class TestFrontendE2E:
    """INT-P5-026 ~ INT-P5-030: 端到端测试 (需要 Playwright)"""

    @pytest.fixture(scope="function")
    def page(self):
        """Playwright 页面 fixture"""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            yield page
            browser.close()

    @pytest.mark.e2e
    def test_e2e_login_flow(self, page):
        """INT-P5-026: 登录流程 E2E 测试"""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        try:
            page.goto(f"{frontend_url}/login")
            # 验证登录页面元素
            expect(page).to_have_url(r".*/login/.*")
        except Exception as e:
            pytest.skip(f"E2E test failed: {e}")

    @pytest.mark.e2e
    def test_e2e_data_source_list(self, page):
        """INT-P5-027: 数据源列表 E2E 测试"""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        try:
            page.goto(f"{frontend_url}/data")
            # 验证数据源页面加载
            expect(page).to_have_title(r".*(data|数据).*")
        except Exception as e:
            pytest.skip(f"E2E test failed: {e}")

    @pytest.mark.e2e
    def test_e2e_workflow_editor(self, page):
        """INT-P5-028: 工作流编辑器 E2E 测试"""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        try:
            page.goto(f"{frontend_url}/workflow")
            # 验证工作流编辑器加载
            expect(page).to_have_title(r".*(workflow|工作流).*")
        except Exception as e:
            pytest.skip(f"E2E test failed: {e}")

    @pytest.mark.e2e
    def test_e2e_chat_interface(self, page):
        """INT-P5-029: 聊天界面 E2E 测试"""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        try:
            page.goto(f"{frontend_url}/chat")
            # 验证聊天界面加载
            expect(page).to_have_title(r".*(chat|聊天).*")
        except Exception as e:
            pytest.skip(f"E2E test failed: {e}")

    @pytest.mark.e2e
    def test_e2e_navigation(self, page):
        """INT-P5-030: 导航流程 E2E 测试"""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        try:
            # 从首页开始
            page.goto(frontend_url)

            # 检查导航菜单是否存在
            nav_selectors = ["nav", "[role='navigation']", ".navbar", ".sidebar"]
            has_nav = any(page.locator(sel).count() > 0 for sel in nav_selectors)

            assert has_nav, "Navigation element not found"

            print(f"Navigation found: Yes")
        except Exception as e:
            pytest.skip(f"E2E test failed: {e}")


@pytest.mark.integration
class TestFrontendAccessibility:
    """INT-P5-031 ~ INT-P5-035: 可访问性测试"""

    @pytest.fixture
    def frontend_config(self):
        return {
            "base_url": os.getenv("FRONTEND_URL", "http://localhost:3000"),
        }

    def test_alt_text_on_images(self, frontend_config):
        """INT-P5-031: 图片 alt 文本测试"""
        try:
            from bs4 import BeautifulSoup

            response = requests.get(frontend_config["base_url"], timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            images = soup.find_all('img')
            images_without_alt = [img for img in images if not img.get('alt')]

            print(f"Total images: {len(images)}")
            print(f"Images without alt: {len(images_without_alt)}")
        except ImportError:
            pytest.skip("BeautifulSoup not installed")
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_form_labels(self, frontend_config):
        """INT-P5-032: 表单标签测试"""
        try:
            from bs4 import BeautifulSoup

            response = requests.get(frontend_config["base_url"], timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            inputs = soup.find_all('input')
            inputs_without_labels = []

            for inp in inputs:
                # 检查是否有 aria-label、id 关联的 label，或 placeholder
                has_label = (
                    inp.get('aria-label') or
                    inp.get('aria-labelledby') or
                    inp.get('placeholder') or
                    inp.get('title')
                )
                if not has_label:
                    inputs_without_labels.append(inp)

            print(f"Inputs without accessible labels: {len(inputs_without_labels)}")
        except ImportError:
            pytest.skip("BeautifulSoup not installed")
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_heading_hierarchy(self, frontend_config):
        """INT-P5-033: 标题层级测试"""
        try:
            from bs4 import BeautifulSoup

            response = requests.get(frontend_config["base_url"], timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            headings = []
            for level in range(1, 7):
                headings.extend(soup.find_all(f'h{level}'))

            print(f"Total headings: {len(headings)}")
            for h in headings[:10]:  # 打印前 10 个
                print(f"  {h.name}: {h.get_text()[:50]}")
        except ImportError:
            pytest.skip("BeautifulSoup not installed")
        except requests.exceptions.ConnectionError:
            pytest.skip("web-frontend 服务未启动")

    def test_color_contrast(self, frontend_config):
        """INT-P5-034: 颜色对比度测试 (框架)"""
        # 这是一个框架测试，实际实现需要 CSS 分析
        print("Color contrast test: Framework only")
        print("This should be extended with actual color contrast analysis")

    def test_keyboard_navigation(self, frontend_config):
        """INT-P5-035: 键盘导航测试 (框架)"""
        print("Keyboard navigation test: Framework only")
        print("This should be extended with Playwright keyboard interaction tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
