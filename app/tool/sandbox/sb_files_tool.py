import asyncio
import os
from pathlib import Path
from typing import Optional, TypeVar

from pydantic import Field

from app.tool.base import ToolResult
from app.utils.files_utils import clean_path, should_exclude_file
from app.utils.logger import logger
from app.tool.local_tool_base import LocalToolsBase


Context = TypeVar("Context")

_FILES_DESCRIPTION = """\
A local file system tool that allows file operations on the local machine.
* This tool provides commands for creating, reading, updating, and deleting files in the workspace
* All operations are performed relative to the workspace directory for security
* Use this when you need to manage files, edit code, or manipulate file contents locally
* Each action requires specific parameters as defined in the tool's dependencies
Key capabilities include:
* File creation: Create new files with specified content and permissions
* File modification: Replace specific strings or completely rewrite files
* File deletion: Remove files from the workspace
* File reading: Read file contents with optional line range specification
"""


class SandboxFilesTool(LocalToolsBase):
    name: str = "local_files"
    description: str = _FILES_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "create_file",
                    "str_replace",
                    "full_file_rewrite",
                    "delete_file",
                ],
                "description": "The file operation to perform",
            },
            "file_path": {
                "type": "string",
                "description": "Path to the file, relative to workspace (e.g., 'src/main.py')",
            },
            "file_contents": {
                "type": "string",
                "description": "Content to write to the file",
            },
            "old_str": {
                "type": "string",
                "description": "Text to be replaced (must appear exactly once)",
            },
            "new_str": {
                "type": "string",
                "description": "Replacement text",
            },
            "permissions": {
                "type": "string",
                "description": "File permissions in octal format (e.g., '644')",
                "default": "644",
            },
        },
        "required": ["action"],
        "dependencies": {
            "create_file": ["file_path", "file_contents"],
            "str_replace": ["file_path", "old_str", "new_str"],
            "full_file_rewrite": ["file_path", "file_contents"],
            "delete_file": ["file_path"],
        },
    }
    SNIPPET_LINES: int = Field(default=4, exclude=True)

    def __init__(
        self, thread_id: Optional[str] = None, **data
    ):
        """Initialize with optional thread_id."""
        super().__init__(**data)

    def clean_path(self, path: str) -> str:
        """Clean and normalize a path to be relative to workspace."""
        return clean_path(path, self.workspace_path)

    def _should_exclude_file(self, rel_path: str) -> bool:
        """Check if a file should be excluded based on path, name, or extension."""
        return should_exclude_file(rel_path)

    def _file_exists(self, path: str) -> bool:
        """Check if a file exists locally."""
        try:
            full_path = Path(path)
            return full_path.exists() and full_path.is_file()
        except Exception:
            return False

    async def get_workspace_state(self) -> dict:
        """Get the current workspace state by reading all files."""
        files_state = {}
        try:
            workspace = Path(self.workspace_path)
            if not workspace.exists():
                return {}

            for file_path in workspace.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(workspace))

                    # Skip excluded files
                    if self._should_exclude_file(rel_path):
                        continue

                    try:
                        content = file_path.read_text(encoding="utf-8")
                        stat = file_path.stat()
                        files_state[rel_path] = {
                            "content": content,
                            "is_dir": False,
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                        }
                    except UnicodeDecodeError:
                        logger.warning(f"Skipping binary file: {rel_path}")
                    except Exception as e:
                        logger.warning(f"Error reading file {rel_path}: {e}")

            return files_state

        except Exception as e:
            logger.error(f"Error getting workspace state: {str(e)}")
            return {}

    async def execute(
        self,
        action: str,
        file_path: Optional[str] = None,
        file_contents: Optional[str] = None,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
        permissions: Optional[str] = "644",
        **kwargs,
    ) -> ToolResult:
        """
        Execute a file operation in the local environment.
        """
        async with asyncio.Lock():
            try:
                # File creation
                if action == "create_file":
                    if not file_path or not file_contents:
                        return self.fail_response(
                            "file_path and file_contents are required for create_file"
                        )
                    return await self._create_file(
                        file_path, file_contents, permissions
                    )

                # String replacement
                elif action == "str_replace":
                    if not file_path or not old_str or not new_str:
                        return self.fail_response(
                            "file_path, old_str, and new_str are required for str_replace"
                        )
                    return await self._str_replace(file_path, old_str, new_str)

                # Full file rewrite
                elif action == "full_file_rewrite":
                    if not file_path or not file_contents:
                        return self.fail_response(
                            "file_path and file_contents are required for full_file_rewrite"
                        )
                    return await self._full_file_rewrite(
                        file_path, file_contents, permissions
                    )

                # File deletion
                elif action == "delete_file":
                    if not file_path:
                        return self.fail_response(
                            "file_path is required for delete_file"
                        )
                    return await self._delete_file(file_path)

                else:
                    return self.fail_response(f"Unknown action: {action}")

            except Exception as e:
                logger.error(f"Error executing file action: {e}")
                return self.fail_response(f"Error executing file action: {e}")

    async def _create_file(
        self, file_path: str, file_contents: str, permissions: str = "644"
    ) -> ToolResult:
        """Create a new file with the provided contents."""
        try:
            file_path = self.clean_path(file_path)
            full_path = Path(self.workspace_path) / file_path

            if full_path.exists():
                return self.fail_response(
                    f"File '{file_path}' already exists. Use full_file_rewrite to modify existing files."
                )

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file content
            full_path.write_text(file_contents, encoding="utf-8")
            # Set permissions (on Unix-like systems)
            try:
                full_path.chmod(int(permissions, 8))
            except Exception:
                pass  # Ignore permission errors on Windows

            message = f"File '{file_path}' created successfully."

            return self.success_response(message)
        except Exception as e:
            return self.fail_response(f"Error creating file: {str(e)}")

    async def _str_replace(
        self, file_path: str, old_str: str, new_str: str
    ) -> ToolResult:
        """Replace specific text in a file."""
        try:
            file_path = self.clean_path(file_path)
            full_path = Path(self.workspace_path) / file_path
            if not full_path.exists():
                return self.fail_response(f"File '{file_path}' does not exist")

            content = full_path.read_text(encoding="utf-8")
            old_str = old_str.expandtabs()
            new_str = new_str.expandtabs()

            occurrences = content.count(old_str)
            if occurrences == 0:
                return self.fail_response(f"String '{old_str}' not found in file")
            if occurrences > 1:
                lines = [
                    i + 1
                    for i, line in enumerate(content.split("\n"))
                    if old_str in line
                ]
                return self.fail_response(
                    f"Multiple occurrences found in lines {lines}. Please ensure string is unique"
                )

            # Perform replacement
            new_content = content.replace(old_str, new_str)
            full_path.write_text(new_content, encoding="utf-8")

            # Show snippet around the edit
            replacement_line = content.split(old_str)[0].count("\n")
            start_line = max(0, replacement_line - self.SNIPPET_LINES)
            end_line = replacement_line + self.SNIPPET_LINES + new_str.count("\n")
            snippet = "\n".join(new_content.split("\n")[start_line : end_line + 1])

            message = f"Replacement successful."

            return self.success_response(message)

        except Exception as e:
            return self.fail_response(f"Error replacing string: {str(e)}")

    async def _full_file_rewrite(
        self, file_path: str, file_contents: str, permissions: str = "644"
    ) -> ToolResult:
        """Completely rewrite an existing file with new content."""
        try:
            file_path = self.clean_path(file_path)
            full_path = Path(self.workspace_path) / file_path
            if not full_path.exists():
                return self.fail_response(
                    f"File '{file_path}' does not exist. Use create_file to create a new file."
                )

            full_path.write_text(file_contents, encoding="utf-8")
            try:
                full_path.chmod(int(permissions, 8))
            except Exception:
                pass

            message = f"File '{file_path}' completely rewritten successfully."

            return self.success_response(message)
        except Exception as e:
            return self.fail_response(f"Error rewriting file: {str(e)}")

    async def _delete_file(self, file_path: str) -> ToolResult:
        """Delete a file at the given path."""
        try:
            file_path = self.clean_path(file_path)
            full_path = Path(self.workspace_path) / file_path
            if not full_path.exists():
                return self.fail_response(f"File '{file_path}' does not exist")

            full_path.unlink()
            return self.success_response(f"File '{file_path}' deleted successfully.")
        except Exception as e:
            return self.fail_response(f"Error deleting file: {str(e)}")

    async def cleanup(self):
        """Clean up local resources (no-op for local tools)."""
        pass

    @classmethod
    def create_with_context(cls, context: Context) -> "LocalFilesTool[Context]":
        """Factory method to create a LocalFilesTool with a specific context."""
        raise NotImplementedError(
            "create_with_context not implemented for LocalFilesTool"
        )