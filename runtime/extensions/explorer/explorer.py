"""
Runtime Explorer & Company Explorer - Observabilidade e Debug.

Exporta dados do Runtime, Workflows, Employees, Providers para frontend.
Não modifica módulos existentes - apenas agrega via composição.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import asyncio

from runtime.base.module import RuntimeModule, ModuleMetadata
from runtime.base.events import get_event_bus, RuntimeEventType, create_event

if TYPE_CHECKING:
    from runtime.runtime import Runtime


@dataclass
class ModuleOverview:
    name: str
    version: str
    state: str
    category: str
    health: str
    latency_ms: int
    last_check: str
    checks: Dict[str, str]

@dataclass
class AgentOverview:
    agent_id: str
    name: str
    role: str
    status: str
    company_id: str
    team_id: Optional[str]
    model: str
    tasks_completed: int
    tasks_failed: int
    avg_response_time_ms: float
    last_activity: str
    memory_usage_mb: float

@dataclass
class WorkflowOverview:
    workflow_id: str
    name: str
    version: str
    status: str
    team_id: Optional[str]
    last_execution: Optional[Dict[str, Any]]
    stats: Dict[str, Any]

@dataclass
class QueueOverview:
    queue_id: str
    name: str
    type: str
    pending: int
    processing: int
    dlq: int
    depth: int


class RuntimeExplorer:
    """
    Explorer do Runtime - visão técnica (Task Manager style).

    Agregador read-only que compõe dados dos módulos existentes.
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.event_bus = get_event_bus()

    async def get_overview(self) -> Dict[str, Any]:
        """Visão geral estilo Task Manager."""
        modules = await self._get_modules_overview()
        agents = await self._get_agents_overview()
        workflows = await self._get_workflows_overview()
        queues = await self._get_queues_overview()
        memory = await self._get_memory_overview()
        llm = await self._get_llm_overview()
        events = await self._get_events_overview()

        return {
            "runtime": {
                "status": "healthy",
                "uptime": str(self.runtime.uptime) if hasattr(self.runtime, 'uptime') else "unknown",
                "version": getattr(self.runtime, 'version', '1.0.0')
            },
            "modules": modules,
            "agents": agents,
            "workflows": workflows,
            "queues": queues,
            "memory": memory,
            "llm": llm,
            "events": events
        }

    async def _get_modules_overview(self) -> Dict[str, Any]:
        modules = []
        module_registry = self.runtime.module_registry

        for name, module in module_registry._modules.items():
            health = await module.health_check()
            modules.append({
                "name": name,
                "version": module.version,
                "state": health.state.value if hasattr(health.state, 'value') else str(health.state),
                "category": self._categorize_module(name),
                "health": health.checks.get("overall", "unknown"),
                "latency_ms": 0,  # Would measure
                "last_check": health.timestamp.isoformat() if health.timestamp else "",
                "checks": health.checks
            })

        return {
            "total": len(modules),
            "running": sum(1 for m in modules if m["state"] == "RUNNING"),
            "degraded": sum(1 for m in modules if m["state"] == "DEGRADED"),
            "stopped": sum(1 for m in modules if m["state"] == "STOPPED"),
            "modules": modules
        }

    def _categorize_module(self, name: str) -> str:
        categories = {
            "agent": "intelligence",
            "conversation": "intelligence",
            "skill": "intelligence",
            "llm": "intelligence",
            "workflow": "orchestration",
            "scheduler": "orchestration",
            "queue": "orchestration",
            "planning": "orchestration",
            "browser": "capabilities",
            "execution": "capabilities",
            "filesystem": "capabilities",
            "network": "capabilities",
            "docker": "capabilities",
            "mcp": "capabilities",
            "memory": "foundation",
            "storage": "foundation",
            "authentication": "foundation",
            "notification": "foundation",
            "workspace": "foundation",
            "voice": "ai",
            "vision": "ai",
            "video": "ai",
            "image": "ai",
            "embedding": "ai",
            "rag": "ai",
            "reasoning": "ai",
        }
        return categories.get(name, "core")

    async def _get_agents_overview(self) -> Dict[str, Any]:
        agent_module = self.runtime.get_module("agent")
        agents = []

        for agent_id, agent in agent_module.agents.items():
            agents.append({
                "agent_id": agent_id,
                "name": agent.name,
                "role": agent.role.value if hasattr(agent.role, 'value') else str(agent.role),
                "status": getattr(agent, 'status', 'unknown'),
                "company_id": getattr(agent, 'company_id', ''),
                "team_id": getattr(agent, 'team_id', None),
                "model": agent.model,
                "tasks_completed": getattr(agent, 'tasks_completed', 0),
                "tasks_failed": getattr(agent, 'tasks_failed', 0),
                "avg_response_time_ms": getattr(agent, 'avg_response_time_ms', 0),
                "last_activity": getattr(agent, 'last_activity', '').isoformat() if getattr(agent, 'last_activity', None) else "",
                "memory_usage_mb": getattr(agent, 'memory_usage_mb', 0)
            })

        return {
            "active": sum(1 for a in agents if a["status"] == "running"),
            "idle": sum(1 for a in agents if a["status"] == "idle"),
            "busy": sum(1 for a in agents if a["status"] == "busy"),
            "error": sum(1 for a in agents if a["status"] == "error"),
            "agents": agents
        }

    async def _get_workflows_overview(self) -> Dict[str, Any]:
        workflow_module = self.runtime.get_module("workflow")
        workflows = []

        # Get from workflow module (implementation dependent)
        if hasattr(workflow_module, 'workflows'):
            for wf_id, wf in workflow_module.workflows.items():
                workflows.append({
                    "workflow_id": wf_id,
                    "name": getattr(wf, 'name', wf_id),
                    "version": getattr(wf, 'version', '1.0.0'),
                    "status": "ACTIVE",
                    "team_id": getattr(wf, 'team_id', None),
                    "last_execution": None,  # Would query execution history
                    "stats": {"executions_total": 0, "success_rate": 1.0}
                })

        return {
            "running": sum(1 for w in workflows if w["status"] == "running"),
            "queued": 0,  # Would query scheduler
            "completed_today": 0,
            "failed_today": 0,
            "workflows": workflows
        }

    async def _get_queues_overview(self) -> Dict[str, Any]:
        queue_module = self.runtime.get_module("queue")
        queues = []

        if hasattr(queue_module, 'queues'):
            for q_id, queue in queue_module.queues.items():
                queues.append({
                    "queue_id": q_id,
                    "name": getattr(queue, 'name', q_id),
                    "type": getattr(queue, 'queue_type', 'fifo'),
                    "pending": getattr(queue, 'pending_count', 0),
                    "processing": getattr(queue, 'processing_count', 0),
                    "dlq": getattr(queue, 'dlq_count', 0),
                    "depth": getattr(queue, 'depth', 0)
                })

        return {
            "messages_pending": sum(q["pending"] for q in queues),
            "processing": sum(q["processing"] for q in queues),
            "dlq": sum(q["dlq"] for q in queues),
            "queues": queues
        }

    async def _get_memory_overview(self) -> Dict[str, Any]:
        memory_module = self.runtime.get_module("memory")
        stores = 0
        total_keys = 0
        size_mb = 0

        if hasattr(memory_module, 'stores'):
            for store_name, store in memory_module.stores.items():
                stores += 1
                if hasattr(store, 'count'):
                    total_keys += store.count()
                if hasattr(store, 'size_bytes'):
                    size_mb += store.size_bytes() / (1024 * 1024)

        return {
            "stores": stores,
            "total_keys": total_keys,
            "size_mb": round(size_mb, 2)
        }

    async def _get_llm_overview(self) -> Dict[str, Any]:
        llm_module = self.runtime.get_module("llm")
        return {
            "requests_today": 0,  # Would track
            "tokens_today": 0,
            "cost_usd_today": 0.0,
            "models_available": len(getattr(llm_module, 'models', {})),
            "providers_loaded": len(getattr(llm_module, 'providers', {}))
        }

    async def _get_events_overview(self):
        event_bus = get_event_bus()
        return {
            "per_second": 0,  # Would calculate
            "history_size": len(getattr(event_bus, '_event_log', [])),
            "dlq_size": len(getattr(event_bus, '_dead_letter', []))
        }

    # =====================================================
    # DETAILED VIEWS
    # =====================================================

    async def get_modules(self, category: str = None, state: str = None) -> List[Dict]:
        """Lista módulos com filtros."""
        overview = await self._get_modules_overview()
        modules = overview["modules"]
        if category:
            modules = [m for m in modules if m["category"] == category]
        if state:
            modules = [m for m in modules if m["state"] == state]
        return modules

    async def get_module_detail(self, module_name: str) -> Optional[Dict]:
        """Detalhes completos de um módulo."""
        module = self.runtime.module_registry._modules.get(module_name)
        if not module:
            return None

        health = await module.health_check()
        return {
            "name": module_name,
            "version": module.version,
            "metadata": asdict(module.metadata) if hasattr(module, 'metadata') else {},
            "health": asdict(health) if hasattr(health, '__dataclass_fields__') else str(health),
            "operations": self._get_module_operations(module)
        }

    def _get_module_operations(self, module) -> List[str]:
        """Extrai operações disponíveis do módulo."""
        if hasattr(module, 'execute'):
            # Would inspect execute signature
            return ["health_check"]  # Simplified
        return []

    async def get_agents(self, company_id: str = None, status: str = None) -> List[Dict]:
        """Lista agents/employees com filtros."""
        overview = await self._get_agents_overview()
        agents = overview["agents"]
        if company_id:
            agents = [a for a in agents if a["company_id"] == company_id]
        if status:
            agents = [a for a in agents if a["status"] == status]
        return agents

    async def get_workflows(self, company_id: str = None, team_id: str = None) -> List[Dict]:
        overview = await self._get_workflows_overview()
        workflows = overview["workflows"]
        if team_id:
            workflows = [w for w in workflows if w["team_id"] == team_id]
        return workflows

    async def get_queues(self) -> List[Dict]:
        overview = await self._get_queues_overview()
        return overview["queues"]

    async def get_recent_events(self, limit: int = 100, event_type: str = None) -> List[Dict]:
        """Últimos eventos do EventBus."""
        event_bus = get_event_bus()
        events = getattr(event_bus, '_event_log', [])
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [
            {
                "event_id": e.correlation_id,  # Using correlation_id as identifier
                "event_type": e.event_type,
                "source": e.source,
                "timestamp": e.timestamp.isoformat() if e.timestamp else "",
                "correlation_id": e.correlation_id,
                "causation_id": e.causation_id,
                "payload": e.payload,
                "priority": e.priority.value if hasattr(e.priority, 'value') else str(e.priority)
            }
            for e in events[-limit:]
        ]

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Métricas de performance por módulo."""
        # Would integrate with Prometheus metrics
        return {
            "modules": {},
            "latency_p50": 0,
            "latency_p99": 0,
            "error_rate": 0.0,
            "throughput_rps": 0
        }


class CompanyExplorer:
    """
    Company Explorer - Visão de negócio (Company Context).

    Foca em: Companies, Employees, Teams, Providers, Workflows de negócio.
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.event_bus = get_event_bus()

    async def get_companies(self) -> List[Dict]:
        """Lista empresas registradas."""
        # Query MemoryModule for company stores
        memory = self.runtime.get_module("memory")
        companies = []

        # List stores matching pattern
        if hasattr(memory, 'stores'):
            for store_name in memory.stores:
                if store_name.startswith("company_") and store_name.endswith("_profile"):
                    # Extract company_id
                    company_id = store_name.replace("company_", "").replace("_profile", "")
                    profile_data = await memory.read(store=f"company_{company_id}", key="profile")
                    if profile_data:
                        companies.append({
                            "company_id": company_id,
                            "name": profile_data.get("name", ""),
                            "segment": profile_data.get("segment", ""),
                            "size": profile_data.get("size", ""),
                            "employee_count": await self._count_employees(company_id),
                            "team_count": await self._count_teams(company_id)
                        })

        return companies

    async def get_company_detail(self, company_id: str) -> Optional[Dict]:
        """Detalhes completos da empresa."""
        memory = self.runtime.get_module("memory")

        profile = await memory.read(store=f"company_{company_id}", key="profile")
        if not profile:
            return None

        brand = await memory.read(store=f"company_{company_id}", key="brand")
        products = await memory.read(store=f"company_{company_id}", key="products")
        channels = await memory.read(store=f"company_{company_id}", key="channels")
        goals = await memory.read(store=f"company_{company_id}", key="goals")
        knowledge_index = await memory.read(store=f"company_{company_id}_knowledge", key="index")

        employees = await self.get_employees(company_id=company_id)
        teams = await self.get_teams(company_id=company_id)

        return {
            "company_id": company_id,
            "profile": profile,
            "brand": brand,
            "products": products,
            "channels": channels,
            "goals": goals,
            "knowledge_count": len(knowledge_index.get("entries", [])) if knowledge_index else 0,
            "employees": employees,
            "teams": teams
        }

    async def get_employees(self, company_id: str = None, team_id: str = None) -> List[Dict]:
        """Lista employees com detalhes."""
        employee_module = self.runtime.get_module("employee")
        if not employee_module or not employee_module.registry:
            return []

        employees = await employee_module.registry.list_employees(
            company_id=company_id,
            team_id=team_id
        )

        return [
            {
                "employee_id": e.employee_id,
                "name": e.profile.name,
                "role": e.profile.role.value,
                "specialization": e.profile.specialization,
                "model": e.profile.model,
                "team_id": e.profile.team_id,
                "skills": e.profile.skills,
                "enabled": e.profile.enabled,
                "status": e.profile.status.value,
                "tasks_completed": e.tasks_completed,
                "tasks_failed": e.tasks_failed,
                "created_at": e.profile.created_at.isoformat()
            }
            for e in employees
        ]

    async def get_employee_detail(self, employee_id: str) -> Optional[Dict]:
        """Detalhes completos de um employee."""
        employee_module = self.runtime.get_module("employee")
        if not employee_module or not employee_module.registry:
            return None

        emp = await employee_module.registry.get_employee(employee_id)
        if not emp:
            return None

        # Get agent state
        agent_module = self.runtime.get_module("agent")
        agent = agent_module.agents.get(employee_id) if agent_module else None

        return {
            "employee_id": employee_id,
            "profile": emp.profile.__dict__ if hasattr(emp.profile, '__dict__') else {},
            "agent_state": {
                "status": getattr(agent, 'status', 'unknown'),
                "memory_usage_mb": getattr(agent, 'memory_usage_mb', 0),
                "current_task": getattr(emp, 'current_task', None)
            } if agent else {},
            "skills": emp.profile.skills,
            "provider_access": emp.company_context.channels.__dict__ if emp.company_context else {},
            "recent_tasks": []  # Would query execution history
        }

    async def get_teams(self, company_id: str = None) -> List[Dict]:
        """Lista teams."""
        team_module = self.runtime.get_module("team")
        if not team_module or not team_module.manager:
            return []

        teams = await team_module.manager.list_teams(company_id or "")
        return [
            {
                "team_id": t.team_id,
                "name": t.name,
                "description": t.description,
                "team_type": t.team_type.value,
                "member_count": len(t.members),
                "workflow_count": len(t.workflow_ids),
                "workspace_id": t.workspace_id,
                "parent_team_id": t.parent_team_id
            }
            for t in teams
        ]

    async def get_team_detail(self, team_id: str) -> Optional[Dict]:
        """Detalhes do time."""
        team_module = self.runtime.get_module("team")
        if not team_module or not team_module.manager:
            return None

        team = await team_module.manager.get_team(team_id)
        if not team:
            return None

        # Get member details
        employee_module = self.runtime.get_module("employee")
        members = []
        for m in team.members.values():
            emp = await employee_module.registry.get_employee(m.employee_id) if employee_module else None
            if emp:
                members.append({
                    "employee_id": m.employee_id,
                    "name": emp.profile.name,
                    "role": m.role.value,
                    "skills": emp.profile.skills,
                    "status": emp.profile.status.value
                })

        return {
            "team_id": team_id,
            "name": team.name,
            "description": team.description,
            "team_type": team.team_type.value,
            "workspace_id": team.workspace_id,
            "members": members,
            "workflows": team.workflow_ids,
            "shared_context": team.shared_context
        }

    async def get_providers(self, company_id: str = None) -> List[Dict]:
        """Lista providers conectados."""
        provider_module = self.runtime.get_module("provider")
        if not provider_module or not provider_module.registry:
            return []

        conns = []
        if company_id:
            conns = provider_module.registry.manager.get_company_connections(company_id)
        else:
            # All connections
            for cid, conn in provider_module.registry.manager.connections.items():
                conns.append(conn)

        return [
            {
                "connection_id": c.connection_id,
                "provider_id": c.provider_id,
                "provider_name": provider_module.registry.get_provider(c.provider_id).name if provider_module.registry.get_provider(c.provider_id) else c.provider_id,
                "company_id": c.company_id,
                "status": c.status,
                "scopes": c.scopes,
                "connected_at": c.connected_at.isoformat(),
                "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None
            }
            for c in conns
        ]

    async def get_workflows(self, company_id: str = None) -> List[Dict]:
        """Workflows de negócio."""
        explorer = RuntimeExplorer(self.runtime)
        return await explorer.get_workflows(company_id=company_id)

    def _count_employees(self, company_id: str) -> int:
        return 0  # Would query

    def _count_teams(self, company_id: str) -> int:
        return 0  # Would query


