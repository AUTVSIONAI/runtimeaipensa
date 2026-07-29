"""
Dependency Injection Container for AIPENSA Runtime

Provides a clean DI mechanism so no agent/module needs to directly instantiate
any component. Everything comes from the container.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, get_type_hints
import asyncio
import inspect
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceLifetime(Enum):
    """Service lifetime scopes."""

    SINGLETON = "singleton"      # One instance per container
    SCOPED = "scoped"            # One instance per scope (request)
    TRANSIENT = "transient"      # New instance every time


class ServiceDescriptor:
    """Describes how a service should be created."""

    def __init__(
        self,
        service_type: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        instance: Optional[Any] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        tags: List[str] = None,
    ):
        self.service_type = service_type
        self.implementation = implementation or service_type
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
        self.tags = tags or []


class Scope:
    """A service scope for scoped lifetime management."""

    def __init__(self, container: "Container", parent: Optional["Scope"] = None):
        self.container = container
        self.parent = parent
        self._instances: Dict[Type, Any] = {}
        self._disposables: List[Any] = []

    def get_or_create(self, descriptor: ServiceDescriptor) -> Any:
        """Get or create an instance based on lifetime."""
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self.container._get_or_create_singleton(descriptor)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._get_or_create_scoped(descriptor)
        else:  # TRANSIENT
            return self.container._create_instance(descriptor)

    def _get_or_create_scoped(self, descriptor: ServiceDescriptor) -> Any:
        if descriptor.service_type in self._instances:
            return self._instances[descriptor.service_type]

        instance = self.container._create_instance(descriptor)
        self._instances[descriptor.service_type] = instance

        # Track for disposal if it implements async close
        if hasattr(instance, "close") and asyncio.iscoroutinefunction(instance.close):
            self._disposables.append(instance)
        elif hasattr(instance, "cleanup") and asyncio.iscoroutinefunction(instance.cleanup):
            self._disposables.append(instance)

        return instance

    async def dispose(self) -> None:
        """Dispose all scoped instances."""
        for instance in reversed(self._disposables):
            try:
                if hasattr(instance, "close"):
                    await instance.close()
                elif hasattr(instance, "cleanup"):
                    await instance.cleanup()
            except Exception as e:
                logger.warning(f"Error disposing scoped instance: {e}")


class Container:
    """
    Dependency Injection Container.

    Supports:
    - Singleton, Scoped, Transient lifetimes
    - Constructor injection
    - Factory methods
    - Instance registration
    - Decorator-based registration
    - Auto-wiring via type hints
    """

    def __init__(self, parent: Optional["Container"] = None):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._parent = parent
        self._scopes: List[Scope] = []
        self._current_scope: Optional[Scope] = None

    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[..., T]] = None,
        instance: Optional[T] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        tags: List[str] = None,
    ) -> "Container":
        """Register a service."""
        if sum(x is not None for x in [implementation, factory, instance]) > 1:
            raise ValueError("Only one of implementation, factory, or instance can be provided")

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            instance=instance,
            lifetime=lifetime,
            tags=tags or [],
        )
        self._services[service_type] = descriptor
        logger.debug(f"Registered {service_type.__name__} with {lifetime.value} lifetime")
        return self

    def register_singleton(self, service_type: Type[T], implementation: Type[T] = None) -> "Container":
        """Register as singleton."""
        return self.register(service_type, implementation, lifetime=ServiceLifetime.SINGLETON)

    def register_scoped(self, service_type: Type[T], implementation: Type[T] = None) -> "Container":
        """Register as scoped."""
        return self.register(service_type, implementation, lifetime=ServiceLifetime.SCOPED)

    def register_transient(self, service_type: Type[T], implementation: Type[T] = None) -> "Container":
        """Register as transient."""
        return self.register(service_type, implementation, lifetime=ServiceLifetime.TRANSIENT)

    def register_factory(self, service_type: Type[T], factory: Callable[..., T], lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> "Container":
        """Register a factory function."""
        return self.register(service_type, factory=factory, lifetime=lifetime)

    def register_instance(self, service_type: Type[T], instance: T) -> "Container":
        """Register a pre-created instance (always singleton)."""
        return self.register(service_type, instance=instance, lifetime=ServiceLifetime.SINGLETON)

    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service."""
        descriptor = self._get_descriptor(service_type)
        if not descriptor:
            if self._parent:
                return self._parent.resolve(service_type)
            raise KeyError(f"Service {service_type.__name__} not registered")

        if self._current_scope and descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._current_scope.get_or_create(descriptor)

        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._get_or_create_singleton(descriptor)

        return self._create_instance(descriptor)

    def try_resolve(self, service_type: Type[T]) -> Optional[T]:
        """Try to resolve a service, return None if not found."""
        try:
            return self.resolve(service_type)
        except KeyError:
            return None

    def resolve_all(self, service_type: Type[T]) -> List[T]:
        """Resolve all services matching a type (by tags)."""
        results = []
        for svc_type, descriptor in self._services.items():
            if issubclass(svc_type, service_type) or service_type in descriptor.tags:
                results.append(self.resolve(svc_type))
            elif descriptor.tags and service_type.__name__ in descriptor.tags:
                results.append(self.resolve(svc_type))
        if self._parent:
            results.extend(self._parent.resolve_all(service_type))
        return results

    def _get_descriptor(self, service_type: Type) -> Optional[ServiceDescriptor]:
        return self._services.get(service_type)

    def _get_or_create_singleton(self, descriptor: ServiceDescriptor) -> Any:
        if descriptor.service_type in self._singletons:
            return self._singletons[descriptor.service_type]

        instance = self._create_instance(descriptor)
        self._singletons[descriptor.service_type] = instance
        return instance

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        if descriptor.instance is not None:
            return descriptor.instance

        if descriptor.factory:
            return self._invoke_factory(descriptor.factory)

        impl = descriptor.implementation
        return self._auto_wire(impl)

    def _invoke_factory(self, factory: Callable) -> Any:
        sig = inspect.signature(factory)
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                kwargs[param_name] = self.resolve(param.annotation)
            elif param.default == inspect.Parameter.empty:
                raise ValueError(f"Factory parameter {param_name} missing type annotation")
        return factory(**kwargs)

    def _auto_wire(self, implementation: Type) -> Any:
        """Auto-wire constructor dependencies."""
        # Check __init__ signature
        init = implementation.__init__
        if init is object.__init__:
            return implementation()

        sig = inspect.signature(init)
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            if param.annotation != inspect.Parameter.empty:
                kwargs[param_name] = self.resolve(param.annotation)
            elif param.default == inspect.Parameter.empty:
                raise ValueError(f"Constructor parameter {param_name} missing type annotation")

        return implementation(**kwargs)

    @asynccontextmanager
    async def create_scope(self) -> Scope:
        """Create a new service scope."""
        scope = Scope(self, self._current_scope)
        self._scopes.append(scope)
        self._current_scope = scope
        try:
            yield scope
        finally:
            await scope.dispose()
            self._scopes.remove(scope)
            self._current_scope = scope.parent if scope.parent else None

    @property
    def current_scope(self) -> Optional[Scope]:
        return self._current_scope

    def create_child_container(self) -> "Container":
        """Create a child container that inherits registrations."""
        return Container(parent=self)

    def clear(self) -> None:
        """Clear all registrations and instances."""
        self._services.clear()
        self._singletons.clear()

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service is registered."""
        return service_type in self._services or (self._parent and self._parent.is_registered(service_type))


# Decorator-based registration
def injectable(lifetime: ServiceLifetime = ServiceLifetime.SINGLETON, tags: List[str] = None):
    """Decorator to mark a class as injectable."""
    def decorator(cls: Type[T]) -> Type[T]:
        cls._di_lifetime = lifetime
        cls._di_tags = tags or []
        return cls
    return decorator


def singleton(cls: Type[T]) -> Type[T]:
    """Decorator to mark a class as singleton (convenience)."""
    return injectable(ServiceLifetime.SINGLETON)(cls)


def transient(cls: Type[T]) -> Type[T]:
    """Decorator to mark a class as transient (convenience)."""
    return injectable(ServiceLifetime.TRANSIENT)(cls)


def scoped(cls: Type[T]) -> Type[T]:
    """Decorator to mark a class as scoped (convenience)."""
    return injectable(ServiceLifetime.SCOPED)(cls)


def inject(func: Callable) -> Callable:
    """Decorator to auto-inject function parameters from container."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        container = get_container()
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name not in kwargs and param.annotation != inspect.Parameter.empty:
                kwargs[param_name] = container.resolve(param.annotation)
        return func(*args, **kwargs)
    return wrapper


