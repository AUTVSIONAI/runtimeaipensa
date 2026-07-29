"""
Employee System - Agentes Especializados com Perfis de Negócio.

Employee = AgentMetadata + Business Context + Specialization
Extendendo o AgentModule existente sem modificar o Core.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

from runtime.base.module import RuntimeModule, ModuleMetadata, ModuleState
from runtime.agent.module import AgentModule, Agent, AgentRole, AgentMetadata
from runtime.base.events import get_event_bus, RuntimeEventType, create_event
from runtime.skill.module import SkillModule
from runtime.extensions.provider.provider import ProviderRegistry
from runtime.extensions.company.engine import CompanyContextEngine, CompanyContext, CompanyProducts, CompanyChannels, CompanyGoals


class EmployeeRole(str, Enum):
    """10 Roles fixos definidos na ENGINE_SPEC.md"""
    CEO = "CEO"
    MARKETING = "MARKETING"
    FINANCE = "FINANCE"
    SUPPORT = "SUPPORT"
    DESIGNER = "DESIGNER"
    EDITOR = "EDITOR"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    HR = "HR"
    LEGAL = "LEGAL"
    DELIVERY = "DELIVERY"


class MemoryScope(str, Enum):
    COMPANY = "COMPANY"
    TEAM = "TEAM"
    PERSONAL = "PERSONAL"


class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class EmployeeProfile:
    """Perfil completo do Employee - extensão de AgentMetadata."""
    employee_id: str
    company_id: str
    team_id: Optional[str] = None

    # Identidade
    name: str = ""
    role: EmployeeRole = EmployeeRole.SUPPORT
    specialization: str = ""

    # Configuração LLM
    model: str = "meta/llama-3.1-8b-instruct"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt_addendum: str = ""

    # Capabilities
    skills: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)

    # Memory & Context
    memory_scope: MemoryScope = MemoryScope.COMPANY

    # Estado
    enabled: bool = True
    status: EmployeeStatus = EmployeeStatus.OFFLINE
    version: str = "1.0.0"

    # Runtime config
    configuration: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


# Configurações padrão por Role (definidas na ENGINE_SPEC.md)
ROLE_CONFIGS = {
    EmployeeRole.CEO: {
        "system_prompt_template": "ceo_prompt.j2",
        "default_skills": ["strategic_planning", "kpi_analysis", "team_management", "decision_making"],
        "default_model": "meta/llama-3.1-70b-instruct",
        "temperature": 0.3,
        "default_permissions": ["workflow.create", "workflow.execute", "team.manage", "company.context.read"],
    },
    EmployeeRole.MARKETING: {
        "system_prompt_template": "marketing_prompt.j2",
        "default_skills": ["campaign_management", "market_analysis", "content_strategy", "seo_optimization"],
        "default_model": "meta/llama-3.1-70b-instruct",
        "temperature": 0.5,
        "default_permissions": ["skill.execute:marketing", "provider.use:meta", "provider.use:google_ads"],
    },
    EmployeeRole.FINANCE: {
        "system_prompt_template": "finance_prompt.j2",
        "default_skills": ["financial_analysis", "budget_planning", "expense_tracking", "forecasting"],
        "default_model": "meta/llama-3.1-70b-instruct",
        "temperature": 0.1,
        "default_permissions": ["skill.execute:finance", "data.read:financial"],
    },
    EmployeeRole.SUPPORT: {
        "system_prompt_template": "support_prompt.j2",
        "default_skills": ["ticket_management", "knowledge_base_search", "escalation_routing", "customer_communication"],
        "default_model": "meta/llama-3.1-8b-instruct",
        "temperature": 0.4,
        "default_permissions": ["skill.execute:support", "data.read:customer"],
    },
    EmployeeRole.DESIGNER: {
        "system_prompt_template": "designer_prompt.j2",
        "default_skills": ["visual_design", "brand_consistency", "ui_ux_review", "asset_generation"],
        "default_model": "meta/llama-3.1-8b-instruct",
        "temperature": 0.6,
        "default_permissions": ["skill.execute:design", "provider.use:image_generation"],
    },
    EmployeeRole.EDITOR: {
        "system_prompt_template": "editor_prompt.j2",
        "default_skills": ["content_editing", "proofreading", "seo_optimization", "tone_adjustment"],
        "default_model": "meta/llama-3.1-8b-instruct",
        "temperature": 0.3,
        "default_permissions": ["skill.execute:editing"],
    },
    EmployeeRole.SOCIAL_MEDIA: {
        "system_prompt_template": "social_media_prompt.j2",
        "default_skills": ["copywriting", "hashtag_research", "engagement_analysis", "community_management", "trend_monitoring"],
        "default_model": "meta/llama-3.1-8b-instruct",
        "temperature": 0.7,
        "default_permissions": ["skill.execute:social_media", "provider.use:meta", "provider.use:tiktok"],
    },
    EmployeeRole.HR: {
        "system_prompt_template": "hr_prompt.j2",
        "default_skills": ["recruitment", "onboarding", "performance_review", "policy_management"],
        "default_model": "meta/llama-3.1-8b-instruct",
        "temperature": 0.3,
        "default_permissions": ["skill.execute:hr", "data.read:employee"],
    },
    EmployeeRole.LEGAL: {
        "system_prompt_template": "legal_prompt.j2",
        "default_skills": ["contract_review", "compliance_check", "risk_assessment", "policy_drafting"],
        "default_model": "meta/llama-3.1-70b-instruct",
        "temperature": 0.1,
        "default_permissions": ["skill.execute:legal", "data.read:legal"],
    },
    EmployeeRole.DELIVERY: {
        "system_prompt_template": "delivery_prompt.j2",
        "default_skills": ["order_management", "logistics_coordination", "tracking", "customer_notifications"],
        "default_model": "meta/llama-3.1-8b-instruct",
        "temperature": 0.3,
        "default_permissions": ["skill.execute:delivery", "provider.use:tracking"],
    },
}


@dataclass
class Employee:
    """Employee runtime instance - wrappa um Agent com contexto de negócio."""
    employee_id: str
    profile: EmployeeProfile
    agent: Agent
    company_context: Optional[CompanyContext] = None
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_activity: Optional[datetime] = None


class EmployeeFactory:
    """
    Factory para criar Employees a partir de perfis.
    Integra com CompanyContextEngine, SkillModule, ProviderRegistry.
    """

    def __init__(
        self,
        agent_module: AgentModule,
        skill_module: SkillModule,
        provider_registry: ProviderRegistry,
        company_context_engine: CompanyContextEngine
    ):
        self.agent_module = agent_module
        self.skill_module = skill_module
        self.provider_registry = provider_registry
        self.company_context_engine = company_context_engine
        self.event_bus = get_event_bus()

    async def create(self, profile: EmployeeProfile) -> Employee:
        """Cria Employee completo com Agent, Skills, Providers e Company Context."""

        # 1. Resolver Company Context
        company_context = await self.company_context_engine.get_context_for_employee(
            employee_id=profile.employee_id,
            company_id=profile.company_id,
            role=profile.role.value,
            task=profile.specialization
        )

        # 2. Obter configuração do role
        role_config = ROLE_CONFIGS.get(profile.role, {})

        # 3. Build system prompt com company context
        system_prompt = self._build_system_prompt(
            profile=profile,
            role_config=role_config,
            company_context=company_context
        )

        # 4. Resolver tools a partir de skills
        tools = await self._resolve_tools_from_skills(profile.skills)

        # 5. Resolver providers permitidos
        provider_access = await self._resolve_provider_access(profile.permissions)

        # 6. Criar Agent
        agent = await self.agent_module.create_agent(
            agent_id=profile.employee_id,
            name=profile.name,
            role=AgentRole.SPECIALIST,
            system_prompt=system_prompt,
            model=profile.model or role_config.get("default_model", "meta/llama-3.1-8b-instruct"),
            temperature=profile.temperature if profile.temperature is not None else role_config.get("temperature", 0.7),
            max_tokens=profile.max_tokens,
            tools=tools,
            memory_scope=profile.memory_scope.value,
        )

        # 7. Criar Employee
        employee = Employee(
            employee_id=profile.employee_id,
            profile=profile,
            agent=agent,
            company_context=company_context
        )

        # 8. Registrar no AgentModule
        self.agent_module.agents[profile.employee_id] = agent

        # 9. Emit event
        await self.event_bus.publish(create_event(
            RuntimeEventType.EMPLOYEE_CREATED,
            f"employee:{profile.employee_id}",
            {
                "employee_id": profile.employee_id,
                "company_id": profile.company_id,
                "team_id": profile.team_id,
                "role": profile.role.value,
                "skills": profile.skills,
                "model": agent.model
            }
        ))

        return employee

    def _build_system_prompt(
        self,
        profile: EmployeeProfile,
        role_config: Dict,
        company_context: CompanyContext
    ) -> str:
        """Constrói system prompt combinando template + company context + profile."""

        # Template base (em produção: Jinja2 template)
        base_prompt = f"""Você é {profile.name}, um {profile.role.value} especializado em {profile.specialization}.

