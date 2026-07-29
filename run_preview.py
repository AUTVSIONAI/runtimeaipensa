#!/usr/bin/env python
"""
Run the AIPENSA Runtime Preview Server
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from runtime.preview.server import run_server

if __name__ == "__main__":
    run_server(
        host="0.0.0.0",
        port=8081,
        workspace="workspace",
        cors_origins=["*"],
        hot_reload=True,
        reload=False,
    )