"""
网页内容抓取工具
Sprint 17: Agent 工具扩展

功能:
- 抓取网页内容
- 提取文本、链接、图片
- URL 白名单安全控制
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
import re
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import BaseTool, ToolSchema

logger = logging.getLogger(__name__)


@dataclass
class WebContent:
    """网页内容"""
    url: str
    title: str
    text: str
    links: List[Dict[str, str]]
    images: List[str]
    metadata: Dict[str, Any]


class WebBrowserTool(BaseTool):
    """
    网页浏览器工具
    Sprint 17: Agent 工具扩展

    安全特性:
    - URL 白名单
    - 请求超时限制
    - 内容大小限制
    - User-Agent 模拟
    """

    name = "web_browser"
    description = "抓取网页内容。可以获取网页的文本、链接和图片。用于从互联网获取信息。"
    parameters = [
        ToolSchema("url", "string", "要抓取的网页 URL", required=True),
        ToolSchema("extract_links", "boolean", "是否提取链接", default=True),
        ToolSchema("extract_images", "boolean", "是否提取图片 URL", default=False),
        ToolSchema("max_length", "integer", "最大返回文本长度", default=5000),
    ]

    # 默认白名单域名
    DEFAULT_WHITELIST = [
        "wikipedia.org",
        "github.com",
        "stackoverflow.com",
        "docs.python.org",
        "developer.mozilla.org",
        "baidu.com",
        "zhihu.com",
        "csdn.net",
    ]

    # 默认黑名单域名
    DEFAULT_BLACKLIST = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "internal",
        "private",
    ]

    DEFAULT_TIMEOUT = 30  # 秒
    MAX_CONTENT_SIZE = 5 * 1024 * 1024  # 5MB
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.whitelist = config.get("whitelist", self.DEFAULT_WHITELIST) if config else self.DEFAULT_WHITELIST
        self.blacklist = config.get("blacklist", self.DEFAULT_BLACKLIST) if config else self.DEFAULT_BLACKLIST
        self.timeout = config.get("timeout", self.DEFAULT_TIMEOUT) if config else self.DEFAULT_TIMEOUT
        self.enable_whitelist = config.get("enable_whitelist", False) if config else False

    def _validate_url(self, url: str) -> tuple[bool, str]:
        """验证 URL 安全性"""
        try:
            parsed = urlparse(url)

            # 检查协议
            if parsed.scheme not in ("http", "https"):
                return False, f"不支持的协议: {parsed.scheme}"

            # 检查黑名单
            for blocked in self.blacklist:
                if blocked in parsed.netloc.lower():
                    return False, f"URL 在黑名单中: {parsed.netloc}"

            # 检查白名单（如果启用）
            if self.enable_whitelist:
                allowed = False
                for domain in self.whitelist:
                    if domain in parsed.netloc.lower():
                        allowed = True
                        break
                if not allowed:
                    return False, f"URL 不在白名单中: {parsed.netloc}"

            return True, ""

        except Exception as e:
            return False, f"URL 解析失败: {str(e)}"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行网页抓取"""
        url = kwargs.get("url")
        extract_links = kwargs.get("extract_links", True)
        extract_images = kwargs.get("extract_images", False)
        max_length = kwargs.get("max_length", 5000)

        if not url:
            return {"success": False, "error": "URL is required"}

        # 验证 URL
        is_valid, error = self._validate_url(url)
        if not is_valid:
            return {"success": False, "error": error}

        try:
            # 延迟导入
            try:
                import aiohttp
                from bs4 import BeautifulSoup
            except ImportError:
                return {
                    "success": False,
                    "error": "Required libraries not installed. Install with: pip install aiohttp beautifulsoup4"
                }

            # 发起请求
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self.DEFAULT_USER_AGENT}
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    # 检查状态码
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {response.reason}"
                        }

                    # 检查内容大小
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > self.MAX_CONTENT_SIZE:
                        return {
                            "success": False,
                            "error": f"Content too large: {int(content_length) / 1024 / 1024:.1f}MB"
                        }

                    html = await response.text()

            # 解析 HTML
            soup = BeautifulSoup(html, "html.parser")

            # 移除脚本和样式
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # 提取标题
            title = soup.title.string if soup.title else ""

            # 提取文本
            text = soup.get_text(separator="\n", strip=True)

            # 清理文本（移除多余空行）
            text = re.sub(r'\n{3,}', '\n\n', text)

            # 限制长度
            if len(text) > max_length:
                text = text[:max_length] + "...[truncated]"

            result = {
                "success": True,
                "url": url,
                "title": title,
                "text": text,
                "content_length": len(text),
            }

            # 提取链接
            if extract_links:
                links = []
                for a in soup.find_all("a", href=True)[:50]:  # 限制链接数量
                    href = a["href"]
                    link_text = a.get_text(strip=True)
                    if href.startswith(("http://", "https://")):
                        links.append({"url": href, "text": link_text[:100]})
                result["links"] = links

            # 提取图片
            if extract_images:
                images = []
                for img in soup.find_all("img", src=True)[:20]:  # 限制图片数量
                    src = img["src"]
                    if src.startswith(("http://", "https://")):
                        images.append(src)
                result["images"] = images

            logger.info(f"Successfully fetched {url}, content length: {len(text)}")
            return result

        except asyncio.TimeoutError:
            return {"success": False, "error": f"Request timeout after {self.timeout}s"}
        except Exception as e:
            logger.error(f"Web fetch failed for {url}: {e}")
            return {"success": False, "error": str(e)}