class ExplorerModule(RuntimeModule):
    """Module wrapper para Explorer systems."""

    metadata = ModuleMetadata(
        name="explorer",
        version="1.0.0",
        description="Runtime & Company Explorer - Observability and Business Intelligence"
    )

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.runtime_explorer: Optional[RuntimeExplorer] = None
        self.company_explorer: Optional[CompanyExplorer] = None

    async def initialize(self, runtime, config: Dict[str, Any]) -> None:
        await super().initialize(runtime, config)
        self.runtime_explorer = RuntimeExplorer(runtime)
        self.company_explorer = CompanyExplorer(runtime)

    async def start(self) -> None:
        await super().start()
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            RuntimeEventType.MODULE_STARTED,
            "explorer",
            {"module": self.name, "version": self.metadata.version}
        ))

    async def stop(self) -> None:
        await super().stop()

    async def cleanup(self) -> None:
        self.runtime_explorer = None
        self.company_explorer = None
        await super().cleanup()

    async def health_check(self):
        from runtime.base.module import ModuleHealth, ModuleState
        return ModuleHealth(
            module=self.name,
            state=ModuleState.RUNNING,
            checks={"runtime_explorer": "ok", "company_explorer": "ok"},
            timestamp=datetime.utcnow()
        )

    async def execute(self, operation: str, **params) -> Any:
        ops = {
            # Runtime Explorer
            "get_overview": self.runtime_explorer.get_overview,
            "get_modules": self.runtime_explorer.get_modules,
            "get_module_detail": self.runtime_explorer.get_module_detail,
            "get_agents": self.runtime_explorer.get_agents,
            "get_workflows": self.runtime_explorer.get_workflows,
            "get_queues": self.runtime_explorer.get_queues,
            "get_recent_events": self.runtime_explorer.get_recent_events,
            "get_performance": self.runtime_explorer.get_performance_metrics,
            # Company Explorer
            "get_companies": self.company_explorer.get_companies,
            "get_company_detail": self.company_explorer.get_company_detail,
            "get_employees": self.company_explorer.get_employees,
            "get_employee_detail": self.company_explorer.get_employee_detail,
            "get_teams": self.company_explorer.get_teams,
            "get_team_detail": self.company_explorer.get_team_detail,
            "get_providers": self.company_explorer.get_providers,
            "get_company_workflows": self.company_explorer.get_workflows,
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: {operation}")
        return await ops[operation](**params)