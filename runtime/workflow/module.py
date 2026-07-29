"""
Workflow Runtime Module

Provides workflow orchestration with DAG execution, step dependencies,
workflow state management, and visual workflow definitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import asyncio
import json
import logging
import uuid
from collections import defaultdict

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Workflow step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


class StepType(Enum):
    """Types of workflow steps."""
    TASK = "task"           # Execute a task/tool
    CONDITION = "condition" # Conditional branch
    PARALLEL = "parallel"   # Parallel execution
    LOOP = "loop"           # Loop iteration
    WAIT = "wait"           # Wait for external signal
    START = "start"         # Workflow entry point
    END = "end"             # Workflow exit point


@dataclass
class WorkflowStep:
    """Workflow step definition."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    step_type: StepType = StepType.TASK
    action: str = ""  # Tool name, function, or condition expression
    parameters: Dict[str, Any] = field(default_factory=dict)
    agent_type: str = "default"
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on
    condition: Optional[str] = None  # For conditional steps
    loop_config: Optional[Dict[str, Any]] = None  # For loop steps
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_seconds: int = 300
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_execute(self, completed_steps: Set[str]) -> bool:
        """Check if step can execute (all dependencies met)."""
        return all(dep in completed_steps for dep in self.depends_on)


@dataclass
class Workflow:
    """Workflow definition and state."""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: List[WorkflowStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    completed_steps: Set[str] = field(default_factory=set)
    failed_steps: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_runnable_steps(self) -> List[WorkflowStep]:
        """Get steps that can execute now."""
        return [s for s in self.steps if s.status == StepStatus.PENDING and s.can_execute(self.completed_steps)]

    def get_next_steps(self) -> List[WorkflowStep]:
        """Get next steps to execute (runnable + conditional based on results)."""
        runnable = self.get_runnable_steps()
        next_steps = []

        for step in runnable:
            if step.step_type == StepType.CONDITION and step.condition:
                # Evaluate condition based on variables/results
                pass  # Will be evaluated at runtime
            next_steps.append(step)

        return next_steps


@dataclass
class WorkflowExecution:
    """Workflow execution context."""
    workflow_id: str
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    workflow: Workflow = field(default_factory=Workflow)
    variables: Dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    event_log: List[Dict[str, Any]] = field(default_factory=list)


class WorkflowExecutor:
    """Executes workflow steps."""

    def __init__(self, module: "WorkflowModule"):
        self._module = module
        self._running_executions: Dict[str, WorkflowExecution] = {}

    async def execute_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Any:
        """Execute a single workflow step."""
        execution.workflow.current_step = step.step_id
        step.status = StepStatus.RUNNING
        step.started_at = datetime.utcnow()
        self._log_event(execution, "step_started", {"step_id": step.step_id, "name": step.name})

        try:
            result = None

            if step.step_type == StepType.TASK:
                result = await self._execute_task_step(execution, step)
            elif step.step_type == StepType.CONDITION:
                result = await self._execute_condition_step(execution, step)
            elif step.step_type == StepType.PARALLEL:
                result = await self._execute_parallel_step(execution, step)
            elif step.step_type == StepType.LOOP:
                result = await self._execute_loop_step(execution, step)
            elif step.step_type == StepType.WAIT:
                result = await self._execute_wait_step(execution, step)
            elif step.step_type == StepType.START:
                # START step is a no-op - marks workflow start
                result = {"status": "started", "step_id": step.step_id}
            elif step.step_type == StepType.END:
                # END step is a no-op - marks workflow end
                result = {"status": "completed", "step_id": step.step_id}

            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            execution.workflow.completed_steps.add(step.step_id)
            execution.step_results[step.step_id] = result
            execution.workflow.variables[f"step_{step.step_id}_result"] = result

            self._log_event(execution, "step_completed", {
                "step_id": step.step_id,
                "name": step.name,
                "duration_ms": (step.completed_at - step.started_at).total_seconds() * 1000 if step.started_at else 0
            })

            return result

        except Exception as e:
            step.error = str(e)
            step.retry_count += 1

            if step.retry_count >= step.max_retries:
                step.status = StepStatus.FAILED
                step.completed_at = datetime.utcnow()
                execution.workflow.failed_steps.add(step.step_id)
                self._log_event(execution, "step_failed", {
                    "step_id": step.step_id,
                    "name": step.name,
                    "error": str(e),
                    "retries": step.retry_count
                })
                raise
            else:
                step.status = StepStatus.PENDING
                self._log_event(execution, "step_retry", {
                    "step_id": step.step_id,
                    "attempt": step.retry_count,
                    "max_retries": step.max_retries
                })
                await asyncio.sleep(step.retry_delay)
                return await self.execute_step(execution, step)

    async def _execute_task_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Any:
        """Execute a task step (tool/function call)."""
        # Check if it's a tool
        if step.action.startswith("tool:"):
            tool_name = step.action[5:]
            tools_module = self._module._runtime.modules.get("tool")
            if tools_module:
                return await tools_module.execute_tool(tool_name, step.parameters)
            raise ValueError(f"Tool module not available: {tool_name}")

        # Check if it's a Python execution
        elif step.action == "python":
            execution_module = self._module._runtime.modules.get("execution") or self._module._runtime.modules.get("local-execution")
            if execution_module:
                return await execution_module.execute_python(
                    step.parameters.get("code", ""),
                    timeout_seconds=step.timeout_seconds
                )
            raise ValueError("Execution module not available")

        # Check if it's a shell command
        elif step.action == "shell":
            execution_module = self._module._runtime.modules.get("execution") or self._module._runtime.modules.get("local-execution")
            if execution_module:
                return await execution_module.execute_shell(
                    step.parameters.get("command", ""),
                    timeout_seconds=step.timeout_seconds
                )
            raise ValueError("Execution module not available")

        # Check if it's an agent action
        elif step.action.startswith("agent:"):
            agent_type = step.action[6:]
            agent = self._module._runtime.modules.get("agent")
            if agent:
                return await agent.execute(f"agent_{agent_type}", step.parameters)
            raise ValueError(f"Agent module not available: {agent_type}")

        # Default: invoke as function on runtime
        runtime = self._module._runtime
        if hasattr(runtime, step.action):
            func = getattr(runtime, step.action)
            if callable(func):
                return await func(**step.parameters)

        # Try to find in modules
        for mod_name, mod in self._module._runtime.modules.items():
            if hasattr(mod, step.action):
                func = getattr(mod, step.action)
                if callable(func):
                    return await func(**step.parameters)

        raise ValueError(f"Unknown action: {step.action}")

    async def _execute_condition_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Any:
        """Execute a conditional step."""
        condition = step.condition
        if not condition:
            return {"branch": "default", "result": True}

        # Simple evaluation - in production use a safe expression evaluator
        try:
            # Replace variables in condition
            evaluated = condition
            for key, value in execution.variables.items():
                evaluated = evaluated.replace(f"${key}", str(value))

            # Evaluate
            result = eval(evaluated, {"__builtins__": {}}, execution.variables)
            return {"branch": "true" if result else "false", "result": bool(result)}
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return {"branch": "error", "result": False, "error": str(e)}

    async def _execute_parallel_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Any:
        """Execute parallel steps."""
        branches = step.parameters.get("branches", [])
        if not branches:
            return {"results": []}

        tasks = []
        for branch in branches:
            # Create sub-steps for parallel execution
            sub_task = self._execute_parallel_branch(execution, step, branch)
            tasks.append(sub_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {"results": results}

    async def _execute_parallel_branch(
        self,
        execution: WorkflowExecution,
        step: WorkflowStep,
        branch: Dict[str, Any]
    ) -> Any:
        """Execute a single parallel branch."""
        # This would execute a sub-workflow or set of steps
        # For simplicity, execute as a single action
        action = branch.get("action", "")
        params = branch.get("parameters", {})
        if action.startswith("tool:"):
            tool_name = action[5:]
            tools_module = self._module._runtime.modules.get("tool")
            if tools_module:
                return await tools_module.execute_tool(tool_name, params)
        return {"branch": branch.get("name", "unknown"), "executed": True}

    async def _execute_loop_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Any:
        """Execute a loop step."""
        loop_config = step.loop_config or {}
        iterable = loop_config.get("iterable", [])
        max_iterations = loop_config.get("max_iterations", 100)

        if isinstance(iterable, str) and iterable.startswith("$"):
            # Variable reference
            iterable = execution.variables.get(iterable[1:], [])

        if not isinstance(iterable, (list, tuple)):
            iterable = [iterable]

        results = []
        for i, item in enumerate(iterable[:max_iterations]):
            execution.variables["loop_item"] = item
            execution.variables["loop_index"] = i

            # Execute loop body steps
            body_steps = loop_config.get("steps", [])
            for body_step_data in body_steps:
                body_step = WorkflowStep(**body_step_data)
                body_step.step_id = f"{step.step_id}_iter_{i}_{body_step.step_id}"
                await self.execute_step(execution, body_step)

            results.append({"item": item, "index": i})

        return {"iterations": len(results), "results": results}

    async def _execute_wait_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Any:
        """Execute a wait step."""
        wait_for = step.parameters.get("event", "")
        timeout = step.parameters.get("timeout", 300)

        if not wait_for:
            await asyncio.sleep(step.parameters.get("duration", 1))
            return {"waited": True}

        # Wait for external signal (would integrate with queue module)
        # For now, just wait with timeout
        try:
            await asyncio.wait_for(
                self._module._wait_for_signal(execution.workflow_id, wait_for),
                timeout=timeout
            )
            return {"signal_received": True}
        except asyncio.TimeoutError:
            return {"signal_received": False, "timeout": True}

    def _log_event(self, execution: WorkflowExecution, event: str, data: Dict[str, Any]) -> None:
        """Log workflow event."""
        execution.event_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "workflow_id": execution.workflow_id,
            "execution_id": execution.execution_id,
            **data
        })


