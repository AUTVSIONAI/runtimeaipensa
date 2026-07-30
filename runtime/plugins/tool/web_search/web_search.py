"""
Web Search Plugin for AIPENSA Runtime

Multi-engine web search capabilities for agents.
"""

from typing import Any, Dict, List, Optional
import logging

from runtime.plugins.base import Plugin, PluginMetadata, PluginType
# from runtime.plugins.decorators import tool  # Not yet implemented

logger = logging.getLogger(__name__)


class WebSearchPlugin(Plugin):
    """Plugin de busca web multi-engine."""

    metadata = PluginMetadata(
        name="web_search",
        version="1.2.0",
        description="Busca web via SerpAPI, Bing, Google Custom Search",
        author="aipensa",
        plugin_type=PluginType.TOOL,
        provides=["web_search", "news_search", "academic_search"],
        dependencies=["network:httpx", "runtime:conversation"],
        tags={"search", "web", "serpapi", "bing"},
        entry_point="web_search.py",
        config_schema={
            "type": "object",
            "properties": {
                "default_engine": {
                    "type": "string",
                    "enum": ["serpapi", "bing", "google"],
                    "default": "serpapi"
                },
                "engines": {
                    "type": "object",
                    "properties": {
                        "serpapi": {
                            "type": "object",
                            "properties": {
                                "api_key": {"type": "string", "format": "password"}
                            },
                            "required": ["api_key"]
                        },
                        "bing": {
                            "type": "object",
                            "properties": {
                                "api_key": {"type": "string", "format": "password"},
                                "endpoint": {"type": "string", "format": "uri"}
                            },
                            "required": ["api_key", "endpoint"]
                        },
                        "google": {
                            "type": "object",
                            "properties": {
                                "api_key": {"type": "string", "format": "password"},
                                "cx": {"type": "string"}
                            },
                            "required": ["api_key", "cx"]
                        }
                    },
                    "required": ["default_engine", "engines"]
                },
                "timeout_seconds": {"type": "integer", "minimum": 5, "maximum": 60, "default": 30},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10}
            },
            "required": ["default_engine", "engines"]
        }
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.engines = {}
        self.default_engine = config.get("default_engine", "serpapi") if config else "serpapi"
        self.timeout = config.get("timeout_seconds", 30) if config else 30
        self.max_results = config.get("max_results", 10) if config else 10

    async def initialize(self, runtime: Any) -> None:
        """Initialize the plugin with runtime reference."""
        self.runtime = runtime
        await self._initialize_engines()
        logger.info("WebSearchPlugin initialized")

    async def _initialize_engines(self) -> None:
        """Initialize configured search engines."""
        engines_config = self.config.get("engines", {}) if self.config else {}

        for name, cfg in engines_config.items():
            if name == "serpapi" and "api_key" in cfg:
                self.engines[name] = SerpAPIEngine(cfg["api_key"])
            elif name == "bing" and "api_key" in cfg and "endpoint" in cfg:
                self.engines[name] = BingEngine(cfg["api_key"], cfg["endpoint"])
            elif name == "google" and "api_key" in cfg and "cx" in cfg:
                self.engines[name] = GoogleCustomSearchEngine(cfg["api_key"], cfg["cx"])

        if not self.engines:
            logger.warning("No search engines configured")

    async def start(self) -> None:
        """Start the plugin."""
        logger.info("WebSearchPlugin started")

    async def stop(self) -> None:
        """Stop the plugin."""
        logger.info("WebSearchPlugin stopped")

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.engines.clear()
        logger.info("WebSearchPlugin cleaned up")

    async def web_search(
        self,
        query: str,
        engine: Optional[str] = None,
        max_results: Optional[int] = None,
        recency_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executa busca web.

        Args:
            query: Query de busca
            engine: Engine específico (opcional, usa default_engine)
            max_results: Máximo de resultados
            recency_days: Filtrar por dias recentes

        Returns:
            Dict com resultados da busca
        """
        engine_name = engine or self.default_engine
        search_engine = self.engines.get(engine_name)

        if not search_engine:
            return {
                "success": False,
                "error": f"Engine '{engine_name}' não configurado",
                "query": query
            }

        try:
            results = await search_engine.search(
                query=query,
                max_results=max_results or self.max_results,
                recency_days=recency_days
            )

            return {
                "success": True,
                "data": {
                    "results": results,
                    "engine": engine_name,
                    "query": query
                }
            }
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

    async def news_search(self, query: str, days_back: int = 7) -> Dict[str, Any]:
        """Busca notícias recentes."""
        return await self.web_search(query, recency_days=days_back)


class SearchEngine:
    """Base class for search engines."""

    async def search(self, query: str, max_results: int = 10, recency_days: Optional[int] = None) -> List[Dict]:
        raise NotImplementedError


class SerpAPIEngine(SearchEngine):
    """SerpAPI search engine."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"

    async def search(self, query: str, max_results: int = 10, recency_days: Optional[int] = None) -> List[Dict]:
        import httpx

        params = {
            "q": query,
            "api_key": self.api_key,
            "num": max_results,
        }

        if recency_days:
            params["tbs"] = f"qdr:d{recency_days}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", 0)
            })

        return results


class BingEngine(SearchEngine):
    """Bing Search API engine."""

    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")

    async def search(self, query: str, max_results: int = 10, recency_days: Optional[int] = None) -> List[Dict]:
        import httpx

        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {
            "q": query,
            "count": max_results,
            "responseFilter": "Webpages"
        }

        if recency_days:
            params["freshness"] = f"Day-{recency_days}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.endpoint}/v7.0/search", headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("webPages", {}).get("value", [])[:max_results]:
            results.append({
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", 0)
            })

        return results


class GoogleCustomSearchEngine(SearchEngine):
    """Google Custom Search API engine."""

    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def search(self, query: str, max_results: int = 10, recency_days: Optional[int] = None) -> List[Dict]:
        import httpx

        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(max_results, 10),  # Google max is 10
        }

        if recency_days:
            params["dateRestrict"] = f"d{recency_days}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for i, item in enumerate(data.get("items", [])[:max_results]):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": i + 1
            })

        return results


# Export plugin class for discovery
__all__ = ["WebSearchPlugin", "SerpAPIEngine", "BingEngine", "GoogleCustomSearchEngine"]