"""
AIPENSA Runtime Base - Dependency Injection Container

Provides a lightweight DI container with support for different
service lifetimes (singleton, scoped, transient) and decorators.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, get_type_hints
import asyncio
import inspect
import logging
from contextlib import asynccontextmanager
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime scopes."""

    SINGLETON = "singleton"      # Single instance for container lifetime
    SCOPED = "scoped"            # Single instance per scope/request
    TRANSIENT = "transient"      # New instance every time


@dataclass
class ServiceDescriptor:
    """Describes a registered service."""

    service_type: Type
    implementation: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    dependencies: List[Type] = field(default_factory=list)


class RuntimeContainer:
    """
    Lightweight dependency injection container.

    Supports:
    - Singleton, Scoped, Transient lifetimes
    - Constructor injection
    - Factory functions
    - Instance registration
    - Async initialization
    - Scoped containers for request lifetime
    """

    def __init__(self, parent: Optional["RuntimeContainer"] = None):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._parent = parent
        self._initialized: Dict[Type, bool] = {}

    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Type] = None,
        factory: Optional[Callable[..., T]] = None,
        instance: Optional[T] = None,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    ) -> "RuntimeContainer":
        """
        Register a service.

        Args:
            service_type: Interface/abstract type to register
            implementation: Concrete implementation class
            factory: Factory function to create instances
            instance: Pre-created instance (singleton only)
            lifetime: Service lifetime scope

        Returns:
            Self for chaining
        """
        if implementation and factory:
            raise ValueError("Cannot specify both implementation and factory")
        if implementation and instance:
            raise ValueError("Cannot specify both implementation and instance")
        if factory and instance:
            raise ValueError("Cannot specify both factory and instance")

        # Auto-detect dependencies from constructor
        deps = []
        if implementation:
            deps = self._get_constructor_dependencies(implementation)
        elif factory:
            deps = self._get_factory_dependencies(factory)

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            instance=instance,
            lifetime=lifetime,
            dependencies=deps,
        )

        self._services[service_type] = descriptor

        # If instance provided, store as singleton
        if instance is not None:
            self._singletons[service_type] = instance

        logger.debug(f"Registered service: {service_type.__name__} ({lifetime.value})")
        return self

    def register_instance(self, service_type: Type[T], instance: T) -> "RuntimeContainer":
        """Register a pre-created instance as singleton."""
        return self.register(service_type, instance=instance, lifetime=ServiceLifetime.SINGLETON)

    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type] = None,
        factory: Optional[Callable[..., T]] = None
    ) -> "RuntimeContainer":
        """Register a singleton service."""
        return self.register(service_type, implementation, factory, lifetime=ServiceLifetime.SINGLETON)

    def register_scoped(
        self,
        service_type: Type[T],
        implementation: Optional[Type] = None,
        factory: Optional[Callable[..., T]] = None
    ) -> "RuntimeContainer":
        """Register a scoped service."""
        return self.register(service_type, implementation, factory, lifetime=ServiceLifetime.SCOPED)

    def register_transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type] = None,
        factory: Optional[Callable[..., T]] = None
    ) -> "RuntimeContainer":
        """Register a transient service."""
        return self.register(service_type, implementation, factory, lifetime=ServiceLifetime.TRANSIENT)

    def _get_constructor_dependencies(self, cls: Type) -> List[Type]:
        """Extract constructor dependencies from type hints."""
        try:
            hints = get_type_hints(cls.__init__)
            deps = []
            for param_name, param_type in hints.items():
                if param_name != 'return' and param_name != 'self':
                    deps.append(param_type)
            return deps
        except Exception:
            return []

    def _get_factory_dependencies(self, factory: Callable) -> List[Type]:
        """Extract dependencies from factory function signature."""
        try:
            sig = inspect.signature(factory)
            hints = get_type_hints(factory)
            deps = []
            for param_name, param in sig.parameters.items():
                if param_name in hints:
                    deps.append(hints[param_name])
            return deps
        except Exception:
            return []

    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service instance.

        Args:
            service_type: Type to resolve

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        descriptor = self._get_descriptor(service_type)
        if not descriptor:
            if self._parent:
                return self._parent.resolve(service_type)
            raise KeyError(f"Service not registered: {service_type.__name__}")

        # Handle different lifetimes
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._resolve_singleton(descriptor)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._resolve_scoped(descriptor)
        else:
            return self._resolve_transient(descriptor)

    def resolve_optional(self, service_type: Type[T]) -> Optional[T]:
        """Resolve a service, return None if not found."""
        try:
            return self.resolve(service_type)
        except KeyError:
            return None

    def _get_descriptor(self, service_type: Type) -> Optional[ServiceDescriptor]:
        """Get service descriptor, checking parent if not found locally."""
        if service_type in self._services:
            return self._services[service_type]
        if self._parent:
            return self._parent._get_descriptor(service_type)
        return None

    def _resolve_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve singleton instance."""
        if descriptor.service_type in self._singletons:
            return self._singletons[descriptor.service_type]

        instance = self._create_instance(descriptor)
        self._singletons[descriptor.service_type] = instance
        return instance

    def _resolve_scoped(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve scoped instance."""
        if descriptor.service_type in self._scoped_instances:
            return self._scoped_instances[descriptor.service_type]

        instance = self._create_instance(descriptor)
        self._scoped_instances[descriptor.service_type] = instance
        return instance

    def _resolve_transient(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve transient instance (new every time)."""
        return self._create_instance(descriptor)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create instance based on descriptor configuration."""
        # Use provided instance
        if descriptor.instance is not None:
            return descriptor.instance

        # Use factory function
        if descriptor.factory:
            # Resolve factory dependencies
            kwargs = {}
            for dep in descriptor.dependencies:
                kwargs[dep.__name__] = self.resolve(dep)
            return descriptor.factory(**kwargs)

        # Use implementation class
        if descriptor.implementation:
            # Resolve constructor dependencies
            kwargs = {}
            for dep in descriptor.dependencies:
                kwargs[dep.__name__] = self.resolve(dep)
            return descriptor.implementation(**kwargs)

        # Last resort: try to instantiate service_type directly
        if not inspect.isabstract(descriptor.service_type):
            kwargs = {}
            for dep in descriptor.dependencies:
                kwargs[dep.__name__] = self.resolve(dep)
            return descriptor.service_type(**kwargs)

        raise ValueError(f"Cannot create instance for {descriptor.service_type.__name__}")

    def create_scope(self) -> "RuntimeContainer":
        """Create a new scoped child container."""
        scope = RuntimeContainer(parent=self)
        # Share singletons with parent
        scope._singletons = self._singletons
        return scope

    @asynccontextmanager
    async def scope(self):
        """Async context manager for scoped lifetime."""
        scope = self.create_scope()
        try:
            yield scope
        finally:
            # Cleanup scoped instances with async cleanup if needed
            for instance in scope._scoped_instances.values():
                if hasattr(instance, 'cleanup') and callable(instance.cleanup):
                    if asyncio.iscoroutinefunction(instance.cleanup):
                        await instance.cleanup()
                    else:
                        instance.cleanup()

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service is registered."""
        return self._get_descriptor(service_type) is not None

    def get_registrations(self) -> List[ServiceDescriptor]:
        """Get all registered service descriptors."""
        return list(self._services.values())

    def clear(self) -> None:
        """Clear all registrations (use with caution)."""
        self._services.clear()
        self._singletons.clear()
        self._scoped_instances.clear()


# Decorators for declarative registration
def injectable(
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    service_type: Optional[Type] = None
):
    """
    Decorator to mark a class as injectable.

    Usage:
        @injectable(ServiceLifetime.SINGLETON)
        class MyService:
            pass
    """
    def decorator(cls: Type) -> Type:
        cls._di_lifetime = lifetime
        cls._di_service_type = service_type or cls
        return cls
    return decorator


def singleton(service_type: Optional[Type] = None):
    """Decorator to register as singleton."""
    return injectable(ServiceLifetime.SINGLETON, service_type)


def transient(service_type: Optional[Type] = None):
    """Decorator to register as transient."""
    return injectable(ServiceLifetime.TRANSIENT, service_type)


def scoped(service_type: Optional[Type] = None):
    """Decorator to register as scoped."""
    return injectable(ServiceLifetime.SCOPED, service_type)


def inject(container: Optional[RuntimeContainer] = None):
    """
    Decorator for property/field injection.

    Usage:
        class MyClass:
            @inject
            def __init__(self, service: MyService):
                self.service = service
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get container from args/kwargs or use provided
            nonlocal container
            if container is None:
                # Try to find container in args
                for arg in args:
                    if isinstance(arg, RuntimeContainer):
                        container = arg
                        break
                if container is None:
                    for v in kwargs.values():
                        if isinstance(v, RuntimeContainer):
                            container = v
                            break

            if container is None:
                raise RuntimeError("No DI container available for injection")

            # Resolve dependencies from signature
            sig = inspect.signature(func)
            hints = get_type_hints(func)
            for param_name, param in sig.parameters.items():
                if param_name in kwargs:
                    continue
                if param_name in hints:
                    dep_type = hints[param_name]
                    if param.default == inspect.Parameter.empty:
                        kwargs[param_name] = container.resolve(dep_type)

            return func(*args, **kwargs)
        return wrapper
    return decorator


async def ainject(container: Optional[RuntimeContainer] = None):
    """Async version of inject decorator."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal container
            if container is None:
                for arg in args:
                    if isinstance(arg, RuntimeContainer):
                        container = arg
                        break
                if container is None:
                    for v in kwargs.values():
                        if isinstance(v, RuntimeContainer):
                            container = v
                            break

            if container is None:
                raise RuntimeError("No DI container available for injection")

            sig = inspect.signature(func)
            hints = get_type_hints(func)
            for param_name, param in sig.parameters.items():
                if param_name in kwargs:
                    continue
                if param_name in hints:
                    dep_type = hints[param_name]
                    if param.default == inspect.Parameter.empty:
                        kwargs[param_name] = container.resolve(dep_type)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Global container instance
_global_container: Optional[RuntimeContainer] = None


def get_container() -> RuntimeContainer:
    """Get global container."""
    global _global_container
    if _global_container is None:
        _global_container = RuntimeContainer()
    return _global_container


def set_container(container: RuntimeContainer) -> None:
    """Set global container."""
    global _global_container
    _global_container = container