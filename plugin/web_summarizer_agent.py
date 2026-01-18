"""
Web Summarizer Agent - 网页内容总结Agent（支持JavaScript渲染）

该Agent可以：
1. 通过爬虫技术获取指定网页的内容
2. 支持JavaScript动态渲染的网站（使用Playwright）
3. 对网页内容进行智能总结
4. 回答用户关于网页内容的提问

使用方式：
1. 复制到 plugin/ 目录下自动加载
2. 对系统说："总结这个网页的内容：http://example.com"

依赖安装：
    pip install playwright
    playwright install chromium
"""

from core.agent import Agent
from core.base_model import Message
from core.prompt.template_model import PromptTemplate
import logging
import re
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ================================
# 提示词模板
# ================================

system_instructions = """
你是一位专业的网页内容分析专家，擅长从网页中提取关键信息并进行总结。

你需要能够：
1. 识别用户提供的网页URL
2. 判断用户的需求（总结全文、提取关键信息、回答特定问题等）
3. 提取网页的主要内容，忽略广告、导航等无关信息
4. 根据用户需求生成结构化的总结报告
"""

core_instructions = """
# 任务流程

1. 分析用户请求，提取以下信息：
   - url: 网页的完整URL地址
   - task: 用户想要执行的任务类型（summary/extract/question）
   - question: 如果用户有特定问题，提取问题内容
   - focus: 用户特别关注的内容方向（可选）

2. 验证URL的有效性：
   - 确保URL格式正确（http://或https://开头）
   - 识别URL中的域名信息

3. 在data字段中返回结构化的请求信息

# 返回格式

在 data 字段中包含以下信息：
- url: 完整的网页URL
- task: 任务类型（"summary"表示总结，"extract"表示提取特定信息，"question"表示回答问题）
- question: 用户的特定问题（如果有）
- focus: 关注的重点方向（可选）
- language: 输出语言（默认中文）
"""

data_fields = """
{
  "url": "string       // 网页的完整URL地址",
  "task": "string      // 任务类型：summary(总结)、extract(提取)、question(回答问题)",
  "question": "string  // 用户的特定问题（可选）",
  "focus": "string     // 关注的重点方向（可选）",
  "language": "string  // 输出语言，默认中文"
}
"""


# ================================
# Agent类
# ================================