CONTEXTO DA EMPRESA:
- Empresa: {company_context.profile.name} ({company_context.profile.segment})
- Brand: {company_context.brand.name} - {company_context.brand.tagline}
- Tom de voz: {company_context.brand.voice_tone}
- Guidelines: {company_context.brand.guidelines}

PRODUTOS/SERVIÇOS:
{self._format_products(company_context.products)}

CANAIS:
{self._format_channels(company_context.channels)}

OBJETIVOS (OKRs/KPIs):
{self._format_goals(company_context.goals)}

CONHECIMENTO RELEVANTE:
{self._format_knowledge(company_context.knowledge)}

SUA ESPECIALIZAÇÃO:
{profile.specialization}

SKILLS DISPONÍVEIS: {', '.join(profile.skills)}

{profile.system_prompt_addendum}

INSTRUÇÕES:
- Sempre use o contexto da empresa para decisões
- Mantenha o tom de voz da brand ({company_context.brand.voice_tone})
- Use as skills disponíveis quando apropriado
- Se precisar de informação externa, use os providers autorizados
- Documente decisões importantes via tool calls
"""
        return base_prompt

    def _format_products(self, products: CompanyProducts) -> str:
        if not products.products and not products.services:
            return "  (nenhum cadastrado)"
        lines = []
        for p in products.products:
            lines.append(f"  - {p.get('name', 'Produto')}: {p.get('description', 'Sem descrição')} (R$ {p.get('price', 'N/A')})")
        for s in products.services:
            lines.append(f"  - {s.get('name', 'Serviço')}: {s.get('description', 'Sem descrição')} (R$ {s.get('price', 'N/A')}/{s.get('recurring', 'mês')})")
        return "\n".join(lines) if lines else "  (nenhum cadastrado)"

    def _format_channels(self, channels: CompanyChannels) -> str:
        active = []
        for field_name in ["instagram", "facebook", "tiktok", "whatsapp", "website", "linkedin", "youtube"]:
            ch = getattr(channels, field_name)
            if ch:
                active.append(f"  - {field_name}: @{ch.get('handle', ch.get('number', 'configurado'))}")
        return "\n".join(active) if active else "  (nenhum configurado)"

    def _format_goals(self, goals: CompanyGoals) -> str:
        lines = []
        for okr in goals.okrs:
            lines.append(f"  - Objetivo: {okr.get('objective', 'N/A')}")
            for kr in okr.get('key_results', []):
                lines.append(f"    KR: {kr.get('metric', 'N/A')} → Target: {kr.get('target', 'N/A')}")
        for kpi in goals.kpis:
            lines.append(f"  - KPI: {kpi.get('name', 'N/A')} = {kpi.get('current', 'N/A')} (target: {kpi.get('target', 'N/A')})")
        return "\n".join(lines) if lines else "  (nenhum definido)"

    def _format_knowledge(self, knowledge: List) -> str:
        if not knowledge:
            return "  (nenhum relevante)"
        lines = []
        for k in knowledge[:5]:  # Top 5
            lines.append(f"  - [{k.category}] {k.title}: {k.content[:200]}...")
        return "\n".join(lines)

    async def _resolve_tools_from_skills(self, skill_ids: List[str]) -> List[Dict]:
        """Converte skills em tools chamáveis pelo Agent."""
        tools = []
        for skill_id in skill_ids:
            skill = await self.skill_module.get_skill(skill_id)
            if skill:
                tool_def = {
                    "name": f"skill_{skill_id}",
                    "description": skill.description,
                    "parameters": skill.input_schema,
                    "skill_id": skill_id
                }
                tools.append(tool_def)
        return tools

    async def _resolve_provider_access(self, permissions: List[str]) -> Dict[str, List[str]]:
        """Mapeia permissões para providers e capabilities."""
        provider_access = {}
        for perm in permissions:
            if perm.startswith("provider.use:"):
                provider_id = perm.split(":")[1]
                if provider_id not in provider_access:
                    provider = self.provider_registry.providers.get(provider_id)
                    if provider:
                        provider_access[provider_id] = provider.capabilities
        return provider_access


class EmployeeRegistry:
    """Registry de Employees - gerencia lifecycle, busca, versionamento."""

    def __init__(self, factory: EmployeeFactory):
        self.factory = factory
        self.employees: Dict[str, Employee] = {}
        self.event_bus = get_event_bus()

    async def create_employee(self, profile: EmployeeProfile) -> Employee:
        if profile.employee_id in self.employees:
            raise ValueError(f"Employee {profile.employee_id} already exists")

        employee = await self.factory.create(profile)
        self.employees[profile.employee_id] = employee
        return employee

    async def get_employee(self, employee_id: str) -> Optional[Employee]:
        return self.employees.get(employee_id)

    async def update_employee(self, employee_id: str, updates: Dict[str, Any]) -> Employee:
        employee = self.employees.get(employee_id)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")

        # Update profile
        for key, value in updates.items():
            if hasattr(employee.profile, key):
                setattr(employee.profile, key, value)
        employee.profile.updated_at = datetime.utcnow()
        employee.profile.version = self._bump_version(employee.profile.version)

        # Recreate agent if config changed
        config_fields = {"model", "temperature", "max_tokens", "system_prompt_addendum", "skills", "permissions"}
        if any(f in updates for f in config_fields):
            new_employee = await self.factory.create(employee.profile)
            self.employees[employee_id] = new_employee
            employee = new_employee

        await self.event_bus.publish(create_event(
            RuntimeEventType.EMPLOYEE_PROFILE_UPDATED,
            f"employee:{employee_id}",
            {"employee_id": employee_id, "changes": updates, "version": employee.profile.version}
        ))

        return employee

    async def delete_employee(self, employee_id: str, hard: bool = False) -> bool:
        employee = self.employees.get(employee_id)
        if not employee:
            return False

        if hard:
            # Stop agent
            await self.factory.agent_module.stop_agent(employee_id)
            del self.employees[employee_id]

            await self.event_bus.publish(create_event(
                RuntimeEventType.EMPLOYEE_DELETED,
                f"employee:{employee_id}",
                {"employee_id": employee_id}
            ))
        else:
            employee.profile.enabled = False
            employee.profile.status = EmployeeStatus.INACTIVE
            await self.event_bus.publish(create_event(
                RuntimeEventType.EMPLOYEE_DEACTIVATED,
                f"employee:{employee_id}",
                {"employee_id": employee_id}
            ))

        return True

    async def list_employees(
        self,
        company_id: Optional[str] = None,
        team_id: Optional[str] = None,
        role: Optional[EmployeeRole] = None,
        enabled_only: bool = True
    ) -> List[Employee]:
        result = []
        for emp in self.employees.values():
            if enabled_only and not emp.profile.enabled:
                continue
            if company_id and emp.profile.company_id != company_id:
                continue
            if team_id and emp.profile.team_id != team_id:
                continue
            if role and emp.profile.role != role:
                continue
            result.append(emp)
        return result

    def _bump_version(self, version: str) -> str:
        parts = version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)


class EmployeeModule(RuntimeModule):
    """Module wrapper for Employee system."""

    metadata = ModuleMetadata(
        name="employee",
        version="1.0.0",
        description="Employee system - Agents with business context"
    )

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.agent_module: Optional[AgentModule] = None
        self.skill_module: Optional[SkillModule] = None
        self.provider_registry: Optional[ProviderRegistry] = None
        self.company_context_engine: Optional[CompanyContextEngine] = None
        self.factory: Optional[EmployeeFactory] = None
        self.registry: Optional[EmployeeRegistry] = None

    async def initialize(self, runtime, config: Dict[str, Any]) -> None:
        await super().initialize(runtime, config)
        self.agent_module = self.runtime.get_module("agent")
        self.skill_module = self.runtime.get_module("skill")
        self.provider_registry = self.runtime.get_module("provider")
        self.company_context_engine = self.runtime.get_module("company_context")

        if not self.provider_registry or not self.provider_registry.registry:
            # Provider registry might not be fully initialized, wait for it
            pass
        if not self.company_context_engine or not self.company_context_engine.engine:
            pass

        self.factory = EmployeeFactory(
            self.agent_module,
            self.skill_module,
            self.provider_registry.registry if self.provider_registry else None,
            self.company_context_engine.engine if self.company_context_engine else None
        )
        self.registry = EmployeeRegistry(self.factory)

    async def start(self) -> None:
        await super().start()
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            RuntimeEventType.MODULE_STARTED,
            "employee",
            {"module": self.name, "version": self.metadata.version}
        ))

    async def stop(self) -> None:
        # Stop all employees
        for emp in self.registry.employees.values():
            await self.agent_module.stop_agent(emp.employee_id)
        await super().stop()

    async def cleanup(self) -> None:
        self.factory = None
        self.registry = None
        await super().cleanup()

    async def health_check(self):
        from runtime.base.module import ModuleHealth, ModuleState
        return ModuleHealth(
            module=self.name,
            state=ModuleState.RUNNING,
            checks={
                "registry": "ok",
                "factory": "ok",
                "employees_count": str(len(self.registry.employees))
            },
            timestamp=datetime.utcnow()
        )

    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "create_employee": self.registry.create_employee,
            "get_employee": self.registry.get_employee,
            "update_employee": self.registry.update_employee,
            "delete_employee": self.registry.delete_employee,
            "list_employees": self.registry.list_employees,
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: {operation}")
        return await ops[operation](**params)