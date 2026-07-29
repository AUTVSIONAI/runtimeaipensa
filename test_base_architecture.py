#!/usr/bin/env python3
"""
Validation script for AIPENSA Runtime Base Architecture

Tests that all base classes can be imported and used correctly.
"""

import asyncio
import sys
import traceback


async def test_imports():
    """Test that all base modules can be imported."""
    print("Testing imports...")

    try:
        from runtime.base import (
            Runtime,
            RuntimeConfig,
            RuntimeStatus,
            RuntimeInfo,
            RuntimeModule,
            ModuleMetadata,
            ModuleState,
            RuntimePlugin,
            PluginMetadata,
            PluginStatus,
            PluginType,
            RuntimeFactory,
            ModuleFactory,
            PluginFactory,
            RuntimeEvent,
            RuntimeEventType,
            RuntimeEventBus,
            RuntimeContainer,
            ServiceLifetime,
            injectable,
            singleton,
            transient,
            scoped,
            RuntimeRegistry,
            ModuleRegistry,
            PluginRegistry,
        )
        print("  [OK] All imports successful")
        return True
    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        traceback.print_exc()
        return False


async def test_events():
    """Test event system functionality."""
    print("Testing Event Bus...")

    try:
        from runtime.base.events import RuntimeEventBus, RuntimeEvent, RuntimeEventType, create_event

        bus = RuntimeEventBus(max_history=100)
        await bus.start()

        # Test event creation
        event = create_event(
            RuntimeEventType.MODULE_STARTED,
            source="test_module",
            payload={"module_name": "test"}
        )
        print(f"  Created event: {event.event_type.value} from {event.source}")

        # Test publish
        await bus.publish(event)
        print(f"  Published event to bus")

        # Test history
        events = bus.get_recent_events(limit=10)
        print(f"  History size: {len(events)}")

        await bus.stop()
        print("  [OK] Event bus test passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Event bus test failed: {e}")
        traceback.print_exc()
        return False


async def test_module_base():
    """Test module base class."""
    print("Testing Module Base...")

    try:
        from runtime.base import RuntimeModule, ModuleMetadata, ModuleState
        from runtime.base.events import RuntimeEvent

        class TestModule(RuntimeModule):
            metadata = ModuleMetadata(
                name="test_module",
                version="1.0.0",
                description="Test module",
                module_type="test"
            )

            async def initialize(self, runtime, config):
                await super().initialize(runtime, config)
                self._initialized = True

            async def start(self):
                await super().start()
                self._started = True

            async def stop(self):
                await super().stop()
                self._started = False

            async def cleanup(self):
                await super().cleanup()
                self._initialized = False

            async def health_check(self):
                return {"healthy": True, "state": self.state.value}

        # Test module metadata
        print(f"  Module name: {TestModule.metadata.name}")
        print(f"  Module version: {TestModule.metadata.version}")
        print(f"  Module type: {TestModule.metadata.module_type}")

        # Test module state
        module = TestModule()
        print(f"  Initial state: {module.state.value}")

        print("  [OK] Module base test passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Module base test failed: {e}")
        traceback.print_exc()
        return False


async def test_plugin_base():
    """Test plugin base class."""
    print("Testing Plugin Base...")

    try:
        from runtime.base import RuntimePlugin, PluginMetadata, PluginStatus, PluginType

        class TestPlugin(RuntimePlugin):
            metadata = PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                description="Test plugin",
                plugin_type=PluginType.CUSTOM
            )

            async def initialize(self, runtime, config):
                await super().initialize(runtime, config)

            async def start(self):
                await super().start()

            async def stop(self):
                await super().stop()

            async def cleanup(self):
                await super().cleanup()

            async def health_check(self):
                return {"healthy": self.status == PluginStatus.RUNNING}

        # Test plugin metadata
        print(f"  Plugin name: {TestPlugin.metadata.name}")
        print(f"  Plugin type: {TestPlugin.metadata.plugin_type}")

        plugin = TestPlugin()
        print(f"  Initial status: {plugin.status.value}")
        print(f"  Plugin ID: {plugin.plugin_id}")

        print("  [OK] Plugin base test passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Plugin base test failed: {e}")
        traceback.print_exc()
        return False


async def test_registry():
    """Test registry functionality."""
    print("Testing Registry...")

    try:
        from runtime.base import ModuleRegistry, PluginRegistry, ModuleMetadata, PluginMetadata, PluginType
        from runtime.base.module import get_module_registry
        from runtime.base.plugin import get_plugin_registry

        # Test module registry
        module_registry = ModuleRegistry()

        class TestModuleForRegistry:
            metadata = ModuleMetadata(name="reg_test", version="1.0.0")

        module_registry.register(TestModuleForRegistry)
        assert "reg_test" in module_registry.list_modules()
        print(f"  Module registry: {module_registry.list_modules()}")

        # Test plugin registry
        plugin_registry = PluginRegistry()

        class TestPluginForRegistry:
            metadata = PluginMetadata(name="reg_plugin", version="1.0.0", plugin_type=PluginType.CUSTOM)

        plugin_registry.register(TestPluginForRegistry)
        assert "reg_plugin" in plugin_registry.list_plugins()
        print(f"  Plugin registry: {plugin_registry.list_plugins()}")

        # Test global registries
        global_module_registry = get_module_registry()
        global_plugin_registry = get_plugin_registry()
        print(f"  Global registries accessible")

        print("  [OK] Registry test passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Registry test failed: {e}")
        traceback.print_exc()
        return False