class WebSummarizerAgent(Agent):
    """
    Web Summarizer Agent - 网页内容获取和格式化Agent（支持JavaScript）

    功能特性：
    1. 使用Playwright支持JavaScript动态渲染的网站
    2. 自动回退到requests（速度更快）
    3. 智能内容提取和格式化
    4. 将规范化的内容传递给general_agent进行总结

    注意：此Agent只负责获取和格式化网页内容，总结由general_agent完成
    """

    # HTTP请求头配置
    _headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # Playwright可用性标志
    _playwright_available = False

    def __init__(self):
        super().__init__(
            name="web_summarizer_agent",
            description="专门用于获取和格式化网页内容，支持JavaScript动态渲染。可以爬取指定网页的内容，进行格式化处理，然后传递给general_agent进行智能总结。适用于新闻文章、博客、社区、单页应用等各类网页。",
            handles=[
                "总结网页", "网页总结", "网页内容",
                "爬取网页", "获取网页", "抓取网页",
                "分析网页", "网页分析",
                "文章总结", "总结文章",
                "提取内容", "网页提取",
                "http://", "https://"
            ],
            parameters={
                "url": "要总结的网页URL地址",
                "task": "任务类型（summary/extract/question）",
                "question": "关于网页的特定问题（可选）"
            }
        )

        self.prompt_template = PromptTemplate(
            system_instructions=system_instructions,
            available_agents=None,
            core_instructions=core_instructions,
            data_fields=data_fields
        )

        # 检查Playwright是否可用
        try:
            import playwright
            self._playwright_available = True
            logger.info(f"✓ {self.name} 初始化成功 (Playwright支持: 已启用)")
        except ImportError:
            self._playwright_available = False
            logger.info(f"✓ {self.name} 初始化成功 (Playwright支持: 未安装，将使用requests)")

    def _validate_url(self, url: str) -> bool:
        """验证URL格式"""
        if not url:
            return False
        pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        return pattern.match(url) is not None

    def _extract_urls(self, text: str) -> list:
        """从文本中提取URL"""
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        return url_pattern.findall(text)

    def _fetch_with_playwright(self, url: str) -> Dict[str, Any]:
        """
        使用Playwright获取JavaScript渲染的网页内容（在线程中运行以避免事件循环冲突）
        """
        import concurrent.futures
        import threading

        def run_playwright():
            """在独立线程中运行Playwright同步API"""
            from playwright.sync_api import sync_playwright

            try:
                logger.info(f"Playwright正在加载: {url}")

                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()

                    # 设置请求头
                    page.set_extra_http_headers(self._headers)

                    try:
                        # 访问页面
                        page.goto(url, wait_until="networkidle", timeout=15000)

                        # 等待动态内容加载
                        page.wait_for_timeout(2000)

                        # 提取标题
                        title = page.title()

                        # 先移除广告和推荐元素
                        ad_selectors = [
                            '.ad', '.ads', '.advertisement',
                            '.recommend', '.related', '.suggestion',
                            '.sidebar', '.side-bar',
                            '.comment', '.comments',
                            '.footer', '.header',
                            'nav', '.navigation', '.menu',
                            '.banner', '.popup',
                            '.share', '.social',
                        ]

                        for selector in ad_selectors:
                            try:
                                elements = page.query_selector_all(selector)
                                for elem in elements:
                                    page.evaluate("element => element.remove()", elem)
                            except:
                                pass

                        # 尝试多个内容选择器（优先级从高到低）
                        content_selectors = [
                            'article',                              # HTML5 article标签
                            '[role="main"]',                        # ARIA main角色
                            'main',                                 # HTML5 main标签
                            '.article-content',                     # 常见文章内容类
                            '.post-content',                        # 帖子内容
                            '.bbs-content',                         # 小黑盒等社区
                            '.markdown-body',                       # Markdown渲染
                            '.content-body',                        # 内容主体
                            '.article-body',                        # 文章主体
                            '.post-body',                           # 帖子主体
                            '.detail-content',                      # 详情内容
                            '.thread-content',                      # 主题内容
                            '#content',                             # content ID
                            '.content',                             # content类
                        ]

                        text = ""
                        for selector in content_selectors:
                            try:
                                element = page.query_selector(selector)
                                if element:
                                    text = element.inner_text()
                                    if len(text) > 100:
                                        logger.info(f"Playwright使用选择器 '{selector}' 找到内容")
                                        break
                            except Exception as e:
                                logger.debug(f"选择器 '{selector}' 失败: {e}")
                                continue

                        # 如果没找到，获取整个body
                        if not text or len(text) < 100:
                            text = page.inner_text('body')

                        browser.close()

                        # 基本清理：移除多余空白，保留段落结构
                        lines = []
                        for line in text.split('\n'):
                            stripped = line.strip()
                            # 保留有内容的行（超过5个字符）
                            if len(stripped) > 5:
                                lines.append(stripped)

                        # 用双换行连接段落，保持可读性
                        text = '\n\n'.join(lines)

                        # 限制长度（30000字符约10000个中文字符）
                        max_length = 30000
                        if len(text) > max_length:
                            text = text[:max_length] + "\n\n[内容过长，已截断]"
                            logger.info(f"内容已截断到 {max_length} 字符")

                        logger.info(f"Playwright成功获取内容，标题: {title}, 长度: {len(text)}")

                        return {
                            "success": True,
                            "url": url,
                            "title": title.strip(),
                            "content": text,
                            "content_length": len(text),
                            "content_truncated": len(text) != len(text),
                            "method": "playwright"
                        }

                    except Exception as e:
                        browser.close()
                        logger.error(f"Playwright加载失败: {e}")
                        return {
                            "success": False,
                            "error": f"Playwright加载失败: {str(e)}"
                        }

            except Exception as e:
                logger.error(f"Playwright执行错误: {e}")
                return {
                    "success": False,
                    "error": f"Playwright执行失败: {str(e)}"
                }

        # 使用线程池执行，避免事件循环冲突
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_playwright)
                return future.result(timeout=30)  # 30秒超时
        except concurrent.futures.TimeoutError:
            logger.error("Playwright执行超时")
            return {
                "success": False,
                "error": "Playwright执行超时（30秒）"
            }
        except Exception as e:
            logger.error(f"Playwright线程执行错误: {e}")
            return {
                "success": False,
                "error": f"Playwright执行失败: {str(e)}"
            }

    def _fetch_with_requests(self, url: str) -> Dict[str, Any]:
        """
        使用requests + BeautifulSoup获取网页内容（回退方案）
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError as e:
            return {
                "success": False,
                "error": f"缺少必要库。请运行: pip install requests beautifulsoup4"
            }

        try:
            logger.info(f"使用requests获取网页: {url}")
            response = requests.get(url, headers=self._headers, timeout=15)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"无法访问网页，状态码: {response.status_code}"
                }

            soup = BeautifulSoup(response.content, 'html.parser')

            # 提取标题
            title = ""
            if soup.title:
                title = soup.title.string.strip()
            elif soup.find('h1'):
                title = soup.find('h1').get_text().strip()

            # 先移除广告、推荐、评论等无关元素
            ad_selectors = [
                '.ad', '.ads', '.advertisement', '.banner',
                '.recommend', '.related', '.suggestion',
                '.sidebar', '.side-bar', 'aside',
                '.comment', '.comments',
                'nav', '.navigation', '.menu',
                '.share', '.social', '.popup',
                '.footer', 'footer',
            ]

            for selector in ad_selectors:
                for element in soup.select(selector):
                    element.decompose()

            # 移除无关标签
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
                element.decompose()

            # 智能提取内容（按优先级）
            content_selectors = [
                'article',                              # HTML5 article标签
                '[role="main"]',                        # ARIA main角色
                'main',                                 # HTML5 main标签
                '.article-content',                     # 常见文章内容类
                '.post-content',                        # 帖子内容
                '.bbs-content',                         # 小黑盒等社区
                '.markdown-body',                       # Markdown渲染
                '.content-body',                        # 内容主体
                '.article-body',                        # 文章主体
                '.post-body',                           # 帖子主体
                '.detail-content',                      # 详情内容
                '.thread-content',                      # 主题内容
                '#content',                             # content ID
                '.content',                             # content类
            ]

            text = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator='\n', strip=True)
                    if len(text) > 100:
                        logger.info(f"requests使用选择器 '{selector}' 找到内容")
                        break

            if not text or len(text) < 100:
                for element in soup.find_all(class_=['nav', 'navigation', 'sidebar', 'menu', 'header', 'footer']):
                    element.decompose()
                text = soup.body.get_text(separator='\n', strip=True) if soup.body else soup.get_text(separator='\n', strip=True)

            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            if len(text) < 200:
                return {
                    "success": False,
                    "error": f"获取内容过少（{len(text)}字符），可能是JS动态页面。建议安装Playwright: pip install playwright && playwright install chromium",
                    "content": text,
                    "is_dynamic": True
                }

            # 限制长度（增加到30000字符，约10000个中文字符）
            max_length = 30000
            if len(text) > max_length:
                text = text[:max_length]
                logger.info(f"内容已截断，原始长度: {len(text)}, 保留: {max_length}")

            logger.info(f"requests成功获取内容，标题: {title}, 长度: {len(text)}")

            return {
                "success": True,
                "url": url,
                "title": title,
                "content": text,
                "content_length": len(text),
                "content_truncated": len(text) != len(text),
                "method": "requests"
            }

        except Exception as e:
            logger.error(f"获取网页失败: {e}")
            return {
                "success": False,
                "error": f"获取网页失败: {str(e)}"
            }

    def _fetch_webpage(self, url: str) -> Dict[str, Any]:
        """
        智能获取网页内容
        优先使用Playwright（支持JS），回退到requests
        """
        # 如果Playwright可用，先尝试
        if self._playwright_available:
            logger.info("尝试使用Playwright获取内容...")
            result = self._fetch_with_playwright(url)
            if result.get("success"):
                return result
            else:
                logger.warning(f"Playwright失败，回退到requests: {result.get('error')}")

        # 使用requests作为回退
        return self._fetch_with_requests(url)

    def _format_webpage_data(self, webpage_data: Dict[str, Any], task: str, question: Optional[str] = None) -> Dict[str, Any]:
        """
        格式化网页数据（不做总结，只做格式化）
        总结工作由general_agent完成
        """
        if not webpage_data.get("success"):
            return {
                "success": False,
                "error": webpage_data.get("error", "无法获取网页内容")
            }

        url = webpage_data.get("url", "")
        title = webpage_data.get("title", "未知标题")
        content = webpage_data.get("content", "")
        method = webpage_data.get("method", "unknown")
        content_length = len(content)
        is_truncated = webpage_data.get("content_truncated", False)

        # 构建格式化的网页信息（传递给general_agent）
        formatted_info = f"""# 网页内容

