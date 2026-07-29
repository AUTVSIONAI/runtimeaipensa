#!/usr/bin/env python
"""
AIPENSA Runtime Preview Server Entry Point

Standalone FastAPI server for previewing generated websites with hot reload.
Run with: python preview_server.py

Or from the frontend: npm run preview
"""

import argparse
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from runtime.preview.server import PreviewServer


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("preview")


# Global server reference for signal handling
_preview_server: PreviewServer = None


def load_preview_config() -> dict:
    """Load preview configuration from runtime.toml or environment."""
    import tomli

    config = {
        "host": "0.0.0.0",
        "port": 8080,
        "workspace": "workspace",
        "cors_origins": ["*"],
        "hot_reload": True,
    }

    # Try to load from runtime.toml
    runtime_toml = Path(__file__).parent / "runtime.toml"
    if runtime_toml.exists():
        try:
            with open(runtime_toml, "rb") as f:
                data = tomli.load(f)
                if "preview" in data:
                    preview = data["preview"]
                    config.update({
                        "host": preview.get("host", config["host"]),
                        "port": preview.get("port", config["port"]),
                        "workspace": preview.get("workspace", config["workspace"]),
                        "cors_origins": preview.get("cors_origins", config["cors_origins"]),
                        "hot_reload": preview.get("hot_reload", config["hot_reload"]),
                    })
        except Exception as e:
            logger.warning(f"Could not load preview config from runtime.toml: {e}")

    # Environment variables override config
    if os.getenv("PREVIEW_HOST"):
        config["host"] = os.getenv("PREVIEW_HOST")
    if os.getenv("PREVIEW_PORT"):
        config["port"] = int(os.getenv("PREVIEW_PORT"))
    if os.getenv("PREVIEW_WORKSPACE"):
        config["workspace"] = os.getenv("PREVIEW_WORKSPACE")

    return config


def run_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    workspace: str = "workspace",
    cors_origins: list = None,
    hot_reload: bool = True,
    reload: bool = False,
):
    """Run the preview server using uvicorn."""
    global _preview_server

    _preview_server = PreviewServer(
        host=host,
        port=port,
        workspace=workspace,
        cors_origins=cors_origins or ["*"],
        hot_reload=hot_reload,
    )

    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(f"Preview server starting on http://{host}:{port}")
    logger.info(f"Serving workspace: {workspace}")
    if hot_reload:
        logger.info("Hot reload enabled")

    uvicorn.run(
        _preview_server.app,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


def main():
    parser = argparse.ArgumentParser(description="AIPENSA Runtime Preview Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--workspace", default="workspace", help="Workspace directory")
    parser.add_argument("--no-hot-reload", action="store_true", help="Disable hot reload")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload")

    args = parser.parse_args()

    # Load config from file (CLI args override)
    config = load_preview_config()
    config.update({
        "host": args.host,
        "port": args.port,
        "workspace": args.workspace,
        "hot_reload": not args.no_hot_reload,
    })

    run_server(**config, reload=args.reload)


if __name__ == "__main__":
    main()