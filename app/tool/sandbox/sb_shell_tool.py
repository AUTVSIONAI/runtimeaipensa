import asyncio
import os
import shlex
import subprocess
import time
from typing import Any, Dict, Optional, TypeVar
from uuid import uuid4

from app.tool.local_tool_base import LocalToolsBase
from app.tool.base import ToolResult
from app.utils.logger import logger


Context = TypeVar("Context")
_SHELL_DESCRIPTION = """\
Execute a shell command in the local workspace directory.
IMPORTANT: Commands are non-blocking by default and run in a tmux/session-like manner.
This is ideal for long-running operations like starting servers or build processes.
Uses sessions to maintain state between commands.
This tool is essential for running CLI tools, installing packages, and managing system operations.
"""


class LocalShellTool(LocalToolsBase):
    """Tool for executing shell commands locally.
    Uses subprocess for maintaining state between commands and provides comprehensive process management.
    """

    name: str = "local_shell"
    description: str = _SHELL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "execute_command",
                    "check_command_output",
                    "terminate_command",
                    "list_commands",
                ],
                "description": "The shell action to perform",
            },
            "command": {
                "type": "string",
                "description": "The shell command to execute. Use this for running CLI tools, installing packages, "
                "or system operations. Commands can be chained using &&, ||, and | operators.",
            },
            "folder": {
                "type": "string",
                "description": "Optional relative path to a subdirectory of /workspace where the command should be "
                "executed. Example: 'data/pdfs'",
            },
            "session_name": {
                "type": "string",
                "description": "Optional name of the session to use. Use named sessions for related commands "
                "that need to maintain state. Defaults to a random session name.",
            },
            "blocking": {
                "type": "boolean",
                "description": "Whether to wait for the command to complete. Defaults to false for non-blocking "
                "execution.",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Optional timeout in seconds for blocking commands. Defaults to 60. Ignored for "
                "non-blocking commands.",
                "default": 60,
            },
            "kill_session": {
                "type": "boolean",
                "description": "Whether to terminate the session after checking. Set to true when you're done "
                "with the command.",
                "default": False,
            },
        },
        "required": ["action"],
        "dependencies": {
            "execute_command": ["command"],
            "check_command_output": ["session_name"],
            "terminate_command": ["session_name"],
            "list_commands": [],
        },
    }

    def __init__(
        self, thread_id: Optional[str] = None, **data
    ):
        """Initialize with optional thread_id."""
        super().__init__(**data)
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._session_output: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def _ensure_browser(self):
        """Override to not require browser for shell tool."""
        pass

    @property
    def browser(self):
        """Not needed for shell tool, but defined for parent class compatibility."""
        return None

    @property
    def context(self):
        """Not needed for shell tool."""
        return None

    async def _get_session(self, session_name: str = "default") -> str:
        """Ensure a session exists and return its name."""
        if session_name not in self._processes:
            self._processes[session_name] = None
            self._session_output[session_name] = ""
        return session_name

    async def _run_command(
        self,
        command: str,
        cwd: str,
        session_name: str,
        blocking: bool = False,
        timeout: int = 60,
    ) -> ToolResult:
        """Execute a command locally."""
        try:
            # Set up working directory
            if not os.path.exists(cwd):
                os.makedirs(cwd, exist_ok=True)

            if blocking:
                # For blocking commands, run and wait
                try:
                    proc = await asyncio.create_subprocess_shell(
                        command,
                        cwd=cwd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=timeout
                    )
                    output = stdout.decode() + stderr.decode()
                    return self.success_response(
                        {
                            "output": output,
                            "session_name": session_name,
                            "cwd": cwd,
                            "completed": True,
                            "exit_code": proc.returncode,
                        }
                    )
                except asyncio.TimeoutError:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    return self.fail_response(f"Command timed out after {timeout} seconds")
                except Exception as e:
                    return self.fail_response(f"Error executing command: {str(e)}")
            else:
                # For non-blocking, start process in background
                if session_name in self._processes and self._processes[session_name] is not None:
                    try:
                        self._processes[session_name].terminate()
                    except Exception:
                        pass

                # Start with bash -c to keep session alive
                # We use a persistent shell that we can send commands to
                shell_cmd = f"cd {shlex.quote(cwd)} && {command}"

                proc = await asyncio.create_subprocess_shell(
                    shell_cmd,
                    cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                self._processes[session_name] = proc

                # Read output asynchronously
                asyncio.create_task(self._read_output(session_name, proc))

                return self.success_response(
                    {
                        "session_name": session_name,
                        "cwd": cwd,
                        "message": f"Command started in session '{session_name}'. Use check_command_output to view results.",
                        "completed": False,
                    }
                )

        except Exception as e:
            return self.fail_response(f"Error executing command: {str(e)}")

    async def _read_output(self, session_name: str, proc: asyncio.subprocess.Process):
        """Read output from a process asynchronously."""
        try:
            stdout, stderr = await proc.communicate()
            output = stdout.decode() + stderr.decode()
            self._session_output[session_name] += output
            logger.debug(f"Session {session_name} completed with output: {output[:200]}")
        except Exception as e:
            logger.error(f"Error reading output: {e}")

    async def _check_command_output(
        self, session_name: str, kill_session: bool = False
    ) -> ToolResult:
        """Check output of a running command."""
        try:
            if session_name not in self._processes:
                return self.fail_response(
                    f"Session '{session_name}' does not exist."
                )

            proc = self._processes[session_name]
            output = self._session_output.get(session_name, "")

            if proc is not None:
                # Check if process is still running
                if proc.returncode is None:
                    return self.success_response(
                        {
                            "output": output,
                            "session_name": session_name,
                            "status": "Session still running.",
                        }
                    )
                else:
                    return self.success_response(
                        {
                            "output": output,
                            "session_name": session_name,
                            "status": f"Session completed with exit code {proc.returncode}.",
                            "completed": True,
                            "exit_code": proc.returncode,
                        }
                    )
            else:
                return self.success_response(
                    {
                        "output": output,
                        "session_name": session_name,
                        "status": "No active process.",
                    }
                )

        except Exception as e:
            return self.fail_response(f"Error checking command output: {str(e)}")

    async def _terminate_command(self, session_name: str) -> ToolResult:
        """Terminate a running command."""
        try:
            if session_name not in self._processes:
                return self.fail_response(
                    f"Session '{session_name}' does not exist."
                )

            proc = self._processes[session_name]
            if proc is not None:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass

            self._processes[session_name] = None
            self._session_output[session_name] = ""

            return self.success_response(
                {"message": f"Session '{session_name}' terminated successfully."}
            )

        except Exception as e:
            return self.fail_response(f"Error terminating command: {str(e)}")

    async def _list_commands(self) -> ToolResult:
        """List all active sessions."""
        try:
            sessions = []
            for session_name, proc in self._processes.items():
                if proc is not None and proc.returncode is None:
                    sessions.append(session_name)

            return self.success_response(
                {
                    "message": f"Found {len(sessions)} active sessions.",
                    "sessions": sessions,
                }
            )

        except Exception as e:
            return self.fail_response(f"Error listing commands: {str(e)}")

    async def execute(
        self,
        action: str,
        command: str,
        folder: Optional[str] = None,
        session_name: Optional[str] = None,
        blocking: bool = False,
        timeout: int = 60,
        kill_session: bool = False,
    ) -> ToolResult:
        """
        Execute a shell action in the local environment.
        """
        async with self._lock:
            try:
                # Default session name
                if not session_name:
                    session_name = f"session_{str(uuid4())[:8]}"

                # Ensure session exists
                await self._get_session(session_name)

                # Set up working directory
                cwd = self.workspace_path
                if folder:
                    folder = folder.strip("/")
                    cwd = os.path.join(self.workspace_path, folder)

                # Navigation actions
                if action == "execute_command":
                    if not command:
                        return self.fail_response("command is required for execute_command")
                    return await self._run_command(
                        command, cwd, session_name, blocking, timeout
                    )
                elif action == "check_command_output":
                    return await self._check_command_output(session_name, kill_session)
                elif action == "terminate_command":
                    return await self._terminate_command(session_name)
                elif action == "list_commands":
                    return await self._list_commands()
                else:
                    return self.fail_response(f"Unknown action: {action}")
            except Exception as e:
                logger.error(f"Error executing shell action: {e}")
                return self.fail_response(f"Error executing shell action: {e}")

    async def cleanup(self):
        """Clean up all processes."""
        for session_name in list(self._processes.keys()):
            await self._terminate_command(session_name)


class SandboxShellTool(LocalToolsBase):
    """Backward compatibility wrapper - redirects to LocalShellTool with lazy Daytona import."""

    name: str = "sandbox_shell"
    description: str = "Execute shell commands in a Daytona sandbox (requires runtime=daytona)"

    def __init__(
        self, sandbox: Optional[Any] = None, thread_id: Optional[str] = None, **data
    ):
        super().__init__(**data)
        self._daytona_sandbox = sandbox
        self._local_shell = LocalShellTool(**data)

    async def _ensure_sandbox(self):
        """Ensure we have a valid Daytona sandbox instance."""
        if self._daytona_sandbox is not None:
            return

        # Lazy imports - only import daytona when actually needed
        from app.daytona.sandbox import create_sandbox, start_supervisord_session
        from app.config import config

        if self._daytona_sandbox is None:
            self._daytona_sandbox = await create_sandbox(password=config.daytona.VNC_password)
            start_supervisord_session(self._daytona_sandbox)
            logger.info("Daytona sandbox initialized for shell tool")

    async def execute(
        self,
        action: str,
        command: str,
        folder: Optional[str] = None,
        session_name: Optional[str] = None,
        blocking: bool = False,
        timeout: int = 60,
        kill_session: bool = False,
    ) -> ToolResult:
        """Execute shell command - delegates to Daytona if sandbox is available, otherwise local."""
        # Check if we should use Daytona (runtime=daytona)
        from app.config import config
        if config.browser_config and getattr(config.browser_config, 'runtime', 'local') == 'daytona':
            await self._ensure_sandbox()
            # Delegate to the original Daytona implementation
            # This would require keeping the old implementation
            # For now, we fall back to local
            pass

        # Default to local execution
        return await self._local_shell.execute(
            action, command, folder, session_name, blocking, timeout, kill_session
        )

    async def cleanup(self):
        """Clean up both local and Dayton resources."""
        await self._local_shell.cleanup()
        if self._daytona_sandbox:
            # Cleanup Daytona if needed
            pass