async def test_di():
    """Test Dependency Injection container."""
    print("Testing DI Container...")

    try:
        from runtime.base import RuntimeContainer, ServiceLifetime, singleton, transient, scoped

        container = RuntimeContainer()

        # Test service registration and resolution
        class TestService:
            def __init__(self):
                self.value = "test"

        container.register(TestService, implementation=TestService, lifetime=ServiceLifetime.SINGLETON)
        service1 = container.resolve(TestService)
        service2 = container.resolve(TestService)

        assert service1 is service2, "Singleton should return same instance"
        print(f"  Singleton: same instance = {service1 is service2}")

        container.register(TestService, implementation=TestService, lifetime=ServiceLifetime.TRANSIENT)
        service3 = container.resolve(TestService)
        service4 = container.resolve(TestService)

        assert service3 is not service4, "Transient should return new instances"
        print(f"  Transient: different instances = {service3 is not service4}")

        # Test instance registration
        container.register_instance(TestService, service1)
        resolved = container.resolve(TestService)
        assert resolved is service1
        print(f"  Instance registration works")

        print("  [OK] DI Container test passed")
        return True
    except Exception as e:
        print(f"  [FAIL] DI Container test failed: {e}")
        traceback.print_exc()
        return False


async def test_factory():
    """Test factory base classes."""
    print("Testing Factory Patterns...")

    try:
        from runtime.base import ModuleFactory, PluginFactory
        from runtime.base.module import RuntimeModule, ModuleMetadata
        from runtime.base.plugin import RuntimePlugin, PluginMetadata, PluginType
        from runtime.base.factory import FactoryConfig

        # Test ModuleFactory
        class TestModuleFactory(ModuleFactory):
            @property
            def module_type(self):
                return "test"

            async def create(self, module_name, config, runtime):
                class TestModule(RuntimeModule):
                    metadata = ModuleMetadata(name=module_name, module_type="test")
                return TestModule(config)

            def get_available_modules(self):
                return ["test_module"]

        factory = TestModuleFactory()
        assert factory.module_type == "test"
        assert "test_module" in factory.get_available_modules()
        print(f"  Module factory type: {factory.module_type}")

        # Test PluginFactory
        class TestPluginFactory(PluginFactory):
            @property
            def plugin_type(self):
                return "test"

            async def create(self, plugin_name, config, runtime):
                class TestPlugin(RuntimePlugin):
                    metadata = PluginMetadata(name=plugin_name, plugin_type=PluginType.CUSTOM)
                return TestPlugin(config)

            def get_available_plugins(self):
                return ["test_plugin"]

        plugin_factory = TestPluginFactory()
        assert plugin_factory.plugin_type == "test"
        assert "test_plugin" in plugin_factory.get_available_plugins()
        print(f"  Plugin factory type: {plugin_factory.plugin_type}")

        print("  [OK] Factory test passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Factory test failed: {e}")
        traceback.print_exc()
        return False


async def test_runtime_config():
    """Test runtime configuration."""
    print("Testing Runtime Config...")

    try:
        from runtime.base import RuntimeConfig, RuntimeStatus

        config = RuntimeConfig(
            runtime_id="test-123",
            name="test-runtime",
            runtime_type="test",
            version="1.0.0",
            max_concurrent_tasks=50,
            features={"feature1": True, "feature2": False}
        )

        print(f"  Runtime ID: {config.runtime_id}")
        print(f"  Name: {config.name}")
        print(f"  Type: {config.runtime_type}")
        print(f"  Max tasks: {config.max_concurrent_tasks}")
        print(f"  Features: {config.features}")

        # Test auto-generated IDs
        config2 = RuntimeConfig()
        print(f"  Auto ID: {config2.runtime_id}")
        print(f"  Auto name: {config2.name}")

        assert config.runtime_id == "test-123"
        assert config2.runtime_id != ""
        print("  [OK] Runtime Config test passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Runtime Config test failed: {e}")
        traceback.print_exc()
        return False


async def test_event_handler_decorator():
    """Test event handler decorator."""
    print("Testing Event Handler Decorator...")

    try:
        from runtime.base import RuntimeEventType, RuntimeEvent
        from runtime.base.events import event_handler

        handler_called = []

        @event_handler(RuntimeEventType.MODULE_STARTED, RuntimeEventType.MODULE_STOPPED, priority=10)
        async def my_handler(event: RuntimeEvent):
            handler_called.append(event.event_type)

        assert handler_called == []
        assert len(my_handler.handles_event_types) == 2
        assert my_handler.priority == 10
        print(f"  Handler handles: {[e.value for e in my_handler.handles_event_types]}")
        print(f"  Handler priority: {my_handler.priority}")

        # Test calling handler
        event = RuntimeEvent(event_type=RuntimeEventType.MODULE_STARTED, source="test")
        await my_handler.handle(event)
        assert len(handler_called) == 1
        print(f"  Handler executed: {handler_called[0].value}")

        print("  [OK] Event Handler Decorator test passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Event Handler Decorator test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    tests = [
        ("Imports", test_imports),
        ("Event System", test_events),
        ("Module Base", test_module_base),
        ("Plugin Base", test_plugin_base),
        ("Registry", test_registry),
        ("DI Container", test_di),
        ("Factories", test_factory),
        ("Runtime Config", test_runtime_config),
        ("Event Handler Decorator", test_event_handler_decorator),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print(f"{'='*60}")
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  [FAIL] {name} crashed: {e}")
            traceback.print_exc()
            results.append((name, False))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\nAll tests passed! Base architecture is working correctly.")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)