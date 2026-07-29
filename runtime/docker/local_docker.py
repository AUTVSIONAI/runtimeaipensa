"""
Local Docker Module Implementation

Provides Docker container management using the Docker SDK.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncIterator
import asyncio
import logging
import os

try:
    import docker
    from docker.errors import DockerException, NotFound
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DockerException = Exception
    NotFound = Exception
    DOCKER_AVAILABLE = False

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    DockerModule,
    ContainerInfo,
)

logger = logging.getLogger(__name__)


class LocalDockerModule(DockerModule):
    """
    Local Docker implementation using docker-py.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="docker",
            version="1.0.0",
            description="Local Docker container management",
            author="AIPENSA",
            dependencies=[],
            provides=["container_run", "container_stop", "container_logs", "container_inspect"],
            tags={"local", "docker", "container"},
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._config = config or {}
        self._client: Optional[docker.DockerClient] = None
        self._base_url = self._config.get("docker_url", "unix:///var/run/docker.sock")

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._base_url = self._config.get("docker_url", self._base_url)

        if not DOCKER_AVAILABLE:
            raise RuntimeError("Docker module not available - install docker-py")

        self.state = ModuleState.INITIALIZED
        logger.info("LocalDockerModule initialized")

    async def start(self) -> None:
        """Initialize Docker client."""
        if not DOCKER_AVAILABLE:
            raise RuntimeError("docker-py not installed")

        try:
            self._client = docker.DockerClient(base_url=self._base_url)
            # Test connection
            self._client.ping()
            self.state = ModuleState.RUNNING
            logger.info("LocalDockerModule started")
        except DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")

    async def stop(self) -> None:
        """Close Docker client."""
        if self._client:
            self._client.close()
            self._client = None
        self.state = ModuleState.STOPPED
        logger.info("LocalDockerModule stopped")

    async def cleanup(self) -> None:
        await self.stop()
        self.state = ModuleState.UNINITIALIZED
        logger.info("LocalDockerModule cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        healthy = False
        if self._client:
            try:
                self._client.ping()
                healthy = True
            except Exception:
                pass

        return {
            "module": "docker",
            "status": self.state.value,
            "healthy": healthy and self.state == ModuleState.RUNNING,
            "docker_available": DOCKER_AVAILABLE,
        }

    async def run_container(
        self,
        image: str,
        name: Optional[str] = None,
        command: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[int, int]] = None,
        volumes: Optional[Dict[str, str]] = None,
        detach: bool = True,
        **kwargs
    ) -> ContainerInfo:
        """Run a Docker container."""
        if not self._client:
            raise RuntimeError("Docker module not started")

        try:
            # Prepare container config
            container_config = {
                "image": image,
                "command": command,
                "environment": env_vars or {},
                "ports": ports or {},
                "volumes": volumes or {},
                "detach": detach,
                **kwargs
            }

            # Pull image if not present
            images = self._client.images.list(name=image)
            if not images:
                logger.info(f"Pulling image: {image}")
                self._client.images.pull(image)

            # Run container
            container = self._client.containers.run(
                **container_config,
                name=name,
            )

            # Get container info
            info = self._container_to_info(container)

            return info

        except DockerException as e:
            raise RuntimeError(f"Failed to run container: {e}")

    async def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """Stop a container."""
        if not self._client:
            raise RuntimeError("Docker module not started")

        try:
            container = self._client.containers.get(container_id)
            container.stop(timeout=timeout)
            return True
        except NotFound:
            return False
        except DockerException as e:
            logger.error(f"Failed to stop container: {e}")
            return False

    async def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container."""
        if not self._client:
            raise RuntimeError("Docker module not started")

        try:
            container = self._client.containers.get(container_id)
            container.remove(force=force)
            return True
        except NotFound:
            return False
        except DockerException as e:
            logger.error(f"Failed to remove container: {e}")
            return False

    async def get_logs(
        self,
        container_id: str,
        tail: int = 100,
        follow: bool = False,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> AsyncIterator[str]:
        """Get container logs."""
        if not self._client:
            raise RuntimeError("Docker module not started")

        try:
            container = self._client.containers.get(container_id)
            logs = container.logs(
                tail=tail,
                follow=follow,
                since=since,
                until=until,
                stream=follow,
            )

            if follow:
                async for log in self._stream_logs(logs):
                    yield log
            else:
                yield logs.decode("utf-8", errors="replace")

        except NotFound:
            yield f"Container {container_id} not found"
        except DockerException as e:
            yield f"Error getting logs: {e}"

    async def _stream_logs(self, logs) -> AsyncIterator[str]:
        """Stream logs asynchronously."""
        for log in logs:
            yield log.decode("utf-8", errors="replace")
            await asyncio.sleep(0)

    async def inspect_container(self, container_id: str) -> Optional[ContainerInfo]:
        """Inspect a container."""
        if not self._client:
            raise RuntimeError("Docker module not started")

        try:
            container = self._client.containers.get(container_id)
            return self._container_to_info(container)
        except NotFound:
            return None
        except DockerException as e:
            logger.error(f"Failed to inspect container: {e}")
            return None

    async def list_containers(self, all: bool = True) -> List[ContainerInfo]:
        """List containers."""
        if not self._client:
            raise RuntimeError("Docker module not started")

        containers = self._client.containers.list(all=all)
        return [self._container_to_info(c) for c in containers]

    def _container_to_info(self, container) -> ContainerInfo:
        """Convert Docker container to ContainerInfo."""
        status = container.status
        if container.status == "running":
            status = "running"
        elif container.status in ("exited", "dead"):
            status = "stopped"
        elif container.status == "created":
            status = "created"
        elif container.status in ("paused", "restarting"):
            status = "running"

        return ContainerInfo(
            container_id=container.id[:12],
            name=container.name,
            image=container.image.tags[0] if container.image.tags else container.image.id[:12],
            status=status,
            created_at=datetime.fromisoformat(container.attrs["Created"].replace("Z", "+00:00")),
            ports=container.attrs.get("NetworkSettings", {}).get("Ports", {}),
            env_vars={e.split("=")[0]: e.split("=", 1)[1] for e in container.attrs.get("Config", {}).get("Env", []) if "=" in e},
        )

    async def build_image(
        self,
        path: str,
        tag: str,
        dockerfile: str = "Dockerfile",
        **kwargs
    ) -> str:
        """Build a Docker image."""
        if not self._client:
            raise RuntimeError("Docker module not started")

        try:
            image, logs = self._client.images.build(
                path=path,
                tag=tag,
                dockerfile=dockerfile,
                **kwargs
            )
            return image.id
        except DockerException as e:
            raise RuntimeError(f"Failed to build image: {e}")

    async def pull_image(self, image: str) -> None:
        """Pull a Docker image."""
        if not self._client:
            raise RuntimeError("Docker module not started")

        try:
            self._client.images.pull(image)
        except DockerException as e:
            raise RuntimeError(f"Failed to pull image: {e}")