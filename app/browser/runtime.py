"""Browser Runtime Abstraction Layer

This module provides an abstraction layer for different browser runtime implementations,
allowing the system to work with different browser backends (local Playwright, Daytona, etc.)
without coupling the browser agents to specific implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List
from dataclasses import dataclass
from pydantic import BaseModel, Field


@dataclass
class BrowserState:
    """Represents the current state of the browser."""
    url: str = ""
    title: str = ""
    tabs: List[Dict[str, Any]] = None
    pixels_above: int = 0
    pixels_below: int = 0
    viewport_height: int = 0
    interactive_elements: str = ""
    screenshot_base64: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.tabs is None:
            self.tabs = []


@dataclass
class BrowserActionResult:
    """Result of a browser action execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    screenshot_base64: Optional[str] = None


class BrowserRuntime(ABC):
    """Abstract base class for browser runtime implementations.

    This interface defines the contract that all browser runtimes must implement.
    BrowserAgent uses this interface without knowing the concrete implementation.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the browser runtime (launch browser, create context, etc.)."""
        ...

    @abstractmethod
    async def navigate(self, url: str) -> BrowserActionResult:
        """Navigate to a URL."""
        ...

    @abstractmethod
    async def go_back(self) -> BrowserActionResult:
        """Navigate back in history."""
        ...

    @abstractmethod
    async def refresh(self) -> BrowserActionResult:
        """Refresh the current page."""
        ...

    @abstractmethod
    async def click_element(self, index: int) -> BrowserActionResult:
        """Click an element by its index."""
        ...

    @abstractmethod
    async def input_text(self, index: int, text: str) -> BrowserActionResult:
        """Input text into an element by index."""
        ...

    @abstractmethod
    async def scroll_down(self, amount: Optional[int] = None) -> BrowserActionResult:
        """Scroll down by specified amount or default page height."""
        ...

    @abstractmethod
    async def scroll_up(self, amount: Optional[int] = None) -> BrowserActionResult:
        """Scroll up by specified amount or default page height."""
        ...

    @abstractmethod
    async def scroll_to_text(self, text: str) -> BrowserActionResult:
        """Scroll to make text visible."""
        ...

    @abstractmethod
    async def send_keys(self, keys: str) -> BrowserActionResult:
        """Send keyboard keys."""
        ...

    @abstractmethod
    async def get_dropdown_options(self, index: int) -> BrowserActionResult:
        """Get dropdown options for a select element."""
        ...

    @abstractmethod
    async def select_dropdown_option(self, index: int, text: str) -> BrowserActionResult:
        """Select a dropdown option by visible text."""
        ...

    @abstractmethod
    async def switch_tab(self, tab_id: int) -> BrowserActionResult:
        """Switch to a specific tab."""
        ...

    @abstractmethod
    async def open_tab(self, url: str) -> BrowserActionResult:
        """Open a new tab with the given URL."""
        ...

    @abstractmethod
    async def close_tab(self, tab_id: Optional[int] = None) -> BrowserActionResult:
        """Close a tab (current tab if tab_id not specified)."""
        ...

    @abstractmethod
    async def wait(self, seconds: int = 3) -> BrowserActionResult:
        """Wait for specified seconds."""
        ...

    @abstractmethod
    async def extract_content(self, goal: str) -> BrowserActionResult:
        """Extract content from the current page based on a goal."""
        ...

    @abstractmethod
    async def web_search(self, query: str) -> BrowserActionResult:
        """Perform a web search and navigate to results."""
        ...

    @abstractmethod
    async def get_state(self) -> BrowserState:
        """Get the current browser state including screenshot."""
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up browser resources (close browser, context, etc.)."""
        ...

    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        """Check if the browser runtime is initialized."""
        ...


class BrowserRuntimeConfig(BaseModel):
    """Configuration for browser runtime."""
    runtime: str = Field(default="local", description="Runtime type: 'local' or 'daytona'")
    headless: bool = Field(default=False, description="Run browser in headless mode")
    disable_security: bool = Field(default=True, description="Disable browser security features")
    extra_chromium_args: List[str] = Field(default_factory=list, description="Extra Chromium arguments")
    chrome_instance_path: Optional[str] = Field(default=None, description="Path to Chrome instance")
    wss_url: Optional[str] = Field(default=None, description="WebSocket URL for browser connection")
    cdp_url: Optional[str] = Field(default=None, description="CDP URL for browser connection")
    max_content_length: int = Field(default=2000, description="Maximum content length for extraction")
    new_context_config: Optional[Any] = Field(default=None, description="Browser context configuration")
    proxy: Optional[Any] = Field(default=None, description="Proxy settings for the browser")

    class Config:
        extra = "allow"


class LocalPlaywrightRuntime(BrowserRuntime):
    """Local browser runtime using Playwright directly via browser-use library."""

    def __init__(self, config: Optional[BrowserRuntimeConfig] = None):
        self.config = config or BrowserRuntimeConfig()
        self._browser = None
        self._context = None
        self._dom_service = None
        self._lock = None
        self._web_search_tool = None
        self._llm = None

    @property
    def is_initialized(self) -> bool:
        return self._context is not None

    async def _ensure_initialized(self):
        """Lazy initialization of browser and context."""
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()

        async with self._lock:
            if self.is_initialized:
                return

            # Lazy imports - only import browser-use when needed
            from browser_use import Browser as BrowserUseBrowser
            from browser_use import BrowserConfig
            from browser_use.browser.context import BrowserContext, BrowserContextConfig
            from browser_use.dom.service import DomService
            from app.tool.web_search import WebSearch
            from app.llm import LLM

            browser_config_kwargs = {
                "headless": self.config.headless,
                "disable_security": self.config.disable_security,
                "extra_chromium_args": self.config.extra_chromium_args,
            }

            if self.config.chrome_instance_path:
                browser_config_kwargs["chrome_instance_path"] = self.config.chrome_instance_path
            if self.config.wss_url:
                browser_config_kwargs["wss_url"] = self.config.wss_url
            if self.config.cdp_url:
                browser_config_kwargs["cdp_url"] = self.config.cdp_url

            if self.config.proxy:
                from browser_use.browser.browser import ProxySettings
                browser_config_kwargs["proxy"] = ProxySettings(
                    server=self.config.proxy.server,
                    username=self.config.proxy.username,
                    password=self.config.proxy.password,
                )

            self._browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))

            context_config = BrowserContextConfig()
            if self.config.new_context_config:
                context_config = self.config.new_context_config

            self._context = await self._browser.new_context(context_config)
            self._dom_service = DomService(await self._context.get_current_page())
            self._web_search_tool = WebSearch()
            self._llm = LLM()

    async def initialize(self) -> None:
        """Initialize the browser runtime."""
        await self._ensure_initialized()

    async def navigate(self, url: str) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            page = await self._context.get_current_page()
            await page.goto(url)
            await page.wait_for_load_state()
            return BrowserActionResult(success=True, message=f"Navigated to {url}")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Navigation failed: {str(e)}")

    async def go_back(self) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            await self._context.go_back()
            return BrowserActionResult(success=True, message="Navigated back")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Go back failed: {str(e)}")

    async def refresh(self) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            await self._context.refresh_page()
            return BrowserActionResult(success=True, message="Refreshed current page")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Refresh failed: {str(e)}")

    async def click_element(self, index: int) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            element = await self._context.get_dom_element_by_index(index)
            if not element:
                return BrowserActionResult(success=False, message="", error=f"Element with index {index} not found")
            download_path = await self._context._click_element_node(element)
            output = f"Clicked element at index {index}"
            if download_path:
                output += f" - Downloaded file to {download_path}"
            return BrowserActionResult(success=True, message=output)
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Click failed: {str(e)}")

    async def input_text(self, index: int, text: str) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            element = await self._context.get_dom_element_by_index(index)
            if not element:
                return BrowserActionResult(success=False, message="", error=f"Element with index {index} not found")
            await self._context._input_text_element_node(element, text)
            return BrowserActionResult(success=True, message=f"Input '{text}' into element at index {index}")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Input text failed: {str(e)}")

    async def scroll_down(self, amount: Optional[int] = None) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            scroll_amount = amount or self._context.config.browser_window_size["height"]
            await self._context.execute_javascript(f"window.scrollBy(0, {scroll_amount});")
            return BrowserActionResult(success=True, message=f"Scrolled down by {scroll_amount} pixels")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Scroll down failed: {str(e)}")

    async def scroll_up(self, amount: Optional[int] = None) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            scroll_amount = amount or self._context.config.browser_window_size["height"]
            await self._context.execute_javascript(f"window.scrollBy(0, {-scroll_amount});")
            return BrowserActionResult(success=True, message=f"Scrolled up by {scroll_amount} pixels")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Scroll up failed: {str(e)}")

    async def scroll_to_text(self, text: str) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            page = await self._context.get_current_page()
            locator = page.get_by_text(text, exact=False)
            await locator.scroll_into_view_if_needed()
            return BrowserActionResult(success=True, message=f"Scrolled to text: '{text}'")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Scroll to text failed: {str(e)}")

    async def send_keys(self, keys: str) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            page = await self._context.get_current_page()
            await page.keyboard.press(keys)
            return BrowserActionResult(success=True, message=f"Sent keys: {keys}")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Send keys failed: {str(e)}")

    async def get_dropdown_options(self, index: int) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            element = await self._context.get_dom_element_by_index(index)
            if not element:
                return BrowserActionResult(success=False, message="", error=f"Element with index {index} not found")
            page = await self._context.get_current_page()
            options = await page.evaluate(
                """
                (xpath) => {
                    const select = document.evaluate(xpath, document, null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (!select) return null;
                    return Array.from(select.options).map(opt => ({
                        text: opt.text,
                        value: opt.value,
                        index: opt.index
                    }));
                }
                """,
                element.xpath,
            )
            return BrowserActionResult(success=True, message="", data={"options": options})
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Get dropdown options failed: {str(e)}")

    async def select_dropdown_option(self, index: int, text: str) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            element = await self._context.get_dom_element_by_index(index)
            if not element:
                return BrowserActionResult(success=False, message="", error=f"Element with index {index} not found")
            page = await self._context.get_current_page()
            await page.select_option(element.xpath, label=text)
            return BrowserActionResult(success=True, message=f"Selected option '{text}' from dropdown at index {index}")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Select dropdown option failed: {str(e)}")

    async def switch_tab(self, tab_id: int) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            await self._context.switch_to_tab(tab_id)
            page = await self._context.get_current_page()
            await page.wait_for_load_state()
            return BrowserActionResult(success=True, message=f"Switched to tab {tab_id}")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Switch tab failed: {str(e)}")

    async def open_tab(self, url: str) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            await self._context.create_new_tab(url)
            return BrowserActionResult(success=True, message=f"Opened new tab with {url}")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Open tab failed: {str(e)}")

    async def close_tab(self, tab_id: Optional[int] = None) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            await self._context.close_current_tab()
            return BrowserActionResult(success=True, message="Closed current tab")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Close tab failed: {str(e)}")

    async def wait(self, seconds: int = 3) -> BrowserActionResult:
        import asyncio
        await asyncio.sleep(seconds)
        return BrowserActionResult(success=True, message=f"Waited for {seconds} seconds")

    async def extract_content(self, goal: str) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            page = await self._context.get_current_page()
            import markdownify

            content = markdownify.markdownify(await page.content())
            max_length = self.config.max_content_length

            prompt = f"""\
Your task is to extract the content of the page. You will be given a page and a goal, and you should extract all relevant information around this goal from the page. If the goal is vague, summarize the page. Respond in json format.
Extraction goal: {goal}

Page content:
{content[:max_length]}
"""

            messages = [{"role": "system", "content": prompt}]

            extraction_function = {
                "type": "function",
                "function": {
                    "name": "extract_content",
                    "description": "Extract specific information from a webpage based on a goal",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "extracted_content": {
                                "type": "object",
                                "description": "The content extracted from the page according to the goal",
                                "properties": {
                                    "text": {
                                        "type": "string",
                                        "description": "Text content extracted from the page",
                                    },
                                    "metadata": {
                                        "type": "object",
                                        "description": "Additional metadata about the extracted content",
                                        "properties": {
                                            "source": {
                                                "type": "string",
                                                "description": "Source of the extracted content",
                                            }
                                        },
                                    },
                                },
                            }
                        },
                        "required": ["extracted_content"],
                    },
                },
            }

            response = await self._llm.ask_tool(
                messages,
                tools=[extraction_function],
                tool_choice="required",
            )

            if response and response.tool_calls:
                import json
                args = json.loads(response.tool_calls[0].function.arguments)
                extracted_content = args.get("extracted_content", {})
                return BrowserActionResult(
                    success=True,
                    message="",
                    data={"extracted_content": extracted_content}
                )

            return BrowserActionResult(success=True, message="No content was extracted from the page.")
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Extract content failed: {str(e)}")

    async def web_search(self, query: str) -> BrowserActionResult:
        await self._ensure_initialized()
        try:
            search_response = await self._web_search_tool.execute(
                query=query, fetch_content=True, num_results=1
            )
            first_search_result = search_response.results[0]
            url_to_navigate = first_search_result.url

            page = await self._context.get_current_page()
            await page.goto(url_to_navigate)
            await page.wait_for_load_state()

            return BrowserActionResult(success=True, message="", data=search_response.model_dump())
        except Exception as e:
            return BrowserActionResult(success=False, message="", error=f"Web search failed: {str(e)}")

    async def get_state(self) -> BrowserState:
        await self._ensure_initialized()
        try:
            import base64

            state = await self._context.get_state()
            page = await self._context.get_current_page()

            await page.bring_to_front()
            await page.wait_for_load_state()

            screenshot = await page.screenshot(
                full_page=True, animations="disabled", type="jpeg", quality=100
            )
            screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")

            viewport_height = 0
            if hasattr(state, "viewport_info") and state.viewport_info:
                viewport_height = state.viewport_info.height
            elif hasattr(self._context, "config") and hasattr(self._context.config, "browser_window_size"):
                viewport_height = self._context.config.browser_window_size.get("height", 0)

            return BrowserState(
                url=state.url,
                title=state.title,
                tabs=[tab.model_dump() for tab in state.tabs],
                pixels_above=getattr(state, "pixels_above", 0),
                pixels_below=getattr(state, "pixels_below", 0),
                viewport_height=viewport_height,
                interactive_elements=(
                    state.element_tree.clickable_elements_to_string()
                    if state.element_tree
                    else ""
                ),
                screenshot_base64=screenshot_b64,
            )
        except Exception as e:
            return BrowserState(error=f"Failed to get browser state: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up browser resources."""
        if self._context is not None:
            await self._context.close()
            self._context = None
            self._dom_service = None
        if self._browser is not None:
            await self._browser.close()
            self._browser = None


class DaytonaRuntime(BrowserRuntime):
    """Daytona sandbox browser runtime.

    This implementation uses the Daytona sandbox for browser automation.
    Only loaded when runtime="daytona" is configured.
    """

    def __init__(self, config: Optional[BrowserRuntimeConfig] = None):
        self.config = config or BrowserRuntimeConfig()
        self._sandbox = None
        self._browser_message = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def _ensure_sandbox(self):
        """Ensure sandbox is available."""
        if self._initialized:
            return

        # Lazy imports - only import daytona when runtime=daytona
        from app.daytona.sandbox import create_sandbox, start_supervisord_session
        from app.config import config as app_config

        if self._sandbox is None:
            self._sandbox = await create_sandbox(password=app_config.daytona.VNC_password)
            start_supervisord_session(self._sandbox)
            self._initialized = True

    async def initialize(self) -> None:
        """Initialize the Daytona runtime."""
        await self._ensure_sandbox()

    async def _execute_browser_action(self, endpoint: str, params: dict = None, method: str = "POST") -> BrowserActionResult:
        await self._ensure_sandbox()
        try:
            import json
            import logging
            logger = logging.getLogger(__name__)

            url = f"http://localhost:8003/api/automation/{endpoint}"
            if method == "GET" and params:
                query_params = "&".join([f"{k}={v}" for k, v in params.items()])
                url = f"{url}?{query_params}"
                curl_cmd = f"curl -s -X {method} '{url}' -H 'Content-Type: application/json'"
            else:
                curl_cmd = f"curl -s -X {method} '{url}' -H 'Content-Type: application/json'"
                if params:
                    json_data = json.dumps(params)
                    curl_cmd += f" -d '{json_data}'"

            logger.debug(f"Executing curl command: {curl_cmd}")
            response = self._sandbox.process.exec(curl_cmd, timeout=30)

            if response.exit_code == 0:
                result = json.loads(response.result)
                result.setdefault("content", "")
                result.setdefault("role", "assistant")

                if "screenshot_base64" in result:
                    screenshot_data = result["screenshot_base64"]
                    # Validation could be added here
                    pass

                success_response = {
                    "success": result.get("success", False),
                    "message": result.get("message", "Browser action completed"),
                }
                for field in [
                    "url", "title", "element_count", "pixels_below", "ocr_text", "image_url"
                ]:
                    if field in result:
                        success_response[field] = result[field]

                self._browser_message = result
                return BrowserActionResult(
                    success=success_response["success"],
                    message=success_response["message"],
                    data=success_response,
                    screenshot_base64=result.get("screenshot_base64")
                )
            else:
                logger.error(f"Browser automation request failed: {response}")
                return BrowserActionResult(success=False, message="", error=f"Browser automation request failed: {response}")
        except Exception as e:
            logger.error(f"Error executing browser action: {e}")
            return BrowserActionResult(success=False, message="", error=f"Error executing browser action: {e}")

    async def navigate(self, url: str) -> BrowserActionResult:
        return await self._execute_browser_action("navigate_to", {"url": url})

    async def go_back(self) -> BrowserActionResult:
        return await self._execute_browser_action("go_back", {})

    async def refresh(self) -> BrowserActionResult:
        return await self._execute_browser_action("refresh", {})

    async def click_element(self, index: int) -> BrowserActionResult:
        return await self._execute_browser_action("click_element", {"index": index})

    async def input_text(self, index: int, text: str) -> BrowserActionResult:
        return await self._execute_browser_action("input_text", {"index": index, "text": text})

    async def scroll_down(self, amount: Optional[int] = None) -> BrowserActionResult:
        params = {"amount": amount} if amount is not None else {}
        return await self._execute_browser_action("scroll_down", params)

    async def scroll_up(self, amount: Optional[int] = None) -> BrowserActionResult:
        params = {"amount": amount} if amount is not None else {}
        return await self._execute_browser_action("scroll_up", params)

    async def scroll_to_text(self, text: str) -> BrowserActionResult:
        return await self._execute_browser_action("scroll_to_text", {"text": text})

    async def send_keys(self, keys: str) -> BrowserActionResult:
        return await self._execute_browser_action("send_keys", {"keys": keys})

    async def get_dropdown_options(self, index: int) -> BrowserActionResult:
        return await self._execute_browser_action("get_dropdown_options", {"index": index})

    async def select_dropdown_option(self, index: int, text: str) -> BrowserActionResult:
        return await self._execute_browser_action("select_dropdown_option", {"index": index, "text": text})

    async def switch_tab(self, tab_id: int) -> BrowserActionResult:
        return await self._execute_browser_action("switch_tab", {"page_id": tab_id})

    async def open_tab(self, url: str) -> BrowserActionResult:
        return await self._execute_browser_action("navigate_to", {"url": url})

    async def close_tab(self, tab_id: Optional[int] = None) -> BrowserActionResult:
        params = {"page_id": tab_id} if tab_id is not None else {}
        return await self._execute_browser_action("close_tab", params)

    async def wait(self, seconds: int = 3) -> BrowserActionResult:
        return await self._execute_browser_action("wait", {"seconds": seconds})

    async def extract_content(self, goal: str) -> BrowserActionResult:
        # Daytona doesn't have dedicated extract_content, return current state
        state = await self.get_state()
        return BrowserActionResult(
            success=True,
            message=f"Extracted content for goal: {goal}",
            data={"state": state.__dict__}
        )

    async def web_search(self, query: str) -> BrowserActionResult:
        # Daytona doesn't have built-in web search delegate to navigate
        return await self.navigate(f"https://www.google.com/search?q={query}")

    async def get_state(self) -> BrowserState:
        await self._ensure_sandbox()
        try:
            import json
            from app.daytona.tool_base import ThreadMessage

            message = self._browser_message
            if not message:
                return BrowserState()

            state = message.content if hasattr(message, 'content') else message
            screenshot = state.get("screenshot_base64")

            return BrowserState(
                url=state.get("url", ""),
                title=state.get("title", ""),
                tabs=[tab if isinstance(tab, dict) else (tab.model_dump() if hasattr(tab, 'model_dump') else {}) for tab in state.get("tabs", [])],
                pixels_above=state.get("pixels_above", 0),
                pixels_below=state.get("pixels_below", 0),
                viewport_height=state.get("viewport_height", 0),
                interactive_elements="",  # Daytona doesn't provide this directly
                screenshot_base64=screenshot,
            )
        except Exception:
            return BrowserState()

    async def cleanup(self) -> None:
        """Clean up Daytona resources."""
        if self._sandbox:
            # Don't delete sandbox by default, just cleanup local reference
            self._sandbox = None
            self._browser_message = None
            self._initialized = False


def create_browser_runtime(config: Optional[BrowserRuntimeConfig] = None) -> BrowserRuntime:
    """Factory function to create the appropriate browser runtime based on config.

    Args:
        config: Browser runtime configuration. If None, uses default config.

    Returns:
        BrowserRuntime instance appropriate for the configured runtime type.

    Raises:
        ValueError: If runtime type is not supported.
    """
    if config is None:
        from app.config import config as app_config
        if app_config.browser_config:
            config = BrowserRuntimeConfig(
                runtime=getattr(app_config.browser_config, "runtime", "local"),
                headless=app_config.browser_config.headless,
                disable_security=app_config.browser_config.disable_security,
                extra_chromium_args=app_config.browser_config.extra_chromium_args,
                chrome_instance_path=app_config.browser_config.chrome_instance_path,
                wss_url=app_config.browser_config.wss_url,
                cdp_url=app_config.browser_config.cdp_url,
                proxy=app_config.browser_config.proxy,
                max_content_length=app_config.browser_config.max_content_length,
                new_context_config=app_config.browser_config.new_context_config,
            )
        else:
            config = BrowserRuntimeConfig()

    if config.runtime == "local":
        return LocalPlaywrightRuntime(config)
    elif config.runtime == "daytona":
        return DaytonaRuntime(config)
    else:
        raise ValueError(f"Unsupported browser runtime: {config.runtime}. Supported: 'local', 'daytona'")