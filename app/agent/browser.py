import json
from typing import TYPE_CHECKING, Optional, Any, Dict, List

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.logger import logger
from app.prompt.browser import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import Message, ToolChoice
from app.tool import Terminate, ToolCollection
from app.browser.runtime import BrowserRuntime, create_browser_runtime, BrowserState


# Avoid circular import if BrowserAgent needs BrowserContextHelper
if TYPE_CHECKING:
    from app.agent.base import BaseAgent  # Or wherever memory is defined


class BrowserContextHelper:
    def __init__(self, agent: "BaseAgent"):
        self.agent = agent
        self._current_base64_image: Optional[str] = None
        self._browser_runtime: Optional[BrowserRuntime] = None

    @property
    def browser_runtime(self) -> Optional[BrowserRuntime]:
        """Get the browser runtime from the agent's available tools."""
        if self._browser_runtime is None:
            # Try to get from the agent's available tools
            for tool in self.agent.available_tools.tools:
                if hasattr(tool, 'browser_runtime'):
                    self._browser_runtime = tool.browser_runtime
                    break
                # Also check if tool is a BrowserRuntime directly
                if isinstance(tool, BrowserRuntime):
                    self._browser_runtime = tool
                    break
        return self._browser_runtime

    async def get_browser_state(self) -> Optional[BrowserState]:
        runtime = self.browser_runtime
        if not runtime:
            logger.warning("BrowserRuntime not found in available tools")
            return None
        try:
            return await runtime.get_state()
        except Exception as e:
            logger.debug(f"Failed to get browser state: {str(e)}")
            return None

    async def format_next_step_prompt(self) -> str:
        """Gets browser state and formats the browser prompt."""
        browser_state = await self.get_browser_state()
        url_info, tabs_info, content_above_info, content_below_info = "", "", "", ""
        results_info = ""  # Or get from agent if needed elsewhere

        if browser_state and not browser_state.error:
            url_info = f"\n   URL: {browser_state.url}\n   Title: {browser_state.title}"
            tabs = browser_state.tabs
            if tabs:
                tabs_info = f"\n   {len(tabs)} tab(s) available"
            pixels_above = browser_state.pixels_above
            pixels_below = browser_state.pixels_below
            if pixels_above > 0:
                content_above_info = f" ({pixels_above} pixels)"
            if pixels_below > 0:
                content_below_info = f" ({pixels_below} pixels)"

            if browser_state.screenshot_base64:
                image_message = Message.user_message(
                    content="Current browser screenshot:",
                    base64_image=browser_state.screenshot_base64,
                )
                self.agent.memory.add_message(image_message)
                # Don't set _current_base64_image to None here - let cleanup handle it

        return NEXT_STEP_PROMPT.format(
            url_placeholder=url_info,
            tabs_placeholder=tabs_info,
            content_above_placeholder=content_above_info,
            content_below_placeholder=content_below_info,
            results_placeholder=results_info,
        )

    async def cleanup_browser(self):
        runtime = self.browser_runtime
        if runtime and hasattr(runtime, "cleanup"):
            await runtime.cleanup()


class BrowserAgent(ToolCallAgent):
    """
    A browser agent that uses the BrowserRuntime abstraction to control a browser.

    This agent can navigate web pages, interact with elements, fill forms,
    extract content, and perform other browser-based actions to accomplish tasks.
    The browser runtime (local Playwright, Daytona, etc.) is determined by configuration.
    """

    name: str = "browser"
    description: str = "A browser agent that can control a browser to accomplish tasks"

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # The browser runtime will be injected via the tool
    browser_runtime: Optional[BrowserRuntime] = Field(default=None, exclude=True)

    # Node: we don't add tools directly here - the tool collection will include the BrowserUseTool
    # which wraps the BrowserRuntime. The actual browser automation is done through that tool.
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            # BrowserUseTool is added dynamically based on runtime configuration
            Terminate()
        )
    )

    # Use Auto for tool choice to allow both tool usage and free-form responses
    tool_choices: ToolChoice = ToolChoice.AUTO
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    browser_context_helper: Optional[BrowserContextHelper] = None

    @model_validator(mode="after")
    def initialize_helper(self) -> "BrowserAgent":
        self.browser_context_helper = BrowserContextHelper(self)
        return self

    async def _initialize_browser_tool(self):
        """Initialize the browser tool based on configuration."""
        from app.config import config as app_config
        from app.tool.browser_use_tool import BrowserUseTool

        # Create browser runtime based on config
        if self.browser_runtime is None:
            self.browser_runtime = create_browser_runtime()

        # Initialize the runtime
        await self.browser_runtime.initialize()

        # Create BrowserUseTool wrapping the runtime
        browser_tool = BrowserUseTool(browser_runtime=self.browser_runtime)

        # Add to available tools
        self.available_tools.add_tools(browser_tool)

    async def think(self) -> bool:
        """Process current state and decide next actions using tools, with browser state info added"""
        # Ensure browser tool is initialized
        if not any(isinstance(t, type) for t in self.available_tools.tools if hasattr(t, 'name') and t.name == 'browser_use'):
            from app.tool.browser_use_tool import BrowserUseTool
            has_browser_tool = any(t.name == 'browser_use' for t in self.available_tools.tools if hasattr(t, 'name'))
            if not has_browser_tool:
                await self._initialize_browser_tool()

        self.next_step_prompt = (
            await self.browser_context_helper.format_next_step_prompt()
        )
        return await super().think()

    async def cleanup(self):
        """Clean up browser agent resources."""
        await self.browser_context_helper.cleanup_browser()