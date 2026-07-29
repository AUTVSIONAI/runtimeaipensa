"""
Local Planning Module Implementation

Provides planning capabilities using LLM-based plan generation and execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio
import json
import logging
import uuid

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    PlanningModule,
    Plan,
    PlanStep,
    PlanStatus,
    StepStatus,
)

logger = logging.getLogger(__name__)


class LocalPlanningModule(PlanningModule):
    """
    Local planning implementation using LLM for plan generation.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="planning",
            version="1.0.0",
            description="LLM-based planning and execution",
            author="AIPENSA",
            dependencies=[],
            provides=["plan_creation", "plan_execution", "plan_management"],
            tags={"local", "planning", "llm"},
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._config = config or {}
        self._plans: Dict[str, Plan] = {}
        self._llm_config = self._config.get("llm", {})

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._llm_config = self._config.get("llm", self._llm_config)
        self.state = ModuleState.INITIALIZED
        logger.info("LocalPlanningModule initialized")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("LocalPlanningModule started")

    async def stop(self) -> None:
        self.state = ModuleState.STOPPED
        logger.info("LocalPlanningModule stopped")

    async def cleanup(self) -> None:
        self._plans.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("LocalPlanningModule cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "planning",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "active_plans": len([p for p in self._plans.values() if p.status == PlanStatus.ACTIVE]),
            "total_plans": len(self._plans),
        }

    async def create_plan(
        self,
        goal: str,
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """Create an execution plan from goal using LLM."""
        from app.llm import LLM

        plan_id = str(uuid.uuid4())[:8]

        # Use LLM to generate plan
        llm = LLM(**self._llm_config)

        prompt = f"""Create an execution plan for the following goal.

Goal: {goal}

Context: {json.dumps(context, default=str)}

Constraints: {json.dumps(constraints or {}, default=str)}

Return a JSON with the following structure:
{{
    "steps": [
        {{
            "step_id": "step_1",
            "name": "Step name",
            "description": "What this step does",
            "action": "tool_name or action_type",
            "parameters": {{}},
            "agent_type": "default",
            "dependencies": [],
            "max_retries": 3
        }}
    ]
}}"""

        messages = [{"role": "system", "content": prompt}]

        try:
            response = await llm.ask(messages)

            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
            else:
                plan_data = {"steps": []}
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            plan_data = {"steps": []}

        steps = []
        for i, step_data in enumerate(plan_data.get("steps", [])):
            step = PlanStep(
                step_id=step_data.get("step_id", f"step_{i+1}"),
                name=step_data.get("name", f"Step {i+1}"),
                description=step_data.get("description", ""),
                action=step_data.get("action", ""),
                parameters=step_data.get("parameters", {}),
                agent_type=step_data.get("agent_type", "default"),
                dependencies=step_data.get("dependencies", []),
                max_retries=step_data.get("max_retries", 3),
            )
            steps.append(step)

        plan = Plan(
            plan_id=plan_id,
            goal=goal,
            context=context,
            constraints=constraints or {},
            steps=steps,
            status=PlanStatus.DRAFT,
        )

        self._plans[plan_id] = plan
        return plan

    async def execute_plan(
        self,
        plan_id: str,
        agents: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a plan with given agents."""
        if plan_id not in self._plans:
            raise ValueError(f"Plan not found: {plan_id}")

        plan = self._plans[plan_id]
        plan.status = PlanStatus.ACTIVE
        plan.started_at = datetime.utcnow()

        results = {}
        completed_steps = set()

        try:
            while True:
                # Find next runnable step
                runnable = None
                for step in plan.steps:
                    if step.status == StepStatus.PENDING:
                        deps_met = all(dep in completed_steps for dep in step.dependencies)
                        if deps_met:
                            runnable = step
                            break

                if not runnable:
                    break  # No more runnable steps

                # Execute step
                runnable.status = StepStatus.RUNNING
                runnable.started_at = datetime.utcnow()

                try:
                    agent = agents.get(runnable.agent_type)
                    if not agent:
                        raise ValueError(f"Agent not found: {runnable.agent_type}")

                    # Execute based on action type
                    if runnable.action.startswith("tool:"):
                        tool_name = runnable.action[5:]
                        tools = self._runtime.get_tools()
                        if tools:
                            result = await tools.execute_tool(tool_name, runnable.parameters)
                            runnable.result = result
                    elif runnable.action == "python":
                        execution = self._runtime.get_execution()
                        if execution:
                            result = await execution.execute_python(runnable.parameters.get("code", ""))
                            runnable.result = result
                    elif runnable.action == "shell":
                        execution = self._runtime.get_execution()
                        if execution:
                            result = await execution.execute_shell(runnable.parameters.get("command", ""))
                            runnable.result = result
                    else:
                        # Custom agent action
                        runnable.result = await agent.execute(runnable.action, runnable.parameters)

                    runnable.status = StepStatus.COMPLETED
                    runnable.completed_at = datetime.utcnow()
                    completed_steps.add(runnable.step_id)
                    results[runnable.step_id] = runnable.result

                except Exception as e:
                    runnable.error = str(e)
                    runnable.retry_count += 1

                    if runnable.retry_count >= runnable.max_retries:
                        runnable.status = StepStatus.FAILED
                        runnable.completed_at = datetime.utcnow()
                        plan.status = PlanStatus.FAILED
                        break
                    else:
                        runnable.status = StepStatus.PENDING
                        await asyncio.sleep(1)  # Wait before retry

            # Check final status
            if plan.status == PlanStatus.ACTIVE:
                failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]
                if failed_steps:
                    plan.status = PlanStatus.FAILED
                else:
                    plan.status = PlanStatus.COMPLETED

            plan.completed_at = datetime.utcnow()

            return {
                "plan_id": plan_id,
                "status": plan.status.value,
                "results": results,
                "steps_completed": len([s for s in plan.steps if s.status == StepStatus.COMPLETED]),
                "steps_failed": len([s for s in plan.steps if s.status == StepStatus.FAILED]),
            }

        except Exception as e:
            plan.status = PlanStatus.FAILED
            plan.completed_at = datetime.utcnow()
            return {
                "plan_id": plan_id,
                "status": PlanStatus.FAILED.value,
                "error": str(e),
                "results": results,
            }

    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get plan by ID."""
        return self._plans.get(plan_id)

    async def update_plan(self, plan: Plan) -> Plan:
        """Update plan."""
        if plan.plan_id in self._plans:
            plan.updated_at = datetime.utcnow()
            self._plans[plan.plan_id] = plan
        return plan

    async def cancel_plan(self, plan_id: str) -> bool:
        """Cancel plan execution."""
        if plan_id in self._plans:
            plan = self._plans[plan_id]
            if plan.status in (PlanStatus.DRAFT, PlanStatus.ACTIVE):
                plan.status = PlanStatus.CANCELLED
                plan.completed_at = datetime.utcnow()
                return True
        return False

    async def list_plans(
        self,
        status: Optional[PlanStatus] = None,
        limit: int = 50
    ) -> List[Plan]:
        """List plans."""
        plans = list(self._plans.values())

        if status:
            plans = [p for p in plans if p.status == status]

        plans.sort(key=lambda p: p.created_at, reverse=True)
        return plans[:limit]