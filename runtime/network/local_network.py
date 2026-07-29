"""
Local Network Module Implementation

Provides HTTP/HTTPS request capabilities using aiohttp.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional
import asyncio
import logging
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientResponse

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    NetworkModule,
    NetworkRequest,
    NetworkResponse,
)

logger = logging.getLogger(__name__)


class LocalNetworkModule(NetworkModule):
    """
    Local network implementation using aiohttp.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="network",
            version="1.0.0",
            description="HTTP/HTTPS network operations",
            author="AIPENSA",
            dependencies=[],
            provides=["http_request", "http_get", "http_post", "file_download"],
            tags={"local", "network", "http", "aiohttp"},
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._config = config or {}
        self._session: Optional[ClientSession] = None
        self._default_timeout = self._config.get("timeout_seconds", 30)
        self._max_connections = self._config.get("max_connections", 100)
        self._proxy = self._config.get("proxy")
        self._verify_ssl = self._config.get("verify_ssl", True)

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._default_timeout = self._config.get("timeout_seconds", self._default_timeout)
        self._max_connections = self._config.get("max_connections", self._max_connections)
        self._proxy = self._config.get("proxy", self._proxy)
        self._verify_ssl = self._config.get("verify_ssl", self._verify_ssl)

        # Create session
        connector = aiohttp.TCPConnector(
            limit=self._max_connections,
            verify_ssl=self._verify_ssl,
        )
        timeout = ClientTimeout(total=self._default_timeout)
        self._session = ClientSession(connector=connector, timeout=timeout)

        self.state = ModuleState.INITIALIZED
        logger.info("LocalNetworkModule initialized")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("LocalNetworkModule started")

    async def stop(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self.state = ModuleState.STOPPED
        logger.info("LocalNetworkModule stopped")

    async def cleanup(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self.state = ModuleState.UNINITIALIZED
        logger.info("LocalNetworkModule cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "network",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "session_open": self._session is not None and not self._session.closed,
        }

    def _get_session(self) -> ClientSession:
        """Get or create session."""
        if not self._session or self._session.closed:
            raise RuntimeError("Network module not initialized")
        return self._session

    async def request(self, request: NetworkRequest) -> NetworkResponse:
        """Make HTTP request."""
        session = self._get_session()

        # Prepare request
        kwargs = {
            "method": request.method,
            "url": request.url,
            "headers": request.headers,
        }

        if request.body is not None:
            if isinstance(request.body, dict):
                kwargs["json"] = request.body
            else:
                kwargs["data"] = request.body

        if request.timeout_seconds:
            kwargs["timeout"] = ClientTimeout(total=request.timeout_seconds)

        if self._proxy:
            kwargs["proxy"] = self._proxy

        try:
            start_time = datetime.utcnow()
            async with session.request(**kwargs) as response:
                body = await response.read()
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000

                return NetworkResponse(
                    status_code=response.status,
                    body=body,
                    headers=dict(response.headers),
                    duration_ms=duration,
                )
        except asyncio.TimeoutError:
            return NetworkResponse(
                status_code=0,
                body=b"",
                headers={},
                duration_ms=request.timeout_seconds * 1000 if request.timeout_seconds else 0,
                error="Request timeout",
            )
        except Exception as e:
            return NetworkResponse(
                status_code=0,
                body=b"",
                headers={},
                duration_ms=0,
                error=str(e),
            )

    async def get(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP GET request."""
        request = NetworkRequest(url=url, method="GET", **kwargs)
        return await self.request(request)

    async def post(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP POST request."""
        request = NetworkRequest(url=url, method="POST", **kwargs)
        return await self.request(request)

    async def put(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP PUT request."""
        request = NetworkRequest(url=url, method="PUT", **kwargs)
        return await self.request(request)

    async def delete(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP DELETE request."""
        request = NetworkRequest(url=url, method="DELETE", **kwargs)
        return await self.request(request)

    async def patch(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP PATCH request."""
        request = NetworkRequest(url=url, method="PATCH", **kwargs)
        return await self.request(request)

    async def head(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP HEAD request."""
        request = NetworkRequest(url=url, method="HEAD", **kwargs)
        return await self.request(request)

    async def download_file(
        self,
        url: str,
        destination: str,
        progress_callback: Optional[callable] = None,
        chunk_size: int = 8192,
        **kwargs
    ) -> NetworkResponse:
        """Download a file with progress tracking."""
        session = self._get_session()

        kwargs.setdefault("method", "GET")
        kwargs["url"] = url

        if self._proxy:
            kwargs["proxy"] = self._proxy

        try:
            async with session.request(**kwargs) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0

                import aiofiles
                os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)

                async with aiofiles.open(destination, "wb") as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

                return NetworkResponse(
                    status_code=response.status,
                    body=b"",
                    headers=dict(response.headers),
                    duration_ms=0,
                )
        except Exception as e:
            return NetworkResponse(
                status_code=0,
                body=b"",
                headers={},
                duration_ms=0,
                error=str(e),
            )

    async def upload_file(
        self,
        url: str,
        file_path: str,
        field_name: str = "file",
        additional_data: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> NetworkResponse:
        """Upload a file using multipart/form-data."""
        session = self._get_session()

        import aiofiles
        file_size = os.path.getsize(file_path)

        form = aiohttp.FormData()
        form.add_field(field_name, open(file_path, "rb"), filename=os.path.basename(file_path))

        if additional_data:
            for key, value in additional_data.items():
                form.add_field(key, value)

        try:
            async with session.post(url, data=form, proxy=self._proxy, **kwargs) as response:
                body = await response.read()
                return NetworkResponse(
                    status_code=response.status,
                    body=body,
                    headers=dict(response.headers),
                    duration_ms=0,
                )
        except Exception as e:
            return NetworkResponse(
                status_code=0,
                body=b"",
                headers={},
                duration_ms=0,
                error=str(e),
            )


# Need to import os for download_file
import os