"""
Local Execution Module Implementation

Provides local code execution and shell command execution capabilities.
Uses subprocess for shell commands and can integrate with Docker for isolated execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio
import subprocess
import os
import sys
import uuid
import logging
import tempfile
import shlex

# Fix for Windows subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    ExecutionModule,
    ExecutionResult,
    SandboxInfo,
)

logger = logging.getLogger(__name__)


@dataclass
class _Sandbox:
    """Internal sandbox representation."""
    sandbox_id: str
    work_dir: str
    process: Optional[asyncio.subprocess.Process] = None
    status: str = "created"
    created_at: datetime = field(default_factory=datetime.utcnow)
    env: Dict[str, str] = field(default_factory=dict)


class LocalExecutionModule(ExecutionModule):
    """
    Local execution module for running code and shell commands.

    Supports:
    - Python code execution
    - Shell command execution
    - Optional Docker sandboxing for isolation
    - Session management for persistent state
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="execution",
            version="1.0.0",
            description="Local code and command execution",
            author="AIPENSA",
            dependencies=[],
            provides=["python_execution", "shell_execution", "sandbox_management"],
            tags={"local", "execution", "shell", "python"},
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._config = config or {}
        self._sandboxes: Dict[str, _Sandbox] = {}
        self._work_dir = self._config.get("work_dir", "workspace")
        self._timeout = self._config.get("timeout_seconds", 300)
        self._lock = asyncio.Lock()

        # Ensure work directory exists
        os.makedirs(self._work_dir, exist_ok=True)

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._work_dir = self._config.get("work_dir", self._work_dir)
        self._timeout = self._config.get("timeout_seconds", self._timeout)
        os.makedirs(self._work_dir, exist_ok=True)
        self.state = ModuleState.INITIALIZED
        logger.info("LocalExecutionModule initialized")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("LocalExecutionModule started")

    async def stop(self) -> None:
        # Clean up all sandboxes
        await self._cleanup_all_sandboxes()
        self.state = ModuleState.STOPPED
        logger.info("LocalExecutionModule stopped")

    async def cleanup(self) -> None:
        await self._cleanup_all_sandboxes()
        self._sandboxes.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("LocalExecutionModule cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "execution",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "active_sandboxes": len(self._sandboxes),
            "work_dir": self._work_dir,
        }

    async def _cleanup_all_sandboxes(self) -> None:
        async with self._lock:
            for sandbox_id, sandbox in list(self._sandboxes.items()):
                try:
                    if sandbox.process:
                        sandbox.process.terminate()
                        try:
                            await asyncio.wait_for(sandbox.process.wait(), timeout=5)
                        except asyncio.TimeoutError:
                            sandbox.process.kill()
                except Exception as e:
                    logger.warning(f"Error cleaning up sandbox {sandbox_id}: {e}")

    def _get_sandbox_env(self, sandbox: _Sandbox) -> Dict[str, str]:
        """Get environment for sandbox execution."""
        env = os.environ.copy()
        env.update(sandbox.env)
        env.setdefault("PYTHONPATH", self._work_dir)
        return env

    async def execute_python(
        self,
        code: str,
        sandbox_id: Optional[str] = None,
        timeout_seconds: int = 30,
        packages: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute Python code."""
        start_time = datetime.utcnow()

        # Install packages if requested
        if packages:
            for pkg in packages:
                try:
                    await self._install_package(pkg, sandbox_id)
                except Exception as e:
                    logger.warning(f"Failed to install package {pkg}: {e}")

        # Prepare execution
        if sandbox_id and sandbox_id in self._sandboxes:
            sandbox = self._sandboxes[sandbox_id]
            work_dir = sandbox.work_dir
            env = self._get_sandbox_env(sandbox)
            if env_vars:
                env.update(env_vars)
        else:
            work_dir = self._work_dir
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

        # Write code to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", dir=work_dir, delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Execute
            process = await asyncio.create_subprocess_exec(
                sys.executable, temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                exec_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return ExecutionResult(
                    success=False,
                    output="",
                    stderr="Execution timed out",
                    error="Timeout",
                    execution_time=exec_time / 1000.0,
                    execution_time_ms=exec_time,
                    exit_code=-1,
                )

            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            execution_time = execution_time_ms / 1000.0
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            return ExecutionResult(
                success=process.returncode == 0,
                output=stdout_str,
                error=stderr_str if process.returncode != 0 else None,
                execution_time=execution_time,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode,
                execution_time_ms=execution_time_ms,
            )

        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    async def _install_package(self, package: str, sandbox_id: Optional[str] = None) -> None:
        """Install a Python package."""
        work_dir = self._work_dir
        if sandbox_id and sandbox_id in self._sandboxes:
            work_dir = self._sandboxes[sandbox_id].work_dir

        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", package,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
        )
        await process.communicate()

    async def execute_shell(
        self,
        command: str,
        sandbox_id: Optional[str] = None,
        timeout_seconds: int = 60,
        working_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute shell command."""
        start_time = datetime.utcnow()

        if sandbox_id and sandbox_id in self._sandboxes:
            sandbox = self._sandboxes[sandbox_id]
            work_dir = working_dir or sandbox.work_dir
            env = self._get_sandbox_env(sandbox)
        else:
            work_dir = working_dir or self._work_dir
            env = os.environ.copy()

        if env_vars:
            env.update(env_vars)

        # Parse command
        if isinstance(command, str):
            cmd = shlex.split(command)
        else:
            cmd = command

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Command timed out after {timeout_seconds}s",
                    exit_code=-1,
                    execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    error="Timeout",
                )

            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            return ExecutionResult(
                success=process.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=process.returncode,
                execution_time_ms=execution_time_ms,
            )

        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Command not found: {cmd[0]}",
                exit_code=127,
                execution_time_ms=0,
                error="Command not found",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=0,
                error=str(e),
            )

    async def create_sandbox(
        self,
        image: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> SandboxInfo:
        """Create a new sandbox (local directory-based)."""
        sandbox_id = f"sandbox_{uuid.uuid4().hex[:8]}"
        work_dir = os.path.join(self._work_dir, sandbox_id)
        os.makedirs(work_dir, exist_ok=True)

        # If Docker is configured, we could create a container here
        # For now, just create a directory-based sandbox
        sandbox = _Sandbox(
            sandbox_id=sandbox_id,
            work_dir=work_dir,
            env=config.get("env_vars", {}) if config else {},
        )

        async with self._lock:
            self._sandboxes[sandbox_id] = sandbox

        return SandboxInfo(
            sandbox_id=sandbox_id,
            status=sandbox.status,
            image=image or "local",
            created_at=sandbox.created_at,
        )

    async def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Destroy sandbox."""
        async with self._lock:
            if sandbox_id in self._sandboxes:
                sandbox = self._sandboxes[sandbox_id]
                if sandbox.process:
                    sandbox.process.terminate()
                    try:
                        await asyncio.wait_for(sandbox.process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        sandbox.process.kill()
                del self._sandboxes[sandbox_id]

                # Clean up work directory
                try:
                    import shutil
                    shutil.rmtree(sandbox.work_dir, ignore_errors=True)
                except Exception:
                    pass
                return True
        return False

    async def get_sandbox(self, sandbox_id: str) -> Optional[SandboxInfo]:
        async with self._lock:
            if sandbox_id in self._sandboxes:
                sandbox = self._sandboxes[sandbox_id]
                return SandboxInfo(
                    sandbox_id=sandbox_id,
                    status=sandbox.status,
                    image="local",
                    created_at=sandbox.created_at,
                )
        return None

    async def list_sandboxes(self) -> List[SandboxInfo]:
        async with self._lock:
            return [
                SandboxInfo(
                    sandbox_id=s.sandbox_id,
                    status=s.status,
                    image="local",
                    created_at=s.created_at,
                )
                for s in self._sandboxes.values()
            ]

    async def install_package(
        self,
        sandbox_id: str,
        package: str,
        package_manager: str = "pip"
    ) -> ExecutionResult:
        """Install package in sandbox."""
        if sandbox_id not in self._sandboxes:
            return ExecutionResult(success=False, error="Sandbox not found")

        sandbox = self._sandboxes[sandbox_id]
        return await self.execute_shell(
            f"{sys.executable} -m {package_manager} install {package}",
            sandbox_id=sandbox_id,
        )