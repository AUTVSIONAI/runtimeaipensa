import asyncio
from runtime.runtime import Runtime, create_runtime
from runtime.config import RuntimeConfig, RuntimeType
from runtime.plugins.local_plugins import LocalExecutionPlugin, LocalWorkflowPlugin

async def test():
    config = RuntimeConfig(runtime_type=RuntimeType.LOCAL)
    runtime = await create_runtime(config)
    try:
        # Initialize and start execution plugin first
        exec_plugin = LocalExecutionPlugin()
        await exec_plugin.initialize(runtime)
        await exec_plugin.start()

        # Initialize and start workflow plugin
        workflow_plugin = LocalWorkflowPlugin()
        await workflow_plugin.initialize(runtime)
        await workflow_plugin.start()

        print('Modules loaded:', list(runtime.modules.keys()))
        module = workflow_plugin._module
        print('Module:', module)
        if module:
            dag = {
                'name': 'Test Workflow',
                'description': 'Test workflow',
                'nodes': [
                    {'id': 'node-1', 'name': 'Task 1', 'type': 'task', 'action': 'shell', 'parameters': {'command': 'echo Hello from shell'}, 'depends_on': []},
                    {'id': 'node-2', 'name': 'Task 2', 'type': 'task', 'action': 'python', 'parameters': {'code': 'print("Hello from Python")'}, 'depends_on': ['node-1']}
                ],
                'edges': [{'source': 'node-1', 'target': 'node-2'}],
                'variables': {}
            }
            result = await module.create_workflow_from_dag(
                name=dag['name'],
                nodes=dag['nodes'],
                edges=dag['edges'],
                variables=dag['variables']
            )
            print('Workflow created:', result)
    finally:
        await runtime.stop()

asyncio.run(test())