**标题**: {title}
**地址**: {url}
**获取方式**: {method.upper()}
**内容长度**: {content_length} 字符

## 正文内容

{content}
"""

        return {
            "success": True,
            "formatted_content": formatted_info,
            "raw_content": content,  # 原始内容
            "url": url,
            "title": title,
            "method": method,
            "task": task,
            "question": question
        }

    def run(self, message: Message) -> Message:
        """主处理逻辑"""
        data = message.data or {}
        url = data.get("url", "")

        # 从消息中提取URL
        if not url and hasattr(message, 'message') and message.message:
            urls = self._extract_urls(message.message)
            if urls:
                url = urls[0]

        if not url and message.task_list:
            for task in message.task_list:
                urls = self._extract_urls(task)
                if urls:
                    url = urls[0]
                    break

        # 验证URL
        if not url or not self._validate_url(url):
            return Message(
                status="error",
                task_list=message.task_list or ["处理网页请求"],
                data={"error": "未提供有效的网页URL。请提供完整的URL地址（以http://或https://开头）"},
                next_agent="none",
                agent_selection_reason="URL验证失败",
                message="请提供有效的网页URL地址，例如：https://example.com"
            )

        task = data.get("task", "summary")
        question = data.get("question")
        focus = data.get("focus")

        logger.info(f"{self.name} 开始处理: url={url}, task={task}")

        # 获取网页内容
        webpage_data = self._fetch_webpage(url)

        if not webpage_data.get("success"):
            error_msg = webpage_data.get("error", "未知错误")
            logger.error(f"获取网页失败: {error_msg}")
            return Message(
                status="error",
                task_list=["获取网页内容"],
                data={"url": url, "error": error_msg},
                next_agent="none",
                agent_selection_reason="网页获取失败",
                message=f"无法获取网页内容: {error_msg}"
            )

        # 格式化网页数据（不总结）
        formatted_data = self._format_webpage_data(webpage_data, task, question)

        # 传递格式化内容给general_agent进行总结
        return Message(
            status="success",
            task_list=["获取网页内容", "格式化数据"],
            data={
                "url": url,
                "title": webpage_data.get("title", ""),
                "formatted_content": formatted_data.get("formatted_content", ""),
                "raw_content": formatted_data.get("raw_content", ""),
                "content_length": len(formatted_data.get("raw_content", "")),
                "task": task,
                "question": question,
                "fetch_method": webpage_data.get("method", "unknown"),
                "webpage_info": {
                    "title": webpage_data.get("title", ""),
                    "url": url,
                    "method": webpage_data.get("method", "unknown"),
                }
            },
            next_agent="general_agent",
            agent_selection_reason="网页内容已获取并格式化，传递给general_agent进行智能总结",
            message=f"已成功获取网页: {webpage_data.get('title', url)}，内容长度: {len(formatted_data.get('raw_content', ''))}字符"
        )


"""
依赖安装说明：

为了支持JavaScript动态渲染的网站（如小黑盒、知乎等），需要安装Playwright：

1. 安装Python包：
   pip install playwright

2. 下载浏览器（首次使用）：
   playwright install chromium

注意：
- 如果不安装Playwright，agent会自动回退到requests模式（速度快但不支持JS）
- Playwright首次下载浏览器约需100-200MB空间
- 对于静态网页，requests模式更快更高效

支持的网站类型：
✅ 传统HTML网站（requests模式）
✅ React/Vue/Angular单页应用（Playwright模式）
✅ 动态加载内容的网站（Playwright模式）
✅ 社区网站、博客、新闻站等
"""