class WorkflowModule(RuntimeModule):
    """
    Workflow orchestration module.

    Provides DAG-based workflow execution with dependencies, parallel execution,
    conditional branching, loops, and state management.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="workflow",
            version="1.0.0",
            description="Workflow orchestration with DAG execution",
            author="AIPENSA",
            dependencies=["tool", "execution", "agent", "queue"],
            provides=["workflow_orchestration", "dag_execution", "workflow_management"],
            tags={"workflow", "orchestration", "dag", "automation"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._workflows: Dict[str, Workflow] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._executor = WorkflowExecutor(self)
        self._max_workflows = config.get("max_workflows", 1000) if config else 1000
        self._max_executions = config.get("max_executions", 10000) if config else 10000
        self._signal_waiters: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize workflow module."""
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._max_workflows = self._config.get("max_workflows", self._max_workflows)
        self._max_executions = self._config.get("max_executions", self._max_executions)

        # Load workflows if persistence configured
        persist_path = self._config.get("persist_path")
        if persist_path:
            await self._load_workflows(persist_path)

        self.state = ModuleState.INITIALIZED
        logger.info(f"Workflow module initialized with {len(self._workflows)} workflows")

    async def start(self) -> None:
        """Start workflow module."""
        self.state = ModuleState.RUNNING
        logger.info("Workflow module started")

    async def stop(self) -> None:
        """Stop workflow module."""
        # Cancel running executions
        for exec_id in list(self._executions.keys()):
            await self.cancel_execution(exec_id)

        self.state = ModuleState.STOPPED
        logger.info("Workflow module stopped")

    async def cleanup(self) -> None:
        """Clean up resources."""
        persist_path = self._config.get("persist_path")
        if persist_path:
            await self._save_workflows(persist_path)

        self._workflows.clear()
        self._executions.clear()
        self._signal_waiters.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("Workflow module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        active_executions = len([e for e in self._executions.values() if e.status == WorkflowStatus.ACTIVE])
        return {
            "module": "workflow",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "total_workflows": len(self._workflows),
            "total_executions": len(self._executions),
            "active_executions": active_executions,
        }

    async def _wait_for_signal(self, workflow_id: str, signal: str) -> None:
        """Wait for a signal from external source."""
        waiter_key = f"{workflow_id}:{signal}"
        if waiter_key not in self._signal_waiters:
            self._signal_waiters[waiter_key] = asyncio.Queue()
        await self._signal_waiters[waiter_key].get()

    def signal(self, workflow_id: str, signal: str, data: Any = None) -> int:
        """Send signal to waiting workflows."""
        waiter_key = f"{workflow_id}:{signal}"
        count = 0
        if waiter_key in self._signal_waiters:
            # Signal all waiters
            queue = self._signal_waiters[waiter_key]
            while not queue.empty():
                try:
                    queue.get_nowait()
                    queue.put_nowait(data or True)
                    count += 1
                except asyncio.QueueEmpty:
                    break
        return count

    # Workflow Management
    async def create_workflow(self, workflow: Workflow) -> Workflow:
        """Create a new workflow definition."""
        if len(self._workflows) >= self._max_workflows:
            raise RuntimeError(f"Maximum workflows ({self._max_workflows}) reached")

        if not workflow.workflow_id:
            workflow.workflow_id = str(uuid.uuid4())[:8]

        self._workflows[workflow.workflow_id] = workflow
        workflow.updated_at = datetime.utcnow()
        logger.info(f"Created workflow: {workflow.workflow_id} - {workflow.name}")
        return workflow

    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)

    async def update_workflow(self, workflow: Workflow) -> Workflow:
        """Update workflow definition."""
        if workflow.workflow_id in self._workflows:
            workflow.updated_at = datetime.utcnow()
            self._workflows[workflow.workflow_id] = workflow
        return workflow

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False

    async def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Workflow]:
        """List workflows."""
        workflows = list(self._workflows.values())

        if status:
            workflows = [w for w in workflows if w.status == status]

        workflows.sort(key=lambda w: w.updated_at, reverse=True)
        return workflows[offset:offset + limit]

    # Workflow Execution
    async def execute_workflow(
        self,
        workflow_id: str,
        variables: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> WorkflowExecution:
        """Execute a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        if len(self._executions) >= self._max_executions:
            raise RuntimeError(f"Maximum executions ({self._max_executions}) reached")

        # Create execution context
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            execution_id=execution_id or str(uuid.uuid4())[:8],
            workflow=workflow,
            variables={**workflow.variables, **(variables or {})}
        )

        workflow.status = WorkflowStatus.ACTIVE
        workflow.started_at = datetime.utcnow()
        execution.workflow.status = WorkflowStatus.ACTIVE
        execution.workflow.started_at = datetime.utcnow()

        self._executions[execution.execution_id] = execution

        # Execute asynchronously
        asyncio.create_task(self._run_execution(execution))

        logger.info(f"Started workflow execution: {execution.execution_id} for workflow {workflow_id}")
        return execution

    async def _run_execution(self, execution: WorkflowExecution) -> None:
        """Run workflow execution."""
        try:
            while True:
                # Get runnable steps
                runnable = execution.workflow.get_runnable_steps()

                if not runnable:
                    # Check if workflow is complete
                    pending_steps = [s for s in execution.workflow.steps if s.status == StepStatus.PENDING]
                    if not pending_steps:
                        break  # All steps processed

                    # Check for failed steps
                    failed_steps = [s for s in execution.workflow.steps if s.status == StepStatus.FAILED]
                    if failed_steps:
                        execution.status = WorkflowStatus.FAILED
                        execution.error = f"Steps failed: {[s.step_id for s in failed_steps]}"
                        break

                    # No runnable steps but pending exist - might be waiting
                    waiting_steps = [s for s in execution.workflow.steps if s.status == StepStatus.WAITING]
                    if not waiting_steps:
                        break

                    # Small delay before checking again
                    await asyncio.sleep(0.1)
                    continue

                # Execute runnable steps
                if len(runnable) == 1:
                    await self._executor.execute_step(execution, runnable[0])
                else:
                    # Execute in parallel
                    tasks = [self._executor.execute_step(execution, step) for step in runnable]
                    await asyncio.gather(*tasks, return_exceptions=True)

            # Finalize
            if execution.status == WorkflowStatus.ACTIVE:
                if execution.workflow.failed_steps:
                    execution.status = WorkflowStatus.FAILED
                else:
                    execution.status = WorkflowStatus.COMPLETED

            execution.completed_at = datetime.utcnow()
            execution.workflow.completed_at = execution.completed_at
            execution.workflow.status = execution.status

            logger.info(f"Workflow execution completed: {execution.execution_id} - {execution.status.value}")

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            logger.error(f"Workflow execution failed: {execution.execution_id} - {e}")

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        if execution.status in (WorkflowStatus.ACTIVE, WorkflowStatus.PAUSED):
            execution.status = WorkflowStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            execution.workflow.status = WorkflowStatus.CANCELLED
            execution.workflow.completed_at = execution.completed_at
            logger.info(f"Cancelled workflow execution: {execution_id}")
            return True

        return False

    async def pause_execution(self, execution_id: str) -> bool:
        """Pause a running execution."""
        execution = self._executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.ACTIVE:
            execution.status = WorkflowStatus.PAUSED
            execution.workflow.status = WorkflowStatus.PAUSED
            return True
        return False

    async def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution."""
        execution = self._executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.ACTIVE
            execution.workflow.status = WorkflowStatus.ACTIVE
            asyncio.create_task(self._run_execution(execution))
            return True
        return False

    async def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution by ID."""
        return self._executions.get(execution_id)

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status summary."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        return {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "current_step": execution.workflow.current_step,
            "completed_steps": list(execution.workflow.completed_steps),
            "failed_steps": list(execution.workflow.failed_steps),
            "step_count": len(execution.workflow.steps),
            "progress": len(execution.workflow.completed_steps) / max(len(execution.workflow.steps), 1) * 100
        }

    # Visual Workflow Definition
    async def create_workflow_from_dag(
        self,
        name: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        variables: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """Create workflow from DAG definition (nodes and edges)."""
        workflow = Workflow(name=name)
        workflow.variables = variables or {}

        # Create steps from nodes
        node_map = {}
        for node in nodes:
            step = WorkflowStep(
                step_id=node.get("id", str(uuid.uuid4())[:8]),
                name=node.get("name", ""),
                description=node.get("description", ""),
                step_type=StepType(node.get("type", "task")),
                action=node.get("action", ""),
                parameters=node.get("parameters", {}),
                agent_type=node.get("agent_type", "default"),
                max_retries=node.get("max_retries", 3),
                timeout_seconds=node.get("timeout_seconds", 300),
                loop_config=node.get("loop_config"),
                condition=node.get("condition"),
                metadata=node.get("metadata", {})
            )
            workflow.steps.append(step)
            node_map[node["id"]] = step.step_id

        # Set dependencies from edges
        for edge in edges:
            source = node_map.get(edge["source"])
            target = node_map.get(edge["target"])
            if source and target:
                for step in workflow.steps:
                    if step.step_id == target:
                        step.depends_on.append(source)
                        break

        return await self.create_workflow(workflow)

    async def export_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Export workflow as DAG (nodes/edges)."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        nodes = []
        edges = []

        for step in workflow.steps:
            nodes.append({
                "id": step.step_id,
                "name": step.name,
                "description": step.description,
                "type": step.step_type.value,
                "action": step.action,
                "parameters": step.parameters,
                "agent_type": step.agent_type,
                "max_retries": step.max_retries,
                "timeout_seconds": step.timeout_seconds,
                "loop_config": step.loop_config,
                "condition": step.condition,
                "metadata": step.metadata
            })

            for dep in step.depends_on:
                edges.append({"source": dep, "target": step.step_id})

        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "version": workflow.version,
            "variables": workflow.variables,
            "nodes": nodes,
            "edges": edges
        }

    # Persistence
    async def _load_workflows(self, path: str) -> None:
        """Load workflows from disk."""
        import os
        import aiofiles

        if not os.path.exists(path):
            return

        try:
            for filename in os.listdir(path):
                if filename.endswith(".json"):
                    filepath = os.path.join(path, filename)
                    async with aiofiles.open(filepath, 'r') as f:
                        content = await f.read()
                        data = json.loads(content)

                        # Reconstruct workflow
                        steps = []
                        for step_data in data.get("steps", []):
                            step = WorkflowStep(**step_data)
                            step.status = StepStatus(step_data.get("status", "pending"))
                            if step_data.get("started_at"):
                                step.started_at = datetime.fromisoformat(step_data["started_at"])
                            if step_data.get("completed_at"):
                                step.completed_at = datetime.fromisoformat(step_data["completed_at"])
                            steps.append(step)

                        workflow = Workflow(
                            workflow_id=data.get("workflow_id", str(uuid.uuid4())[:8]),
                            name=data.get("name", ""),
                            description=data.get("description", ""),
                            version=data.get("version", "1.0.0"),
                            steps=steps,
                            variables=data.get("variables", {}),
                            status=WorkflowStatus(data.get("status", "draft")),
                            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
                            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
                            metadata=data.get("metadata", {})
                        )

                        self._workflows[workflow.workflow_id] = workflow

            logger.info(f"Loaded {len(self._workflows)} workflows from {path}")
        except Exception as e:
            logger.error(f"Failed to load workflows: {e}")

    async def _save_workflows(self, path: str) -> None:
        """Save workflows to disk."""
        import os
        import aiofiles

        os.makedirs(path, exist_ok=True)

        try:
            for workflow in self._workflows.values():
                data = {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "description": workflow.description,
                    "version": workflow.version,
                    "status": workflow.status.value,
                    "created_at": workflow.created_at.isoformat(),
                    "updated_at": workflow.updated_at.isoformat(),
                    "variables": workflow.variables,
                    "metadata": workflow.metadata,
                    "steps": []
                }

                for step in workflow.steps:
                    data["steps"].append({
                        "step_id": step.step_id,
                        "name": step.name,
                        "description": step.description,
                        "step_type": step.step_type.value,
                        "action": step.action,
                        "parameters": step.parameters,
                        "agent_type": step.agent_type,
                        "depends_on": step.depends_on,
                        "condition": step.condition,
                        "loop_config": step.loop_config,
                        "max_retries": step.max_retries,
                        "retry_delay": step.retry_delay,
                        "timeout_seconds": step.timeout_seconds,
                        "status": step.status.value,
                        "result": step.result,
                        "error": step.error,
                        "started_at": step.started_at.isoformat() if step.started_at else None,
                        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                        "retry_count": step.retry_count,
                        "metadata": step.metadata
                    })

                filepath = os.path.join(path, f"{workflow.workflow_id}.json")
                async with aiofiles.open(filepath, 'w') as f:
                    await f.write(json.dumps(data, indent=2))

            logger.info(f"Saved {len(self._workflows)} workflows to {path}")
        except Exception as e:
            logger.error(f"Failed to save workflows: {e}")

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute module operations."""
        if operation == "create_workflow":
            return await self.create_workflow(kwargs.get("workflow"))
        elif operation == "get_workflow":
            return await self.get_workflow(kwargs.get("workflow_id"))
        elif operation == "update_workflow":
            return await self.update_workflow(kwargs.get("workflow"))
        elif operation == "delete_workflow":
            return await self.delete_workflow(kwargs.get("workflow_id"))
        elif operation == "list_workflows":
            return await self.list_workflows(**kwargs)
        elif operation == "execute_workflow":
            return await self.execute_workflow(
                kwargs.get("workflow_id"),
                kwargs.get("variables"),
                kwargs.get("execution_id")
            )
        elif operation == "cancel_execution":
            return await self.cancel_execution(kwargs.get("execution_id"))
        elif operation == "pause_execution":
            return await self.pause_execution(kwargs.get("execution_id"))
        elif operation == "resume_execution":
            return await self.resume_execution(kwargs.get("execution_id"))
        elif operation == "get_execution":
            return await self.get_execution(kwargs.get("execution_id"))
        elif operation == "get_execution_status":
            return await self.get_execution_status(kwargs.get("execution_id"))
        elif operation == "create_from_dag":
            return await self.create_workflow_from_dag(**kwargs)
        elif operation == "export_workflow":
            return await self.export_workflow(kwargs.get("workflow_id"))
        elif operation == "signal":
            return self.signal(kwargs.get("workflow_id"), kwargs.get("signal"), kwargs.get("data"))
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported")


# Export
__all__ = [
    "WorkflowModule",
    "Workflow",
    "WorkflowStep",
    "WorkflowExecution",
    "WorkflowStatus",
    "StepStatus",
    "StepType",
    "WorkflowExecutor",
]