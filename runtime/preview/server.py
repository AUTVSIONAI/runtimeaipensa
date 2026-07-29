#!/usr/bin/env python
"""
AIPENSA Runtime Preview Server

Standalone FastAPI server for previewing generated websites with hot reload.
Run with: python -m runtime.preview.server
"""

import argparse
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Request

from runtime.config import RuntimeConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("preview")


# Global server reference for signal handling
_preview_server: "PreviewServer" = None


def load_preview_config(config: RuntimeConfig) -> dict:
    """Extract preview configuration from runtime config."""
    # Try to get from preview section if it exists
    preview_config = getattr(config, 'preview', {})
    if isinstance(preview_config, dict):
        return {
            "host": preview_config.get("host", "0.0.0.0"),
            "port": preview_config.get("port", 8080),
            "workspace": preview_config.get("workspace", "workspace"),
            "cors_origins": preview_config.get("cors_origins", ["*"]),
            "hot_reload": preview_config.get("hot_reload", True),
        }
    return {
        "host": getattr(config, "host", "0.0.0.0"),
        "port": getattr(config, "port", 8080),
        "workspace": getattr(config, "workspace", "workspace"),
        "cors_origins": getattr(config, "cors_origins", ["*"]),
        "hot_reload": getattr(config, "hot_reload", True),
    }


