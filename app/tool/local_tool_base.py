"""Local Tools Base

This module provides a base class for tools that run locally using Playwright,
equivalent to SandboxToolsBase but without Daytona dependency.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

from pydantic import Field

from app.tool.base import BaseTool
from app.utils.files_utils import clean_path
from app.utils.logger import logger


@dataclass
class ThreadMessage:
    """
    Represents a message to be added to a thread.
    """

    type: str
    content: Dict[str, Any]
    is_llm_message: bool = False
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = field(
        default_factory=lambda: datetime.now().timestamp()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary for API calls"""
        return {
            "type": self.type,
            "content": self.content,
            "is_llm_message": self.is_llm_message,
            "metadata": self.metadata or {},
            "timestamp": self.timestamp,
        }


class LocalToolsBase(BaseTool):
    """Base class for all local tools that provides project-based access.

    This is the local equivalent of SandboxToolsBase, using Playwright directly
    instead of requiring a Daytona sandbox.
    """

    # Class variable to track if URLs have been printed
    _urls_printed: ClassVar[bool] = False

    # Required fields
    project_id: Optional[str] = None

    # Private fields (not part of the model schema)
    workspace_path: str = Field(default="/workspace", exclude=True)
    _browser = None
    _context = None
    _sessions: dict[str, str] = {}

    class Config:
        arbitrary_types_allowed = True  # Allow non-pydantic types like ThreadManager

    def clean_path(self, path: str) -> str:
        """Clean and normalize a path to be relative to /workspace."""
        cleaned_path = clean_path(path, self.workspace_path)
        logger.debug(f"Cleaned path: {path} -> {cleaned_path}")
        return cleaned_path

    async def _ensure_browser(self) -> None:
        """Ensure browser and context are initialized lazily."""
        if self._browser is not None and self._context is not None:
            return

        # Lazy imports - only import when actually needed
        from browser_use import Browser as BrowserUseBrowser
        from browser_use import BrowserConfig
        from browser_use.browser.context import BrowserContext, BrowserContextConfig
        from app.config import config

        browser_config_kwargs = {"headless": False, "disable_security": True}

        if config.browser_config:
            from browser_use.browser.browser import ProxySettings

            # Handle proxy settings
            if config.browser_config.proxy and config.browser_config.proxy.server:
                browser_config_kwargs["proxy"] = ProxySettings(
                    server=config.browser_config.proxy.server,
                    username=config.browser_config.proxy.username,
                    password=config.browser_config.proxy.password,
                )

            browser_attrs = [
                "headless",
                "disable_security",
                "extra_chromium_args",
                "chrome_instance_path",
                "wss_url",
                "cdp_url",
            ]

            for attr in browser_attrs:
                value = getattr(config.browser_config, attr, None)
                if value is not None:
                    if not isinstance(value, list) or value:
                        browser_config_kwargs[attr] = value

        self._browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))

        context_config = BrowserContextConfig()

        # If there is context config in the config, use it
        if (
            config.browser_config
            and hasattr(config.browser_config, "new_context_config")
            and config.browser_config.new_context_config
        ):
            context_config = config.browser_config.new_context_config

        self._context = await self._browser.new_context(context_config)
        logger.info("Local browser initialized successfully")

    @property
    def browser(self):
        """Get the browser instance, ensuring it exists."""
        if self._browser is None:
            raise RuntimeError("Browser not initialized. Call _ensure_browser() first.")
        return self._browser

    @property
    def context(self):
        """Get the browser context instance, ensuring it exists."""
        if self._context is None:
            raise RuntimeError("Browser context not initialized. Call _ensure_browser() first.")
        return self._context

    async def cleanup(self):
        """Clean up browser resources."""
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._browser is not None:
            await self._browser.close()
            self._browser = None