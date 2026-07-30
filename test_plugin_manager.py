"""
Test script for Enhanced Plugin Manager

Tests:
1. Plugin discovery from filesystem
2. Manifest validation
3. Dependency resolution (topological sort)
4. Plugin loading
5. Hot-reload (dev mode only)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.plugins.manager import EnhancedPluginManager, TopologicalSorter
from runtime.plugins.schemas import load_manifest


class MockRuntime:
    """Mock runtime for testing."""
    def __init__(self):
        self._modules = {}
        self._module_registry = MockModuleRegistry()


class MockModuleRegistry:
    def set_instance(self, name, instance):
        pass


async def test_discovery():
    """Test plugin discovery from filesystem."""
    print("\n=== Test 1: Plugin Discovery ===")

    manager = EnhancedPluginManager(dev_mode=True, config={})
    summaries = await manager.discover_plugins()

    print(f"Discovered {len(summaries)} plugins:")
    for name, summary in summaries.items():
        print(f"  - {name} v{summary.version} ({summary.type.value}): {summary.status}")
        if summary.capabilities:
            print(f"    Capabilities: {', '.join(summary.capabilities)}")
        if summary.tags:
            print(f"    Tags: {', '.join(summary.tags)}")

    # Check specific plugins
    expected = ["nvidia_nim", "web_search", "example_skill"]
    for exp in expected:
        if exp in summaries:
            print(f"  OK Found expected plugin: {exp}")
        else:
            print(f"  MISSING Missing expected plugin: {exp}")

    return manager


async def test_manifest_validation(manager):
    """Test manifest validation."""
    print("\n=== Test 2: Manifest Validation ===")

    errors = await manager.validate_all_manifests()
    if errors:
        print("Validation errors found:")
        for name, errs in errors.items():
            print(f"  {name}: {errs}")
    else:
        print("  OK All manifests valid")

    # Test loading a specific manifest
    nvidia_manifest = manager._discovered.get("nvidia_nim")
    if nvidia_manifest:
        print(f"  NVIDIA NIM Manifest:")
        print(f"    Name: {nvidia_manifest.manifest.name}")
        print(f"    Version: {nvidia_manifest.manifest.version}")
        print(f"    Type: {nvidia_manifest.manifest.type.value}")
        print(f"    Class: {nvidia_manifest.manifest.class_name}")
        print(f"    Entry: {nvidia_manifest.manifest.entry_point}")
        print(f"    Dependencies: {[d.full_spec for d in nvidia_manifest.manifest.dependencies]}")
        print(f"    Capabilities: {nvidia_manifest.manifest.capabilities}")

    return errors


async def test_dependency_resolution(manager):
    """Test dependency resolution with topological sort."""
    print("\n=== Test 3: Dependency Resolution ===")

    try:
        load_order = await manager.resolve_dependencies()
        print(f"Load order ({len(load_order)} plugins):")
        for i, name in enumerate(load_order):
            plugin = manager._discovered[name]
            deps = [d.full_spec for d in plugin.manifest.dependencies]
            print(f"  {i+1}. {name} (deps: {deps if deps else 'none'})")
        return load_order
    except ValueError as e:
        print(f"  FAIL Dependency resolution failed: {e}")
        return []


async def test_plugin_loading(manager, load_order):
    """Test plugin loading."""
    print("\n=== Test 4: Plugin Loading ===")

    runtime = MockRuntime()
    manager.set_runtime(runtime)

    for name in load_order:
        try:
            plugin = await manager.load_plugin(name)
            if plugin:
                print(f"  OK Loaded: {name} -> {type(plugin).__name__}")
            else:
                print(f"  FAIL Failed to load: {name}")
        except Exception as e:
            print(f"  FAIL Error loading {name}: {e}")


async def test_hot_reload(manager):
    """Test hot-reload capability (if in dev mode)."""
    print("\n=== Test 5: Hot-Reload Capability ===")

    if not manager.dev_mode:
        print("  Skipped (not in dev mode)")
        return

    # Enable hot-reload watcher
    await manager.enable_hot_reload()
    print("  Hot-reload watcher enabled")

    # Test reload of a plugin
    try:
        success = await manager.reload_plugin("example_skill")
        if success:
            print("  OK Hot-reload successful for example_skill")
        else:
            print("  FAIL Hot-reload failed")
    except Exception as e:
        print(f"  FAIL Hot-reload error: {e}")

    # Disable watcher
    await manager.disable_hot_reload()
    print("  Hot-reload watcher disabled")


async def test_dependency_graph(manager):
    """Test dependency graph visualization."""
    print("\n=== Test 6: Dependency Graph ===")

    graph = manager.get_dependency_graph()
    for name, info in graph.items():
        print(f"  {name}:")
        print(f"    Status: {info['status']}")
        print(f"    Dependencies: {info['dependencies'] if info['dependencies'] else 'none'}")
        print(f"    Dependents: {info['dependents'] if info['dependents'] else 'none'}")


async def test_plugin_schemas():
    """Test plugin schema validation directly."""
    print("\n=== Test 7: Direct Schema Validation ===")

    # Test NVIDIA NIM manifest
    try:
        manifest = load_manifest(Path("runtime/plugins/llm/nvidia_nim/plugin.yaml"))
        print(f"  OK NVIDIA NIM manifest valid: {manifest.name} v{manifest.version}")
    except Exception as e:
        print(f"  FAIL NVIDIA NIM manifest invalid: {e}")

    # Test web_search manifest
    try:
        manifest = load_manifest(Path("runtime/plugins/tool/web_search/plugin.yaml"))
        print(f"  OK Web Search manifest valid: {manifest.name} v{manifest.version}")
    except Exception as e:
        print(f"  FAIL Web Search manifest invalid: {e}")

    # Test example_skill manifest
    try:
        manifest = load_manifest(Path("runtime/plugins/custom/example_skill/plugin.yaml"))
        print(f"  OK Example Skill manifest valid: {manifest.name} v{manifest.version}")
    except Exception as e:
        print(f"  FAIL Example Skill manifest invalid: {e}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("AIPENSA Plugin Manager - Test Suite")
    print("=" * 60)

    # Test schema validation directly
    await test_plugin_schemas()

    # Test discovery
    manager = await test_discovery()

    # Test manifest validation
    await test_manifest_validation(manager)

    # Test dependency resolution
    load_order = await test_dependency_resolution(manager)

    # Test plugin loading
    await test_plugin_loading(manager, load_order)

    # Test dependency graph
    await test_dependency_graph(manager)

    # Test hot-reload
    await test_hot_reload(manager)

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())