class PreviewServer:
    """
    Standalone FastAPI server for previewing generated websites.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        workspace: str = "workspace",
        cors_origins: list = None,
        hot_reload: bool = True,
    ):
        self.host = host
        self.port = port
        self.workspace_root = Path(workspace).resolve()
        self.cors_origins = cors_origins or ["*"]
        self.hot_reload = hot_reload

        self._websockets: set = set()
        self._observer: Observer = None

        # Create FastAPI app
        self.app = self._create_app()

    def _create_app(self):
        """Create and configure the FastAPI application."""
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
        from fastapi.middleware.cors import CORSMiddleware

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self.start()
            yield
            # Shutdown
            await self.stop()

        app = FastAPI(
            title="AIPENSA Preview Server",
            description="Live preview for generated websites",
            version="1.0.0",
            lifespan=lifespan,
        )

        # CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins if self.cors_origins != ["*"] else ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # WebSocket endpoint for hot reload
        @app.websocket("/ws/reload")
        async def websocket_reload(websocket: WebSocket):
            await websocket.accept()
            self._websockets.add(websocket)
            logger.info(f"WebSocket connected. Total: {len(self._websockets)}")
            try:
                while True:
                    await websocket.receive_text()  # Keep alive
            except WebSocketDisconnect:
                pass
            finally:
                self._websockets.discard(websocket)
                logger.info(f"WebSocket disconnected. Total: {len(self._websockets)}")

        # Health check
        @app.get("/health")
        async def health():
            return {"status": "healthy", "workspace": str(self.workspace_root)}

        # Directory listing / file serving
        @app.get("/{path:path}")
        async def serve_file(request: Request, path: str = ""):
            return await self._serve_path(path)

        return app

    async def _serve_path(self, path: str):
        """Serve a file or directory listing."""
        from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

        # Normalize path
        if not path or path == "/":
            path = "index.html"

        # Handle /sites/{site_id}/{path} routes for subdomain-style previews
        if path.startswith("sites/"):
            parts = path.split("/", 2)
            if len(parts) >= 2:
                site_id = parts[1]
                site_path = parts[2] if len(parts) > 2 else "index.html"
                return await self._serve_site(site_id, site_path)

        # Security: prevent directory traversal
        try:
            file_path = (self.workspace_root / path).resolve()
            # Ensure the path is within workspace
            file_path.relative_to(self.workspace_root)
        except ValueError:
            return PlainTextResponse("Forbidden", status_code=403)

        # Check if file exists
        if file_path.is_file():
            # Serve file with proper MIME type
            return FileResponse(file_path)

        # If directory, check for index.html
        if file_path.is_dir():
            index_path = file_path / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)
            # Generate directory listing
            return await self._generate_directory_listing(file_path, path)

        # Check if it's a path without extension - try adding .html
        if "." not in Path(path).name:
            html_path = self.workspace_root / f"{path}.html"
            if html_path.is_file():
                return FileResponse(html_path)

            # Try index.html in that directory
            index_path = self.workspace_root / path / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)

        return PlainTextResponse("Not Found", status_code=404)

    async def _serve_site(self, site_id: str, site_path: str):
        """Serve a specific site from sites/{site_id}/ directory."""
        from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

        site_dir = self.workspace_root / "sites" / site_id

        # Security check
        try:
            site_dir.resolve().relative_to(self.workspace_root.resolve())
        except ValueError:
            return PlainTextResponse("Forbidden", status_code=403)

        if not site_dir.exists() or not site_dir.is_dir():
            return PlainTextResponse(f"Site '{site_id}' not found", status_code=404)

        if not site_path or site_path == "/":
            site_path = "index.html"

        file_path = (site_dir / site_path).resolve()

        try:
            file_path.relative_to(site_dir.resolve())
        except ValueError:
            return PlainTextResponse("Forbidden", status_code=403)

        if file_path.is_file():
            return FileResponse(file_path)

        if file_path.is_dir():
            index_path = file_path / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)
            return await self._generate_directory_listing(file_path, f"sites/{site_id}/{site_path}")

        # Try .html extension
        if "." not in Path(site_path).name:
            html_path = site_dir / f"{site_path}.html"
            if html_path.is_file():
                return FileResponse(html_path)

            index_path = site_dir / site_path / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)

        return PlainTextResponse("Not Found", status_code=404)

    async def _generate_directory_listing(self, dir_path: Path, relative_path: str):
        """Generate HTML directory listing."""
        items = []
        for item in sorted(dir_path.iterdir()):
            rel_item = item.relative_to(self.workspace_root)
            if item.is_dir():
                items.append(
                    f'<li><a href="/{rel_item}/">📁 {item.name}/</a></li>'
                )
            else:
                items.append(
                    f'<li><a href="/{rel_item}">📄 {item.name}</a> '
                    f'({item.stat().st_size} bytes)</li>'
                )

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Directory: /{relative_path}</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                       max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
                h1 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 0.5rem; }}
                ul {{ list-style: none; padding: 0; }}
                li {{ padding: 0.5rem; border-bottom: 1px solid #f0f0f0; }}
                a {{ color: #0066cc; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>📁 Directory: /{relative_path}</h1>
            <ul>
                {''.join(items)}
            </ul>
            <script>
                // Hot reload client
                const ws = new WebSocket(`ws://${{location.host}}/ws/reload`);
                ws.onmessage = () => {{ location.reload(); }};
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)

    async def start(self):
        """Start the preview server."""
        # Ensure workspace exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # Setup file watcher for hot reload
        if self.hot_reload:
            self._setup_file_watcher()

        logger.info(f"Preview server starting on http://{self.host}:{self.port}")
        logger.info(f"Serving workspace: {self.workspace_root}")

    async def stop(self):
        """Stop the preview server."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
        logger.info("Preview server stopped")

    def _setup_file_watcher(self):
        """Setup watchdog observer for file changes."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class WorkspaceEventHandler(FileSystemEventHandler):
            def __init__(self, server):
                self.server = server
                self._last_modified = {}

            def on_modified(self, event):
                if event.is_directory:
                    return
                self._handle_event(event.src_path)

            def on_created(self, event):
                if not event.is_directory:
                    self._handle_event(event.src_path)

            def on_deleted(self, event):
                if not event.is_directory:
                    self._handle_event(event.src_path)

            def _handle_event(self, filepath):
                import datetime
                curr_time = datetime.datetime.now().timestamp()
                if filepath in self._last_modified:
                    if curr_time - self._last_modified[filepath] < 0.5:
                        return
                self._last_modified[filepath] = curr_time

                try:
                    rel_path = os.path.relpath(filepath, self.server.workspace_root)
                    # Broadcast to all WebSocket clients
                    import asyncio
                    asyncio.create_task(self.server.broadcast_reload(rel_path))
                except ValueError:
                    pass

        handler = WorkspaceEventHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.workspace_root), recursive=True)
        self._observer.start()

    async def broadcast_reload(self, path: str):
        """Broadcast reload signal to all connected WebSocket clients."""
        if not self._websockets:
            return

        message = {"type": "reload", "path": path}
        import json
        msg_json = json.dumps(message)

        disconnected = set()
        for ws in self._websockets:
            try:
                await ws.send_text(msg_json)
            except Exception:
                disconnected.add(ws)

        # Clean up disconnected
        for ws in disconnected:
            self._websockets.discard(ws)


def create_preview_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    workspace: str = "workspace",
    cors_origins: list = None,
    hot_reload: bool = True,
) -> PreviewServer:
    """Factory function to create a preview server."""
    return PreviewServer(
        host=host,
        port=port,
        workspace=workspace,
        cors_origins=cors_origins,
        hot_reload=hot_reload,
    )


def run_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    workspace: str = "workspace",
    cors_origins: list = None,
    hot_reload: bool = True,
    reload: bool = False,
):
    """Run the preview server using uvicorn."""
    server = create_preview_server(
        host=host,
        port=port,
        workspace=workspace,
        cors_origins=cors_origins,
        hot_reload=hot_reload,
    )

    global _preview_server
    _preview_server = server

    # Handle signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    uvicorn.run(
        server.app,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIPENSA Runtime Preview Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--workspace", default="workspace", help="Workspace directory")
    parser.add_argument("--no-hot-reload", action="store_true", help="Disable hot reload")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload")

    args = parser.parse_args()

    run_server(
        host=args.host,
        port=args.port,
        workspace=args.workspace,
        hot_reload=not args.no_hot_reload,
        reload=args.reload,
    )