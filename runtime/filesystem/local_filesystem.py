"""
Local File System Module Implementation

Provides file system operations using the local file system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio
import logging
import os
import shutil
import aiofiles
import mimetypes
from pathlib import Path

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    FileSystemModule,
    FileInfo,
)

logger = logging.getLogger(__name__)


class LocalFileSystemModule(FileSystemModule):
    """
    Local file system implementation using aiofiles for async operations.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="filesystem",
            version="1.0.0",
            description="Local file system operations",
            author="AIPENSA",
            dependencies=[],
            provides=["file_read", "file_write", "file_delete", "file_list", "file_search"],
            tags={"local", "filesystem", "storage"},
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._config = config or {}
        self._workspace = self._config.get("workspace", "workspace")
        self._allowed_paths = self._config.get("allowed_paths", [])
        self._blocked_paths = self._config.get("blocked_paths", [".git", "__pycache__", "node_modules", ".venv"])

        # Ensure workspace exists
        os.makedirs(self._workspace, exist_ok=True)

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._workspace = self._config.get("workspace", self._workspace)
        self._allowed_paths = self._config.get("allowed_paths", self._allowed_paths)
        self._blocked_paths = self._config.get("blocked_paths", self._blocked_paths)
        os.makedirs(self._workspace, exist_ok=True)
        self.state = ModuleState.INITIALIZED
        logger.info("LocalFileSystemModule initialized")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("LocalFileSystemModule started")

    async def stop(self) -> None:
        self.state = ModuleState.STOPPED
        logger.info("LocalFileSystemModule stopped")

    async def cleanup(self) -> None:
        self.state = ModuleState.UNINITIALIZED
        logger.info("LocalFileSystemModule cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "filesystem",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "workspace": self._workspace,
        }

    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to workspace and validate access."""
        # Convert to absolute path
        if not os.path.isabs(path):
            full_path = os.path.join(self._workspace, path)
        else:
            full_path = path

        # Normalize path
        full_path = os.path.normpath(full_path)

        # Check blocked paths
        for blocked in self._blocked_paths:
            if blocked in full_path:
                raise PermissionError(f"Access to path blocked: {blocked}")

        # Check allowed paths if configured
        if self._allowed_paths:
            allowed = False
            for allowed_path in self._allowed_paths:
                if full_path.startswith(os.path.abspath(allowed_path)):
                    allowed = True
                    break
            if not allowed:
                raise PermissionError(f"Path not in allowed paths: {full_path}")

        return full_path

    async def read_file(self, path: str, encoding: str = "utf-8") -> str:
        """Read file contents."""
        full_path = self._resolve_path(path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        if not os.path.isfile(full_path):
            raise ValueError(f"Path is not a file: {path}")

        async with aiofiles.open(full_path, "r", encoding=encoding) as f:
            return await f.read()

    async def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True
    ) -> FileInfo:
        """Write file contents."""
        full_path = self._resolve_path(path)

        if create_dirs:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

        async with aiofiles.open(full_path, "w", encoding=encoding) as f:
            await f.write(content)

        stat = os.stat(full_path)
        return FileInfo(
            path=path,
            name=os.path.basename(path),
            is_directory=False,
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            created_at=datetime.fromtimestamp(stat.st_ctime),
            mime_type=mimetypes.guess_type(path)[0],
        )

    async def delete_file(self, path: str) -> bool:
        """Delete file or directory."""
        full_path = self._resolve_path(path)

        if not os.path.exists(full_path):
            return False

        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)

        return True

    async def list_directory(
        self,
        path: str,
        recursive: bool = False,
        pattern: Optional[str] = None
    ) -> List[FileInfo]:
        """List directory contents."""
        full_path = self._resolve_path(path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Directory not found: {path}")

        if not os.path.isdir(full_path):
            raise ValueError(f"Path is not a directory: {path}")

        files = []

        if recursive:
            for root, dirs, filenames in os.walk(full_path):
                # Filter blocked paths
                dirs[:] = [d for d in dirs if not any(b in os.path.join(root, d) for b in self._blocked_paths)]

                for filename in filenames:
                    if pattern and not self._match_pattern(filename, pattern):
                        continue
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, full_path)
                    stat = os.stat(file_path)
                    files.append(FileInfo(
                        path=rel_path,
                        name=filename,
                        is_directory=False,
                        size=stat.st_size,
                        modified_at=datetime.fromtimestamp(stat.st_mtime),
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        mime_type=mimetypes.guess_type(filename)[0],
                    ))
        else:
            for entry in os.scandir(full_path):
                if entry.name.startswith(".") or any(b in entry.name for b in self._blocked_paths):
                    continue
                if pattern and not self._match_pattern(entry.name, pattern):
                    continue
                if entry.is_file():
                    stat = entry.stat()
                    files.append(FileInfo(
                        path=os.path.relpath(entry.path, full_path) if full_path != self._workspace else entry.name,
                        name=entry.name,
                        is_directory=False,
                        size=stat.st_size,
                        modified_at=datetime.fromtimestamp(stat.st_mtime),
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        mime_type=mimetypes.guess_type(entry.name)[0],
                    ))

        return files

    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Match filename against glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)

    async def exists(self, path: str) -> bool:
        """Check if path exists."""
        try:
            full_path = self._resolve_path(path)
            return os.path.exists(full_path)
        except Exception:
            return False

    async def copy_file(self, src: str, dst: str) -> FileInfo:
        """Copy file."""
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)

        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source not found: {src}")

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy2(src_path, dst_path)

        stat = os.stat(dst_path)
        return FileInfo(
            path=dst,
            name=os.path.basename(dst),
            is_directory=False,
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            created_at=datetime.fromtimestamp(stat.st_ctime),
        )

    async def move_file(self, src: str, dst: str) -> FileInfo:
        """Move/rename file."""
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)

        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source not found: {src}")

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.move(src_path, dst_path)

        stat = os.stat(dst_path)
        return FileInfo(
            path=dst,
            name=os.path.basename(dst),
            is_directory=os.path.isdir(dst_path),
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            created_at=datetime.fromtimestamp(stat.st_ctime),
        )

    async def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Get file info."""
        try:
            full_path = self._resolve_path(path)
            if not os.path.exists(full_path):
                return None

            stat = os.stat(full_path)
            return FileInfo(
                path=path,
                name=os.path.basename(path),
                is_directory=os.path.isdir(full_path),
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                created_at=datetime.fromtimestamp(stat.st_ctime),
                mime_type=mimetypes.guess_type(path)[0],
            )
        except Exception:
            return None

    async def search_files(
        self,
        pattern: str,
        path: str = ".",
        content_pattern: Optional[str] = None
    ) -> List[FileInfo]:
        """Search files by name and optionally content."""
        full_path = self._resolve_path(path)
        results = []

        for root, dirs, filenames in os.walk(full_path):
            dirs[:] = [d for d in dirs if not any(b in os.path.join(root, d) for b in self._blocked_paths)]

            for filename in filenames:
                if not self._match_pattern(filename, pattern):
                    continue

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, full_path)

                # Check content if pattern provided
                if content_pattern:
                    try:
                        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                            content = await f.read()
                            if content_pattern not in content:
                                continue
                    except Exception:
                        continue

                stat = os.stat(file_path)
                results.append(FileInfo(
                    path=rel_path,
                    name=filename,
                    is_directory=False,
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    mime_type=mimetypes.guess_type(filename)[0],
                ))

        return results