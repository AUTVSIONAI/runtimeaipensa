import asyncio
import json
from typing import Generic, Optional, TypeVar

from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from app.config import config
from app.llm import LLM
from app.tool.base import BaseTool, ToolResult
from app.tool.web_search import WebSearch
from app.browser.runtime import BrowserRuntime, create_browser_runtime, BrowserActionResult


_BROWSER_DESCRIPTION = """\
A powerful browser automation tool that allows interaction with web pages through various actions.
* This tool provides commands for controlling a browser session, navigating web pages, and extracting information
* It maintains state across calls, keeping the browser session alive until explicitly closed
* Use this when you need to browse websites, fill forms, click buttons, extract content, or perform web searches
* Each action requires specific parameters as defined in the tool's dependencies

Key capabilities include:
* Navigation: Go to specific URLs, go back, search the web, or refresh pages
* Interaction: Click elements, input text, select from dropdowns, send keyboard commands
* Scrolling: Scroll up/down by pixel amount or scroll to specific text
* Content extraction: Extract and analyze content from web pages based on specific goals
* Tab management: Switch between tabs, open new tabs, or close tabs

Note: When using element indices, refer to the numbered elements shown in the current browser state.
"""

Context = TypeVar("Context")


class BrowserUseTool(BaseTool, Generic[Context]):
    name: str = "browser_use"
    description: str = _BROWSER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "go_to_url",
                    "click_element",
                    "input_text",
                    "scroll_down",
                    "scroll_up",
                    "scroll_to_text",
                    "send_keys",
                    "get_dropdown_options",
                    "select_dropdown_option",
                    "go_back",
                    "web_search",
                    "wait",
                    "extract_content",
                    "switch_tab",
                    "open_tab",
                    "close_tab",
                    "refresh",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'go_to_url' or 'open_tab' actions",
            },
            "index": {
                "type": "integer",
                "description": "Element index for 'click_element', 'input_text', 'get_dropdown_options', or 'select_dropdown_option' actions",
            },
            "text": {
                "type": "string",
                "description": "Text for 'input_text', 'scroll_to_text', or 'select_dropdown_option' actions",
            },
            "scroll_amount": {
                "type": "integer",
                "description": "Pixels to scroll (positive for down, negative for up) for 'scroll_down' or 'scroll_up' actions",
            },
            "tab_id": {
                "type": "integer",
                "description": "Tab ID for 'switch_tab' action",
            },
            "query": {
                "type": "string",
                "description": "Search query for 'web_search' action",
            },
            "goal": {
                "type": "string",
                "description": "Extraction goal for 'extract_content' action",
            },
            "keys": {
                "type": "string",
                "description": "Keys to send for 'send_keys' action",
            },
            "seconds": {
                "type": "integer",
                "description": "Seconds to wait for 'wait' action",
            },
        },
        "required": ["action"],
        "dependencies": {
            "go_to_url": ["url"],
            "click_element": ["index"],
            "input_text": ["index", "text"],
            "switch_tab": ["tab_id"],
            "open_tab": ["url"],
            "scroll_down": ["scroll_amount"],
            "scroll_up": ["scroll_amount"],
            "scroll_to_text": ["text"],
            "send_keys": ["keys"],
            "get_dropdown_options": ["index"],
            "select_dropdown_option": ["index", "text"],
            "go_back": [],
            "web_search": ["query"],
            "wait": ["seconds"],
            "extract_content": ["goal"],
        },
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
    browser_runtime: Optional[BrowserRuntime] = Field(default=None, exclude=True)

    # Context for generic functionality
    tool_context: Optional[Context] = Field(default=None, exclude=True)

    llm: Optional[LLM] = Field(default_factory=LLM)

    @field_validator("parameters", mode="before")
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        if not v:
            raise ValueError("Parameters cannot be empty")
        return v

    def __init__(self, browser_runtime: Optional[BrowserRuntime] = None, **data):
        """Initialize BrowserUseTool with optional browser runtime."""
        super().__init__(**data)
        self.browser_runtime = browser_runtime

    async def _ensure_runtime_initialized(self) -> BrowserRuntime:
        """Ensure browser runtime is initialized."""
        if self.browser_runtime is None:
            self.browser_runtime = create_browser_runtime()

        if not self.browser_runtime.is_initialized:
            await self.browser_runtime.initialize()

        return self.browser_runtime

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        index: Optional[int] = None,
        text: Optional[str] = None,
        scroll_amount: Optional[int] = None,
        tab_id: Optional[int] = None,
        query: Optional[str] = None,
        goal: Optional[str] = None,
        keys: Optional[str] = None,
        seconds: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a specified browser action.

        Args:
            action: The browser action to perform
            url: URL for navigation or new tab
            index: Element index for click or input actions
            text: Text for input action or search query
            scroll_amount: Pixels to scroll for scroll action
            tab_id: Tab ID for switch_tab action
            query: Search query for Google search
            goal: Extraction goal for content extraction
            keys: Keys to send for keyboard actions
            seconds: Seconds to wait
            **kwargs: Additional arguments

        Returns:
            ToolResult with the action's output or error
        """
        async with self.lock:
            try:
                runtime = await self._ensure_runtime_initialized()

                max_content_length = getattr(
                    config.browser_config, "max_content_length", 2000
                )

                # Navigation actions
                if action == "go_to_url":
                    if not url:
                        return ToolResult(error="URL is required for 'go_to_url' action")
                    result = await runtime.navigate(url)
                    return ToolResult(output=result.message, error=result.error)

                elif action == "go_back":
                    result = await runtime.go_back()
                    return ToolResult(output=result.message, error=result.error)

                elif action == "refresh":
                    result = await runtime.refresh()
                    return ToolResult(output=result.message, error=result.error)

                elif action == "web_search":
                    if not query:
                        return ToolResult(
                            error="Query is required for 'web_search' action"
                        )
                    result = await runtime.web_search(query)
                    return ToolResult(
                        output=result.message,
                        error=result.error,
                        data=result.data
                    )

                # Element interaction actions
                elif action == "click_element":
                    if index is None:
                        return ToolResult(
                            error="Index is required for 'click_element' action"
                        )
                    result = await runtime.click_element(index)
                    return ToolResult(output=result.message, error=result.error)

                elif action == "input_text":
                    if index is None or not text:
                        return ToolResult(
                            error="Index and text are required for 'input_text' action"
                        )
                    result = await runtime.input_text(index, text)
                    return ToolResult(output=result.message, error=result.error)

                elif action == "scroll_down" or action == "scroll_up":
                    direction = 1 if action == "scroll_down" else -1
                    amount = (
                        scroll_amount
                        if scroll_amount is not None
                        else direction * abs(scroll_amount or 0)
                    )
                    # Use the runtime's scroll methods
                    if action == "scroll_down":
                        result = await runtime.scroll_down(scroll_amount)
                    else:
                        result = await runtime.scroll_up(abs(scroll_amount or 0))
                    return ToolResult(output=result.message, error=result.error)

                elif action == "scroll_to_text":
                    if not text:
                        return ToolResult(
                            error="Text is required for 'scroll_to_text' action"
                        )
                    result = await runtime.scroll_to_text(text)
                    return ToolResult(output=result.message, error=result.error)

                elif action == "send_keys":
                    if not keys:
                        return ToolResult(
                            error="Keys are required for 'send_keys' action"
                        )
                    result = await runtime.send_keys(keys)
                    return ToolResult(output=result.message, error=result.error)

                elif action == "get_dropdown_options":
                    if index is None:
                        return ToolResult(
                            error="Index is required for 'get_dropdown_options' action"
                        )
                    result = await runtime.get_dropdown_options(index)
                    output = f"Dropdown options: {result.data.get('options', [])}" if result.data else result.message
                    return ToolResult(output=output, error=result.error)

                elif action == "select_dropdown_option":
                    if index is None or not text:
                        return ToolResult(
                            error="Index and text are required for 'select_dropdown_option' action"
                        )
                    result = await runtime.select_dropdown_option(index, text)
                    return ToolResult(output=result.message, error=result.error)

                # Content extraction actions
                elif action == "extract_content":
                    if not goal:
                        return ToolResult(
                            error="Goal is required for 'extract_content' action"
                        )

                    result = await runtime.extract_content(goal)
                    if result.success and result.data:
                        extracted = result.data.get("extracted_content", {})
                        return ToolResult(
                            output=f"Extracted from page:\n{extracted_content}\n"
                        )
                    return ToolResult(output="No content was extracted from the page.", error=result.error)

                # Tab management actions
                elif action == "switch_tab":
                    if tab_id is None:
                        return ToolResult(
                            error="Tab ID is required for 'switch_tab' action"
                        )
                    result = await runtime.switch_tab(tab_id)
                    return ToolResult(output=result.message, error=result.error)

                elif action == "open_tab":
                    if not url:
                        return ToolResult(error="URL is required for 'open_tab' action")
                    result = await runtime.open_tab(url)
                    return ToolResult(output=result.message, error=result.error)

                elif action == "close_tab":
                    result = await runtime.close_tab()
                    return ToolResult(output=result.message, error=result.error)

                # Utility actions
                elif action == "wait":
                    seconds_to_wait = seconds if seconds is not None else 3
                    result = await runtime.wait(seconds_to_wait)
                    return ToolResult(output=result.message, error=result.error)

                else:
                    return ToolResult(error=f"Unknown action: {action}")

            except Exception as e:
                return ToolResult(error=f"Browser action '{action}' failed: {str(e)}")

    async def get_current_state(self) -> ToolResult:
        """
        Get the current browser state as a ToolResult.
        """
        try:
            runtime = await self._ensure_runtime_initialized()
            state = await runtime.get_state()

            if state.error:
                return ToolResult(error=state.error)

            import base64

            return ToolResult(
                output=json.dumps({
                    "url": state.url,
                    "title": state.title,
                    "tabs": state.tabs,
                    "pixels_above": state.pixels_above,
                    "pixels_below": state.pixels_below,
                    "viewport_height": state.viewport_height,
                    "interactive_elements": state.interactive_elements,
                }, indent=4, ensure_ascii=False),
                base64_image=state.screenshot_base64,
            )
        except Exception as e:
            return ToolResult(error=f"Failed to get browser state: {str(e)}")

    async def cleanup(self):
        """Clean up browser resources."""
        async with self.lock:
            if self.browser_runtime is not None:
                await self.browser_runtime.cleanup()
                self.browser_runtime = None

    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        if self.browser_runtime is not None:
            try:
                asyncio.run(self.cleanup())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.cleanup())
                loop.close()

    @classmethod
    def create_with_context(cls, context: Context) -> "BrowserUseTool[Context]":
        """Factory method to create a BrowserUseTool with a specific context."""
        tool = cls()
        tool.tool_context = context
        return tool

    @classmethod
    def create_with_runtime(cls, browser_runtime: BrowserRuntime) -> "BrowserUseTool":
        """Factory method to create a BrowserUseTool with a specific browser runtime."""
        tool = cls(browser_runtime=browser_runtime)
        return tool