async def ainject(func: Callable) -> Callable:
    """Async version of inject decorator."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        container = get_container()
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name not in kwargs and param.annotation != inspect.Parameter.empty:
                kwargs[param_name] = container.resolve(param.annotation)
        return await func(*args, **kwargs)
    return wrapper


# Global container instance
_global_container: Optional[Container] = None


def get_container() -> Container:
    """Get the global container instance."""
    global _global_container
    if _global_container is None:
        _global_container = Container()
    return _global_container


def set_container(container: Container) -> None:
    """Set the global container instance."""
    global _global_container
    _global_container = container


def configure_container(configurator: Callable[[Container], None]) -> Container:
    """Configure and return a new container."""
    container = Container()
    configurator(container)
    return container


class ServiceProvider:
    """Service provider abstraction for frameworks."""

    def __init__(self, container: Container):
        self.container = container

    def get_service(self, service_type: Type[T]) -> T:
        return self.container.resolve(service_type)

    def get_services(self, service_type: Type[T]) -> List[T]:
        return self.container.resolve_all(service_type)

    def create_scope(self) -> Scope:
        return self.container.create_scope()

    @asynccontextmanager
    async def scoped_service_provider(self):
        async with self.container.create_scope() as scope:
            yield ServiceProvider(scope.container if hasattr(scope, 'container') else self.container)


# Module exports
__all__ = [
    "Container",
    "Scope",
    "ServiceDescriptor",
    "ServiceLifetime",
    "ServiceProvider",
    "injectable",
    "inject",
    "ainject",
    "get_container",
    "set_container",
    "configure_container",
    "singleton",
    "transient",
    "scoped",
]