"""
Local Browser Module Implementation

Uses Playwright via browser-use for local browser automation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio
import base64
import logging
import uuid

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    BrowserModule,
    BrowserSession,
    BrowserState,
)

logger = logging.getLogger(__name__)


@dataclass
class _BrowserContext:
    """Internal browser context holder."""
    browser_session: Any = None


class LocalBrowserModule(BrowserModule):
    """
    Local browser implementation using Playwright via browser-use (v0.13+).

    This module provides browser automation without any external dependencies
    on Daytona or cloud services. It runs entirely locally using Playwright.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="browser",
            version="1.0.0",
            description="Local browser automation using Playwright via browser-use",
            author="AIPENSA",
            dependencies=[],
            provides=["browser_automation", "web_scraping", "screenshot", "content_extraction"],
            tags={"local", "playwright", "browser", "browser-use"},
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._config = config or {}
        self._sessions: Dict[str, _BrowserContext] = {}
        self._lock = asyncio.Lock()

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize the browser module."""
        self._runtime = runtime
        self._config = {**self._config, **config}
        self.state = ModuleState.INITIALIZED
        logger.info("LocalBrowserModule initialized")

    async def start(self) -> None:
        """Start the browser module."""
        # No-op for local browser - sessions are created lazily
        self.state = ModuleState.RUNNING
        logger.info("LocalBrowserModule started")

    async def stop(self) -> None:
        """Stop all browser sessions."""
        await self._close_all_sessions()
        self.state = ModuleState.STOPPED
        logger.info("LocalBrowserModule stopped")

    async def cleanup(self) -> None:
        """Clean up all resources."""
        await self._close_all_sessions()
        self._sessions.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("LocalBrowserModule cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "browser",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "active_sessions": len(self._sessions),
        }

    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute module operations."""
        if operation == "create_session":
            return await self.create_session(kwargs.get("url", "about:blank"), kwargs.get("config"))
        elif operation == "navigate":
            return await self.navigate(kwargs["session_id"], kwargs["url"], kwargs.get("wait_until", "networkidle"))
        elif operation == "get_state":
            return await self.get_state(kwargs["session_id"])
        elif operation == "execute_action":
            return await self.execute_action(kwargs["session_id"], kwargs["action"], kwargs["params"])
        elif operation == "extract_content":
            return await self.extract_content(kwargs["session_id"], kwargs["goal"], kwargs.get("selector"))
        elif operation == "take_screenshot":
            return await self.take_screenshot(kwargs["session_id"], kwargs.get("full_page", True), kwargs.get("format", "png"))
        elif operation == "close_session":
            return await self.close_session(kwargs["session_id"])
        elif operation == "list_sessions":
            return await self.list_sessions()
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported")

    async def _close_all_sessions(self) -> None:
        """Close all active browser sessions."""
        async with self._lock:
            for session_id, context in list(self._sessions.items()):
                try:
                    if context.browser_session:
                        await context.browser_session.stop()
                except Exception as e:
                    logger.warning(f"Error closing session {session_id}: {e}")
            self._sessions.clear()

    async def _ensure_session(self, session_id: str) -> _BrowserContext:
        """Get or create a browser session context."""
        async with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]

            # Create new browser session using browser-use v0.13+ API
            from browser_use.browser.session import BrowserProfile, BrowserSession

            # Build profile config
            profile_kwargs = {
                "headless": self._config.get("headless", False),
                "disable_security": self._config.get("disable_security", True),
            }

            # Add custom chrome path if provided
            if self._config.get("chrome_instance_path"):
                profile_kwargs["executable_path"] = self._config["chrome_instance_path"]

            # Proxy settings
            if self._config.get("proxy"):
                profile_kwargs["proxy"] = self._config["proxy"]

            # Viewport config
            viewport_width = self._config.get("viewport_width", 1280)
            viewport_height = self._config.get("viewport_height", 720)
            profile_kwargs["viewport"] = {"width": viewport_width, "height": viewport_height}

            profile = BrowserProfile(**profile_kwargs)
            browser_session = BrowserSession(browser_profile=profile)
            await browser_session.start()

            ctx = _BrowserContext(browser_session=browser_session)
            self._sessions[session_id] = ctx
            return ctx

    async def create_session(
        self,
        url: str = "about:blank",
        config: Optional[Dict[str, Any]] = None
    ) -> BrowserSession:
        """Create a new browser session."""
        session_id = str(uuid.uuid4())[:8]
        ctx = await self._ensure_session(session_id)

        session = BrowserSession(
            session_id=session_id,
            url=url,
            title="",
        )

        # Navigate to initial URL if provided
        if url and url != "about:blank":
            try:
                await ctx.browser_session.navigate_to(url)
                session.url = await ctx.browser_session.get_current_page_url()
                session.title = await ctx.browser_session.get_current_page_title()
            except Exception as e:
                logger.warning(f"Initial navigation failed: {e}")

        return session

    async def navigate(self, session_id: str, url: str, wait_until: str = "networkidle") -> Dict[str, Any]:
        """Navigate to URL."""
        ctx = await self._ensure_session(session_id)
        try:
            await ctx.browser_session.navigate_to(url)
            return {
                "success": True,
                "url": await ctx.browser_session.get_current_page_url(),
                "title": await ctx.browser_session.get_current_page_title(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_state(self, session_id: str) -> BrowserState:
        """Get current browser state."""
        ctx = await self._ensure_session(session_id)
        try:
            # Get browser state with screenshot
            state = await ctx.browser_session.get_browser_state_summary(include_screenshot=True)

            # Get screenshot
            screenshot_b64 = state.screenshot or ""

            # Get tabs
            tabs_info = await ctx.browser_session.get_tabs()
            tabs = []
            for tab in tabs_info:
                tabs.append({
                    "url": tab.url,
                    "title": tab.title,
                    "page_index": tab.target_id,
                })

            return BrowserState(
                session_id=session_id,
                url=state.url,
                title=state.title,
                viewport=state.viewport if hasattr(state, 'viewport') else {"width": 1280, "height": 720},
                screenshot=screenshot_b64,
                screenshot_base64=screenshot_b64,
                tabs=tabs,
                pixels_above=state.pixels_above if hasattr(state, 'pixels_above') else 0,
                pixels_below=state.pixels_below if hasattr(state, 'pixels_below') else 0,
                viewport_height=720,
                interactive_elements=str(state.dom_state) if hasattr(state, 'dom_state') else "",
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Failed to get browser state: {e}")
            return BrowserState(
                session_id=session_id,
                url="",
                title="",
                viewport={"width": 1280, "height": 720},
                error=str(e),
            )

    async def execute_action(
        self,
        session_id: str,
        action: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute browser action."""
        ctx = await self._ensure_session(session_id)

        # Map frontend action names to backend action names
        # Frontend uses: click (selector), type (selector, text), scroll (direction, amount), get_text (selector), get_attribute (selector, attribute)
        # Backend uses: click (index), input_text (index, text), scroll_down/up (amount), navigate (url), go_back, go_forward, refresh, wait

        # Handle frontend compatibility
        if action == "type":
            action = "input_text"
        elif action == "scroll":
            direction = params.get("direction", "down")
            action = "scroll_down" if direction == "down" else "scroll_up"
        elif action == "get_text":
            # Frontend wants to get text by selector, we'll extract it from the page
            return await self._get_text_by_selector(ctx, params.get("selector", ""))
        elif action == "get_attribute":
            return await self._get_attribute_by_selector(ctx, params.get("selector", ""), params.get("attribute", ""))
        elif action == "click" and "selector" in params and "index" not in params:
            # Frontend uses selector, we need to convert to index
            return await self._click_by_selector(ctx, params.get("selector", ""))

        try:
            if action == "click":
                index = params.get("index")
                if index is not None:
                    # Use get_dom_element_by_index method
                    element = await ctx.browser_session.get_dom_element_by_index(index)
                    if element:
                        download_path = await ctx.browser_session._click_element_node(element)
                        return {"success": True, "message": f"Clicked element {index}", "download_path": download_path}
                    return {"success": False, "error": f"Element {index} not found"}

            elif action == "input_text":
                index = params.get("index")
                text = params.get("text", "")
                if index is not None:
                    element = await ctx.browser_session.get_dom_element_by_index(index)
                    if element:
                        await ctx.browser_session._input_text_element_node(element, text)
                        return {"success": True, "message": f"Input text into element {index}"}
                    return {"success": False, "error": f"Element {index} not found"}

            elif action == "scroll_down":
                amount = params.get("amount", 500)
                page = await ctx.browser_session.get_current_page()
                if page is None:
                    return {"success": False, "error": "No active page in browser session"}
                await page.evaluate(f"() => {{ window.scrollBy(0, {amount}); }}")
                return {"success": True, "message": f"Scrolled down {amount}px"}

            elif action == "scroll_up":
                amount = params.get("amount", 500)
                page = await ctx.browser_session.get_current_page()
                if page is None:
                    return {"success": False, "error": "No active page in browser session"}
                await page.evaluate(f"() => {{ window.scrollBy(0, {-amount}); }}")
                return {"success": True, "message": f"Scrolled up {amount}px"}

            elif action == "scroll_to_text":
                text = params.get("text", "")
                if text:
                    page = await ctx.browser_session.get_current_page()
                    locator = page.get_by_text(text, exact=False)
                    await locator.scroll_into_view_if_needed()
                    return {"success": True, "message": f"Scrolled to text: {text}"}

            elif action == "send_keys":
                keys = params.get("keys", "")
                if keys:
                    page = await ctx.browser_session.get_current_page()
                    await page.keyboard.press(keys)
                    return {"success": True, "message": f"Sent keys: {keys}"}

            elif action == "get_dropdown_options":
                index = params.get("index")
                if index is not None:
                    element = await ctx.browser_session.get_dom_element_by_index(index)
                    if element:
                        page = await ctx.browser_session.get_current_page()
                        options = await page.evaluate(
                            """(xpath) => {
                                const select = document.evaluate(xpath, document, null,
                                    XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                if (!select) return null;
                                return Array.from(select.options).map(opt => ({
                                    text: opt.text, value: opt.value, index: opt.index
                                }));
                            }""",
                            element.xpath,
                        )
                        return {"success": True, "options": options}

            elif action == "select_dropdown_option":
                index = params.get("index")
                text = params.get("text", "")
                if index is not None:
                    element = await ctx.browser_session.get_dom_element_by_index(index)
                    if element:
                        page = await ctx.browser_session.get_current_page()
                        await page.select_option(element.xpath, label=text)
                        return {"success": True, "message": f"Selected '{text}' in dropdown {index}"}

            elif action == "switch_tab":
                tab_id = params.get("tab_id")
                if tab_id is not None:
                    await ctx.browser_session.switch_to_tab(tab_id)
                    return {"success": True, "message": f"Switched to tab {tab_id}"}

            elif action == "open_tab":
                url = params.get("url", "about:blank")
                await ctx.browser_session.create_new_tab(url)
                return {"success": True, "message": f"Opened new tab with {url}"}

            elif action == "close_tab":
                await ctx.browser_session.close_current_tab()
                return {"success": True, "message": "Closed current tab"}

            elif action == "go_back":
                page = await ctx.browser_session.get_current_page()
                if page and hasattr(page, 'go_back'):
                    await page.go_back()
                    return {"success": True, "message": "Navigated back"}
                else:
                    # Fallback: use browser-use navigate_to with back navigation
                    try:
                        await ctx.browser_session.go_back()
                        return {"success": True, "message": "Navigated back"}
                    except AttributeError:
                        return {"success": False, "error": "go_back not supported by browser session"}

            elif action == "refresh":
                await ctx.browser_session.refresh_page()
                return {"success": True, "message": "Refreshed page"}

            elif action == "wait":
                seconds = params.get("seconds", 3)
                await asyncio.sleep(seconds)
                return {"success": True, "message": f"Waited {seconds} seconds"}

            elif action == "navigate":
                url = params.get("url", "")
                if url:
                    await ctx.browser_session.navigate_to(url)
                    return {
                        "success": True,
                        "url": await ctx.browser_session.get_current_page_url(),
                        "title": await ctx.browser_session.get_current_page_title(),
                    }
                return {"success": False, "error": "URL required for navigate action"}

            elif action == "go_forward":
                page = await ctx.browser_session.get_current_page()
                if page and hasattr(page, 'go_forward'):
                    await page.go_forward()
                    return {"success": True, "message": "Navigated forward"}
                else:
                    # Fallback: use browser-use if it has the method
                    try:
                        await ctx.browser_session.go_forward()
                        return {"success": True, "message": "Navigated forward"}
                    except AttributeError:
                        return {"success": False, "error": "go_forward not supported by browser session"}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"Action {action} failed: {e}")
            return {"success": False, "error": str(e)}

    async def _click_by_selector(self, ctx, selector: str) -> Dict[str, Any]:
        """Click element by CSS selector."""
        try:
            page = await ctx.browser_session.get_current_page()
            if page is None:
                return {"success": False, "error": "No active page"}

            element = await page.wait_for_selector(selector, timeout=5000)
            if element:
                await element.click()
                return {"success": True, "message": f"Clicked element with selector: {selector}"}
            return {"success": False, "error": f"Element not found: {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_text_by_selector(self, ctx, selector: str) -> Dict[str, Any]:
        """Get text content by CSS selector."""
        try:
            page = await ctx.browser_session.get_current_page()
            if page is None:
                return {"success": False, "error": "No active page"}

            element = await page.wait_for_selector(selector, timeout=5000)
            if element:
                text = await element.text_content()
                return {"success": True, "text": text or ""}
            return {"success": False, "error": f"Element not found: {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_attribute_by_selector(self, ctx, selector: str, attribute: str) -> Dict[str, Any]:
        """Get attribute value by CSS selector."""
        try:
            page = await ctx.browser_session.get_current_page()
            if page is None:
                return {"success": False, "error": "No active page"}

            element = await page.wait_for_selector(selector, timeout=5000)
            if element:
                value = await element.get_attribute(attribute)
                return {"success": True, "value": value or ""}
            return {"success": False, "error": f"Element not found: {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract_content(
        self,
        session_id: str,
        goal: str,
        selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract content from page using LLM."""
        ctx = await self._ensure_session(session_id)
        try:
            page = await ctx.browser_session.get_current_page()
            import markdownify

            content = markdownify.markdownify(await page.content())
            max_length = self._config.get("max_content_length", 5000)

            if selector:
                # Use selector to extract specific content
                element = await page.query_selector(selector)
                if element:
                    content = markdownify.markdownify(await element.inner_html())

            # Use LLM to extract relevant content
            from app.llm import LLM
            llm = LLM()

            prompt = f"""Extract content from the page based on the goal.
Goal: {goal}

Page content:
{content[:max_length]}

Return JSON with extracted information."""

            messages = [{"role": "system", "content": prompt}]
            extraction_tool = {
                "type": "function",
                "function": {
                    "name": "extract_content",
                    "description": "Extract content based on goal",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "extracted_content": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "metadata": {"type": "object"},
                                },
                                "required": ["text"],
                            }
                        },
                        "required": ["extracted_content"],
                    },
                },
            }

            response = await llm.ask_tool(
                messages,
                tools=[extraction_tool],
                tool_choice="required",
            )

            if response and response.tool_calls:
                import json
                args = json.loads(response.tool_calls[0].function.arguments)
                return {"success": True, "data": args.get("extracted_content", {})}

            return {"success": True, "data": {"text": "No content extracted"}}

        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return {"success": False, "error": str(e)}

    async def take_screenshot(
        self,
        session_id: str,
        full_page: bool = True,
        format: str = "png"
    ) -> str:
        """Take screenshot and return base64."""
        ctx = await self._ensure_session(session_id)
        try:
            # Use browser_session's built-in screenshot with full_page
            screenshot_bytes = await ctx.browser_session.take_screenshot(
                full_page=full_page,
                format="jpeg" if format == "jpg" else format,
                quality=80,
            )
            return base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""

    async def close_session(self, session_id: str) -> bool:
        """Close browser session."""
        async with self._lock:
            if session_id in self._sessions:
                ctx = self._sessions[session_id]
                try:
                    if ctx.browser_session:
                        await ctx.browser_session.stop()
                except Exception as e:
                    logger.warning(f"Error closing session: {e}")
                del self._sessions[session_id]
                return True
            return False

    async def list_sessions(self) -> List[BrowserSession]:
        """List all active sessions."""
        sessions = []
        for session_id, ctx in self._sessions.items():
            try:
                url = await ctx.browser_session.get_current_page_url()
                title = await ctx.browser_session.get_current_page_title()
                sessions.append(BrowserSession(
                    session_id=session_id,
                    url=url,
                    title=title,
                ))
            except Exception:
                sessions.append(BrowserSession(session_id=session_id))
        return sessions