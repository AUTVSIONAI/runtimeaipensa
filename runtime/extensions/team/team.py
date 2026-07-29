"""
Team Manager - Workspaces Hierárquicos como Times.

Estende o WorkspaceModule existente para adicionar:
- Hierarquia Company → Team → Project
- Membership com roles
- Delegação de tasks entre employees
- Workflows de time
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

from runtime.base.module import RuntimeModule, ModuleMetadata
from runtime.base.events import get_event_bus, RuntimeEventType, create_event
from runtime.workspace.module import WorkspaceModule, WorkspaceType
from runtime.extensions.employee.employee import EmployeeRegistry, Employee
from runtime.extensions.company.engine import CompanyContextEngine


class TeamRole(str, Enum):
    """Roles dentro de um Team."""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    LEAD = "LEAD"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class TeamType(str, Enum):
    """Tipos de times."""
    FUNCTIONAL = "functional"      # Marketing, Finance, Support
    PROJECT = "project"            # Projeto específico
    CROSS_FUNCTIONAL = "cross_functional"  # Squad multifuncional
    LEADERSHIP = "leadership"      # C-level, diretoria


@dataclass
class TeamMember:
    """Membro de um time - link Employee ↔ Team."""
    employee_id: str
    team_id: str
    role: TeamRole = TeamRole.MEMBER
    joined_at: datetime = field(default_factory=datetime.utcnow)
    permissions: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class Team:
    """Team = Workspace especializado com membros Employees."""
    team_id: str
    company_id: str
    name: str
    description: str = ""
    team_type: TeamType = TeamType.FUNCTIONAL
    parent_team_id: Optional[str] = None  # Para sub-times

    # Workspace integration
    workspace_id: str = ""

    # Members
    members: Dict[str, TeamMember] = field(default_factory=dict)  # employee_id -> TeamMember

    # Shared context
    shared_context: Dict[str, Any] = field(default_factory=dict)

    # Associated workflows
    workflow_ids: List[str] = field(default_factory=list)

    # Settings
    settings: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


class TeamManager:
    """Gerencia Teams como workspaces hierárquicos com Employees."""

    def __init__(
        self,
        workspace_module: WorkspaceModule,
        employee_registry: EmployeeRegistry,
        company_context_engine: CompanyContextEngine
    ):
        self.workspace_module = workspace_module
        self.employee_registry = employee_registry
        self.company_context_engine = company_context_engine
        self.teams: Dict[str, Team] = {}
        self.event_bus = get_event_bus()

    async def create_team(
        self,
        company_id: str,
        name: str,
        description: str = "",
        team_type: TeamType = TeamType.FUNCTIONAL,
        parent_team_id: Optional[str] = None,
        members: List[str] = None,
        created_by: Optional[str] = None
    ) -> Team:
        """Cria Team + Workspace associado."""

        # 1. Criar Workspace tipo TEAM
        workspace = await self.workspace_module.create_workspace(
            name=name,
            workspace_type=WorkspaceType.TEAM,
            parent_id=f"ws_{company_id}",  # Company workspace
            quotas=self._default_team_quotas(),
            settings={
                "allow_public_invite": False,
                "require_2fa": True,
                "team_type": team_type.value
            }
        )

        # 2. Criar Team
        team = Team(
            team_id=f"team_{uuid.uuid4().hex[:12]}",
            company_id=company_id,
            name=name,
            description=description,
            team_type=team_type,
            parent_team_id=parent_team_id,
            workspace_id=workspace.workspace_id,
            created_by=created_by
        )

        # 3. Adicionar membros iniciais
        if members:
            for emp_id in members:
                await self.add_member(team.team_id, emp_id, TeamRole.MEMBER)

        self.teams[team.team_id] = team

        # 4. Emit event
        await self.event_bus.publish(create_event(
            RuntimeEventType.TEAM_CREATED,
            f"team:{team.team_id}",
            {
                "team_id": team.team_id,
                "company_id": company_id,
                "name": name,
                "team_type": team_type.value,
                "workspace_id": workspace.workspace_id,
                "parent_team_id": parent_team_id
            }
        ))

        return team

    def _default_team_quotas(self) -> Dict:
        return {
            "max_members": 50,
            "max_workflows": 100,
            "max_scheduled_jobs": 50,
            "storage_mb": 1024,
            "llm_tokens_per_month": 1000000
        }

    async def add_member(
        self,
        team_id: str,
        employee_id: str,
        role: TeamRole = TeamRole.MEMBER,
        permissions: List[str] = None
    ) -> TeamMember:
        """Adiciona Employee ao Team."""
        team = self.teams.get(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")

        # Verificar se employee existe
        employee = await self.employee_registry.get_employee(employee_id)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")

        # Verificar se employee pertence à mesma empresa
        if employee.profile.company_id != team.company_id:
            raise ValueError(f"Employee belongs to different company")

        # Criar membership
        member = TeamMember(
            employee_id=employee_id,
            team_id=team_id,
            role=role,
            permissions=permissions or self._default_permissions_for_role(role)
        )

        team.members[employee_id] = member

        # Adicionar ao workspace
        await self.workspace_module.add_member(
            team.workspace_id,
            employee_id,
            role.value,
            permissions=member.permissions
        )

        await self.event_bus.publish(create_event(
            RuntimeEventType.TEAM_MEMBER_ADDED,
            f"team:{team_id}",
            {
                "team_id": team_id,
                "employee_id": employee_id,
                "role": role.value
            }
        ))

        return member

    def _default_permissions_for_role(self, role: TeamRole) -> List[str]:
        perms = {
            TeamRole.OWNER: ["team.*", "workflow.*", "member.*"],
            TeamRole.ADMIN: ["workflow.execute", "workflow.create", "member.add", "member.remove"],
            TeamRole.LEAD: ["workflow.execute", "task.delegate", "member.view"],
            TeamRole.MEMBER: ["workflow.execute", "task.execute"],
            TeamRole.VIEWER: ["workflow.view", "task.view"]
        }
        return perms.get(role, [])

    async def remove_member(self, team_id: str, employee_id: str, reason: str = "") -> bool:
        """Remove Employee do Team."""
        team = self.teams.get(team_id)
        if not team or employee_id not in team.members:
            return False

        del team.members[employee_id]

        # Remover do workspace
        await self.workspace_module.remove_member(team.workspace_id, employee_id)

        await self.event_bus.publish(create_event(
            RuntimeEventType.TEAM_MEMBER_REMOVED,
            f"team:{team_id}",
            {"team_id": team_id, "employee_id": employee_id, "reason": reason}
        ))

        return True

    async def change_member_role(self, team_id: str, employee_id: str, new_role: TeamRole) -> bool:
        """Altera role do membro no Team."""
        team = self.teams.get(team_id)
        if not team or employee_id not in team.members:
            return False

        old_role = team.members[employee_id].role
        team.members[employee_id].role = new_role
        team.members[employee_id].permissions = self._default_permissions_for_role(new_role)

        # Atualizar workspace
        await self.workspace_module.update_member_role(
            team.workspace_id,
            employee_id,
            new_role.value,
            team.members[employee_id].permissions
        )

        await self.event_bus.publish(create_event(
            RuntimeEventType.TEAM_MEMBER_ROLE_CHANGED,
            f"team:{team_id}",
            {"team_id": team_id, "employee_id": employee_id, "from_role": old_role.value, "to_role": new_role.value}
        ))

        return True

    async def delegate_task(
        self,
        team_id: str,
        from_employee_id: str,
        to_employee_id: str,
        task: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> str:
        """Delega task de um employee para outro dentro do time."""
        team = self.teams.get(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")

        if from_employee_id not in team.members or to_employee_id not in team.members:
            raise ValueError("Both employees must be team members")

        # Executar task no employee destino
        to_employee = await self.employee_registry.get_employee(to_employee_id)
        if not to_employee:
            raise ValueError(f"Employee {to_employee_id} not found")

        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task_with_context = {
            **task,
            "task_id": task_id,
            "delegated_from": from_employee_id,
            "delegated_to": to_employee_id,
            "team_id": team_id,
            "context": context or {}
        }

        # Enviar via AgentModule message passing
        await self.employee_registry.factory.agent_module.send_message(
            to_agent_id=to_employee_id,
            from_agent_id=from_employee_id,
            content=task_with_context,
            message_type="task_delegation"
        )

        await self.event_bus.publish(create_event(
            RuntimeEventType.TASK_DELEGATED,
            f"team:{team_id}",
            {
                "team_id": team_id,
                "task_id": task_id,
                "from_employee": from_employee_id,
                "to_employee": to_employee_id,
                "task_type": task.get("type", "unknown")
            }
        ))

        return task_id

    async def execute_team_workflow(
        self,
        team_id: str,
        workflow_id: str,
        input_data: Dict[str, Any],
        trigger: Dict[str, Any] = None
    ) -> str:
        """Executa workflow associado ao time."""
        team = self.teams.get(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")

        if workflow_id not in team.workflow_ids:
            raise ValueError(f"Workflow {workflow_id} not associated with team")

        # Get workflow module
        workflow_module = self.workspace_module.runtime.get_module("workflow")

        execution = await workflow_module.execute_workflow(
            workflow_id=workflow_id,
            input_data=input_data,
            context={
                "team_id": team_id,
                "company_id": team.company_id,
                "trigger": trigger or {}
            }
        )

        await self.event_bus.publish(create_event(
            RuntimeEventType.TEAM_WORKFLOW_STARTED,
            f"team:{team_id}",
            {
                "team_id": team_id,
                "workflow_id": workflow_id,
                "execution_id": execution.execution_id,
                "trigger": trigger
            }
        ))

        return execution.execution_id

    async def get_team(self, team_id: str) -> Optional[Team]:
        return self.teams.get(team_id)

    async def list_teams(self, company_id: str, team_type: TeamType = None) -> List[Team]:
        result = []
        for team in self.teams.values():
            if team.company_id == company_id:
                if team_type is None or team.team_type == team_type:
                    result.append(team)
        return result

    async def get_team_hierarchy(self, company_id: str) -> Dict[str, Any]:
        """Retorna hierarquia completa de times da empresa."""
        company_teams = await self.list_teams(company_id)
        hierarchy = {}

        # Build tree
        for team in company_teams:
            if team.parent_team_id is None:
                hierarchy[team.team_id] = await self._build_team_tree(team, company_teams)

        return hierarchy

    async def _build_team_tree(self, team: Team, all_teams: List[Team]) -> Dict:
        children = [t for t in all_teams if t.parent_team_id == team.team_id]
        members = []
        for m in team.members.values():
            emp = await self.employee_registry.get_employee(m.employee_id)
            if emp:
                members.append(emp)
        return {
            "team": team,
            "members": members,
            "children": {c.team_id: await self._build_team_tree(c, all_teams) for c in children}
        }


class TeamModule(RuntimeModule):
    """Module wrapper para Team system."""

    metadata = ModuleMetadata(
        name="team",
        version="1.0.0",
        description="Team Manager - Hierarchical Workspaces with Employees"
    )

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.workspace_module: Optional[WorkspaceModule] = None
        self.employee_registry: Optional[EmployeeRegistry] = None
        self.company_context_engine: Optional[CompanyContextEngine] = None
        self.manager: Optional[TeamManager] = None

    async def initialize(self, runtime, config: Dict[str, Any]) -> None:
        await super().initialize(runtime, config)
        self.workspace_module = self.runtime.get_module("workspace")
        self.employee_registry = self.runtime.get_module("employee").registry
        self.company_context_engine = self.runtime.get_module("company_context")

        self.manager = TeamManager(
            self.workspace_module,
            self.employee_registry,
            self.company_context_engine
        )

    async def start(self) -> None:
        await super().start()
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            RuntimeEventType.MODULE_STARTED,
            "team",
            {"module": self.name, "version": self.metadata.version}
        ))

    async def stop(self) -> None:
        await super().stop()

    async def cleanup(self) -> None:
        self.manager = None
        await super().cleanup()

    async def health_check(self):
        from runtime.base.module import ModuleHealth, ModuleState
        await super().cleanup()

    async def health_check(self):
        from runtime.base.module import ModuleHealth, ModuleState
        return ModuleHealth(
            module=self.name,
            state=ModuleState.RUNNING,
            checks={"teams": str(len(self.manager.teams)) if self.manager else "0"},
            timestamp=datetime.utcnow()
        )

    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "create_team": self.manager.create_team,
            "add_member": self.manager.add_member,
            "remove_member": self.manager.remove_member,
            "change_member_role": self.manager.change_member_role,
            "delegate_task": self.manager.delegate_task,
            "execute_team_workflow": self.manager.execute_team_workflow,
            "get_team": self.manager.get_team,
            "list_teams": self.manager.list_teams,
            "get_team_hierarchy": self.manager.get_team_hierarchy,
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: {operation}")
        return await ops[operation](**params)