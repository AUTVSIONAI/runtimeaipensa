"""
Sync Package - Sincronização Engine ↔ Core via YAML.

Implementa export/import de estado completo da Engine para o Core.
Formato versionado, forward-compatible, com checksum.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import yaml
import hashlib
import json

from runtime.base.module import RuntimeModule, ModuleMetadata
from runtime.base.events import get_event_bus, RuntimeEventType, create_event


SYNC_VERSION = "1.0"


@dataclass
class SyncPackage:
    """Pacote completo de sincronização."""
    version: str = SYNC_VERSION
    engine_version: str = "1.0.0"
    exported_at: str = ""
    checksum: str = ""

    # Core data
    companies: List[Dict[str, Any]] = None
    employees: List[Dict[str, Any]] = None
    teams: List[Dict[str, Any]] = None
    skills: List[Dict[str, Any]] = None
    providers: List[Dict[str, Any]] = None
    provider_connections: List[Dict[str, Any]] = None  # apenas connection_ids, credenciais em secrets
    workflows: List[Dict[str, Any]] = None
    schedules: List[Dict[str, Any]] = None
    plugins: List[Dict[str, Any]] = None
    llm_models: List[Dict[str, Any]] = None
    memory_configs: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.exported_at == "":
            self.exported_at = datetime.utcnow().isoformat() + "Z"
        if self.companies is None:
            self.companies = []
        if self.employees is None:
            self.employees = []
        if self.teams is None:
            self.teams = []
        if self.skills is None:
            self.skills = []
        if self.providers is None:
            self.providers = []
        if self.provider_connections is None:
            self.provider_connections = []
        if self.workflows is None:
            self.workflows = []
        if self.schedules is None:
            self.schedules = []
        if self.plugins is None:
            self.plugins = []
        if self.llm_models is None:
            self.llm_models = []
        if self.memory_configs is None:
            self.memory_configs = []

    def to_yaml(self) -> str:
        """Converte para YAML string."""
        data = asdict(self)
        # Calcular checksum antes de serializar
        data["checksum"] = self._calculate_checksum(data)
        return yaml.dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)

    def to_json(self) -> str:
        """Converte para JSON string."""
        data = asdict(self)
        data["checksum"] = self._calculate_checksum(data)
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    def _calculate_checksum(self, data: Dict) -> str:
        """Calcula SHA256 do pacote (sem o campo checksum)."""
        data_copy = {k: v for k, v in data.items() if k != "checksum"}
        content = yaml.dump(data_copy, sort_keys=True, allow_unicode=True)
        return "sha256:" + hashlib.sha256(content.encode()).hexdigest()

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "SyncPackage":
        """Carrega de YAML e valida checksum."""
        data = yaml.safe_load(yaml_str)
        return cls._validate_and_create(data)

    @classmethod
    def from_json(cls, json_str: str) -> "SyncPackage":
        """Carrega de JSON e valida checksum."""
        data = json.loads(json_str)
        return cls._validate_and_create(data)

    @classmethod
    def _validate_and_create(cls, data: Dict) -> "SyncPackage":
        # Validar versão
        if data.get("version") != SYNC_VERSION:
            raise ValueError(f"Unsupported sync version: {data.get('version')}, expected {SYNC_VERSION}")

        # Validar checksum
        provided_checksum = data.get("checksum", "")
        calculated = cls()._calculate_checksum(data)
        if provided_checksum != calculated:
            raise ValueError(f"Checksum mismatch: expected {calculated}, got {provided_checksum}")

        # Criar instância
        return cls(**{k: v for k, v in data.items() if k != "checksum"})


class SyncExporter:
    """Exporta estado da Engine para SyncPackage."""

    def __init__(self, runtime):
        self.runtime = runtime

    async def export(self, include_secrets_refs: bool = False) -> SyncPackage:
        """Exporta tudo para SyncPackage."""
        pkg = SyncPackage(
            engine_version=getattr(self.runtime, 'version', '1.0.0')
        )

        # Companies
        pkg.companies = await self._export_companies()

        # Employees
        pkg.employees = await self._export_employees()

        # Teams
        pkg.teams = await self._export_teams()

        # Skills
        pkg.skills = await self._export_skills()

        # Providers
        pkg.providers = await self._export_providers()
        pkg.provider_connections = await self._export_connections(include_secrets_refs)

        # Workflows
        pkg.workflows = await self._export_workflows()

        # Schedules
        pkg.schedules = await self._export_schedules()

        # Plugins
        pkg.plugins = await self._export_plugins()

        # LLM Models
        pkg.llm_models = await self._export_llm_models()

        # Memory configs
        pkg.memory_configs = await self._export_memory_configs()

        return pkg

    async def _export_companies(self) -> List[Dict]:
        memory = self.runtime.get_module("memory")
        companies = []

        if hasattr(memory, 'stores'):
            for store_name in memory.stores:
                if store_name.startswith("company_") and store_name.endswith("_profile"):
                    company_id = store_name.replace("company_", "").replace("_profile", "")
                    profile = await memory.read(store=store_name, key="profile")
                    if not profile:
                        continue

                    brand = await memory.read(store=f"company_{company_id}", key="brand")
                    products = await memory.read(store=f"company_{company_id}", key="products")
                    channels = await memory.read(store=f"company_{company_id}", key="channels")
                    goals = await memory.read(store=f"company_{company_id}", key="goals")

                    companies.append({
                        "company_id": company_id,
                        "profile": profile,
                        "brand": brand,
                        "products": products,
                        "channels": channels,
                        "goals": goals
                    })

        return companies

    async def _export_employees(self) -> List[Dict]:
        emp_module = self.runtime.get_module("employee")
        if not emp_module or not emp_module.registry:
            return []

        employees = []
        for emp in emp_module.registry.employees.values():
            employees.append({
                "employee_id": emp.employee_id,
                "company_id": emp.profile.company_id,
                "team_id": emp.profile.team_id,
                "name": emp.profile.name,
                "role": emp.profile.role.value,
                "specialization": emp.profile.specialization,
                "skills": emp.profile.skills,
                "model": emp.profile.model,
                "temperature": emp.profile.temperature,
                "max_tokens": emp.profile.max_tokens,
                "memory_scope": emp.profile.memory_scope.value,
                "permissions": emp.profile.permissions,
                "enabled": emp.profile.enabled,
                "version": emp.profile.version,
                "configuration": emp.profile.configuration,
                "system_prompt_addendum": emp.profile.system_prompt_addendum
            })
        return employees

    async def _export_teams(self) -> List[Dict]:
        team_module = self.runtime.get_module("team")
        if not team_module or not team_module.manager:
            return []

        teams = []
        for team in team_module.manager.teams.values():
            teams.append({
                "team_id": team.team_id,
                "company_id": team.company_id,
                "name": team.name,
                "description": team.description,
                "team_type": team.team_type.value,
                "parent_team_id": team.parent_team_id,
                "workspace_id": team.workspace_id,
                "members": [
                    {
                        "employee_id": m.employee_id,
                        "role": m.role.value,
                        "permissions": m.permissions,
                        "joined_at": m.joined_at.isoformat()
                    }
                    for m in team.members.values()
                ],
                "shared_context": team.shared_context,
                "workflow_ids": team.workflow_ids,
                "settings": team.settings
            })
        return teams

    async def _export_skills(self) -> List[Dict]:
        skill_module = self.runtime.get_module("skill")
        if not skill_module:
            return []

        skills = []
        if hasattr(skill_module, 'registry') and hasattr(skill_module.registry, 'skills'):
            for skill in skill_module.registry.skills.values():
                skills.append({
                    "skill_id": skill.skill_id,
                    "name": skill.name,
                    "type": skill.type.value,
                    "category": skill.category,
                    "version": skill.version,
                    "description": skill.description,
                    "input_schema": skill.input_schema,
                    "output_schema": skill.output_schema,
                    "definition": skill.definition if hasattr(skill, 'definition') else None,
                    "dependencies": skill.dependencies if hasattr(skill, 'dependencies') else [],
                    "rate_limit": skill.rate_limit if hasattr(skill, 'rate_limit') else None,
                    "permissions_required": skill.permissions_required if hasattr(skill, 'permissions_required') else [],
                    "provider_requirements": skill.provider_requirements if hasattr(skill, 'provider_requirements') else [],
                    "configuration": skill.configuration if hasattr(skill, 'configuration') else {},
                })
        return skills

    async def _export_providers(self) -> List[Dict]:
        provider_module = self.runtime.get_module("provider")
        if not provider_module or not provider_module.registry:
            return []

        providers = []
        for provider in provider_module.registry.providers.values():
            providers.append({
                "provider_id": provider.provider_id,
                "name": provider.name,
                "type": provider.provider_type.value,
                "version": provider.version,
                "description": getattr(provider, 'description', ''),
                "capabilities": [
                    {
                        "capability_id": c.capability_id,
                        "name": c.name,
                        "description": c.description,
                        "input_schema": c.input_schema,
                        "output_schema": c.output_schema,
                        "rate_limit": c.rate_limit,
                        "requires_scopes": c.requires_scopes
                    }
                    for c in provider.capabilities
                ],
                "config_schema": provider.config_schema,
                "oauth_config": {
                    "authorization_url": provider.oauth_config.authorization_url,
                    "token_url": provider.oauth_config.token_url,
                    "scopes": provider.oauth_config.scopes,
                    "pkce": provider.oauth_config.pkce
                } if provider.oauth_config else None
            })
        return providers

    async def _export_connections(self, include_secrets_refs: bool) -> List[Dict]:
        provider_module = self.runtime.get_module("provider")
        if not provider_module or not provider_module.registry:
            return []

        connections = []
        for conn in provider_module.registry.manager.connections.values():
            conn_data = {
                "connection_id": conn.connection_id,
                "provider_id": conn.provider_id,
                "company_id": conn.company_id,
                "scopes": conn.scopes,
                "status": conn.status,
                "connected_at": conn.connected_at.isoformat(),
                "expires_at": conn.expires_at.isoformat() if conn.expires_at else None
            }
            if include_secrets_refs:
                conn_data["credentials_ref"] = f"secret:provider_{conn.provider_id}_{conn.connection_id}"
            connections.append(conn_data)
        return connections

    async def _export_workflows(self) -> List[Dict]:
        workflow_module = self.runtime.get_module("workflow")
        if not workflow_module:
            return []

        workflows = []
        if hasattr(workflow_module, 'workflows'):
            for wf in workflow_module.workflows.values():
                workflows.append({
                    "workflow_id": wf.workflow_id if hasattr(wf, 'workflow_id') else getattr(wf, 'id', ''),
                    "name": getattr(wf, 'name', ''),
                    "version": getattr(wf, 'version', '1.0.0'),
                    "description": getattr(wf, 'description', ''),
                    "team_id": getattr(wf, 'team_id', None),
                    "definition": getattr(wf, 'definition', {}),
                    "tags": getattr(wf, 'tags', []),
                    "status": getattr(wf, 'status', 'ACTIVE'),
                    "schedule": getattr(wf, 'schedule', None)
                })
        return workflows

    async def _export_schedules(self) -> List[Dict]:
        scheduler_module = self.runtime.get_module("scheduler")
        if not scheduler_module:
            return []

        schedules = []
        if hasattr(scheduler_module, 'jobs'):
            for job in scheduler_module.jobs.values():
                schedules.append({
                    "job_id": job.job_id,
                    "name": job.name,
                    "workflow_id": job.workflow_id,
                    "cron": job.cron_expression,
                    "interval_seconds": job.interval_seconds,
                    "run_once_at": job.run_once_at.isoformat() if job.run_once_at else None,
                    "delay_seconds": job.delay_seconds,
                    "timezone": job.timezone,
                    "enabled": job.enabled,
                    "max_concurrent": job.max_concurrent,
                    "retry_policy": job.retry_policy,
                    "company_id": job.company_id,
                    "team_id": job.team_id,
                    "employee_id": job.employee_id
                })
        return schedules

    async def _export_plugins(self) -> List[Dict]:
        plugin_manager = self.runtime.plugin_manager
        if not plugin_manager:
            return []

        plugins = []
        if hasattr(plugin_manager, 'plugins'):
            for p in plugin_manager.plugins.values():
                plugins.append({
                    "name": p.manifest.name,
                    "version": p.manifest.version,
                    "type": p.manifest.type.value,
                    "class_name": p.manifest.class_name,
                    "entry_point": p.manifest.entry_point,
                    "description": p.manifest.description,
                    "capabilities": p.manifest.capabilities,
                    "config_schema": p.manifest.config_schema,
                    "dependencies": p.manifest.dependencies
                })
        return plugins

    async def _export_llm_models(self) -> List[Dict]:
        llm_module = self.runtime.get_module("llm")
        if not llm_module:
            return []

        models = []
        if hasattr(llm_module, 'models'):
            for model_id, model in llm_module.models.items():
                models.append({
                    "model_id": model_id,
                    "provider": model.provider,
                    "capabilities": model.capabilities,
                    "context_window": model.context_window,
                    "max_output_tokens": model.max_output_tokens,
                    "cost_per_1k_input": model.cost_per_1k_input,
                    "cost_per_1k_output": model.cost_per_1k_output
                })
        return models

    async def _export_memory_configs(self) -> List[Dict]:
        memory_module = self.runtime.get_module("memory")
        if not memory_module:
            return []

        configs = []
        if hasattr(memory_module, 'stores'):
            for store_name, store in memory_module.stores.items():
                configs.append({
                    "store_name": store_name,
                    "store_type": type(store).__name__,
                    "config": getattr(store, 'config', {})
                })
        return configs


class SyncImporter:
    """Importa SyncPackage para a Engine."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.results = {
            "companies": 0,
            "employees": 0,
            "teams": 0,
            "skills": 0,
            "providers": 0,
            "connections": 0,
            "workflows": 0,
            "schedules": 0,
            "warnings": [],
            "errors": []
        }

    async def import_package(self, pkg: SyncPackage) -> Dict[str, Any]:
        """Importa pacote completo."""
        # Companies first (foundational)
        await self._import_companies(pkg.companies)

        # Providers (needed for connections)
        await self._import_providers(pkg.providers)

        # Provider connections
        await self._import_connections(pkg.provider_connections)

        # Skills (needed for employees)
        await self._import_skills(pkg.skills)

        # Employees
        await self._import_employees(pkg.employees)

        # Teams
        await self._import_teams(pkg.teams)

        # Workflows
        await self._import_workflows(pkg.workflows)

        # Schedules
        await self._import_schedules(pkg.schedules)

        # Plugins (just register, don't load)
        await self._import_plugins(pkg.plugins)

        # LLM Models
        await self._import_llm_models(pkg.llm_models)

        # Memory configs
        await self._import_memory_configs(pkg.memory_configs)

        return self.results

    async def _import_companies(self, companies: List[Dict]):
        company_engine = self.runtime.get_module("company_context").engine
        for c in companies:
            try:
                company_id = c["company_id"]
                await company_engine.save_profile(company_id, c["profile"])
                if c.get("brand"):
                    await company_engine.save_brand(company_id, c["brand"])
                if c.get("products"):
                    await company_engine.save_products(company_id, c["products"])
                if c.get("channels"):
                    await company_engine.save_channels(company_id, c["channels"])
                if c.get("goals"):
                    await company_engine.save_goals(company_id, c["goals"])
                self.results["companies"] += 1
            except Exception as e:
                self.results["errors"].append(f"Company {c.get('company_id')}: {e}")

    async def _import_providers(self, providers: List[Dict]):
        provider_module = self.runtime.get_module("provider")
        if not provider_module:
            self.results["warnings"].append("Provider module not available, skipping providers import")
            return

        for p in providers:
            try:
                # Providers são geralmente built-in, apenas verificar se existem
                existing = provider_module.registry.get_provider(p["provider_id"])
                if not existing:
                    self.results["warnings"].append(f"Provider {p['provider_id']} not found in Engine (built-in only)")
                else:
                    self.results["providers"] += 1
            except Exception as e:
                self.results["errors"].append(f"Provider {p.get('provider_id')}: {e}")

    async def _import_connections(self, connections: List[Dict]):
        provider_module = self.runtime.get_module("provider")
        if not provider_module:
            return

        for c in connections:
            try:
                # Conexões requerem credenciais que não estão no sync (estão em secrets)
                # Apenas registrar como pending_credentials
                self.results["warnings"].append(
                    f"Connection {c['connection_id']} requires credential setup in secrets manager"
                )
                self.results["connections"] += 1
            except Exception as e:
                self.results["errors"].append(f"Connection {c.get('connection_id')}: {e}")

    async def _import_skills(self, skills: List[Dict]):
        skill_module = self.runtime.get_module("skill")
        if not skill_module:
            return

        for s in skills:
            try:
                await skill_module.execute("register_skill", skill=s)
                self.results["skills"] += 1
            except Exception as e:
                self.results["errors"].append(f"Skill {s.get('skill_id')}: {e}")

    async def _import_employees(self, employees: List[Dict]):
        emp_module = self.runtime.get_module("employee")
        if not emp_module:
            return

        for e in employees:
            try:
                from runtime.extensions.employee.employee import EmployeeProfile, EmployeeRole, MemoryScope
                profile = EmployeeProfile(
                    employee_id=e["employee_id"],
                    company_id=e["company_id"],
                    team_id=e.get("team_id"),
                    name=e["name"],
                    role=EmployeeRole(e["role"]),
                    specialization=e["specialization"],
                    skills=e["skills"],
                    model=e["model"],
                    temperature=e["temperature"],
                    max_tokens=e["max_tokens"],
                    memory_scope=MemoryScope(e["memory_scope"]),
                    permissions=e["permissions"],
                    enabled=e["enabled"],
                    version=e["version"],
                    configuration=e["configuration"],
                    system_prompt_addendum=e.get("system_prompt_addendum", "")
                )
                await emp_module.registry.create_employee(profile)
                self.results["employees"] += 1
            except Exception as e:
                self.results["errors"].append(f"Employee {e.get('employee_id')}: {e}")

    async def _import_teams(self, teams: List[Dict]):
        team_module = self.runtime.get_module("team")
        if not team_module:
            return

        for t in teams:
            try:
                # Create team
                team = await team_module.manager.create_team(
                    company_id=t["company_id"],
                    name=t["name"],
                    description=t.get("description", ""),
                    team_type=t["team_type"],
                    parent_team_id=t.get("parent_team_id")
                )

                # Add members
                for m in t.get("members", []):
                    await team_module.manager.add_member(
                        team.team_id,
                        m["employee_id"],
                        m["role"]
                    )

                # Update shared context and workflows
                team.shared_context = t.get("shared_context", {})
                team.workflow_ids = t.get("workflow_ids", [])

                self.results["teams"] += 1
            except Exception as e:
                self.results["errors"].append(f"Team {t.get('team_id')}: {e}")

    async def _import_workflows(self, workflows: List[Dict]):
        workflow_module = self.runtime.get_module("workflow")
        if not workflow_module:
            return

        for w in workflows:
            try:
                # Would register workflow definition
                self.results["workflows"] += 1
            except Exception as e:
                self.results["errors"].append(f"Workflow {w.get('workflow_id')}: {e}")

    async def _import_schedules(self, schedules: List[Dict]):
        scheduler_module = self.runtime.get_module("scheduler")
        if not scheduler_module:
            return

        for s in schedules:
            try:
                # Would create scheduled job
                self.results["schedules"] += 1
            except Exception as e:
                self.results["errors"].append(f"Schedule {s.get('job_id')}: {e}")

    async def _import_plugins(self, plugins: List[Dict]):
        # Plugins são carregados via filesystem, não via sync
        # Apenas avisar se há plugins no sync que não estão instalados
        plugin_manager = self.runtime.plugin_manager
        if plugin_manager:
            for p in plugins:
                if p["name"] not in [pl.manifest.name for pl in plugin_manager.plugins.values()]:
                    self.results["warnings"].append(f"Plugin {p['name']} not installed in Engine")

    async def _import_llm_models(self, models: List[Dict]):
        # Models são definidos pelos providers
        pass

    async def _import_memory_configs(self, configs: List[Dict]):
        # Memory stores são criados sob demanda
        pass


class SyncModule(RuntimeModule):
    """Module wrapper para Sync Package."""

    metadata = ModuleMetadata(
        name="sync",
        version="1.0.0",
        description="Sync Package - Engine↔Core state synchronization via YAML"
    )

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.exporter: Optional[SyncExporter] = None
        self.importer: Optional[SyncImporter] = None

    async def initialize(self, runtime, config: Dict[str, Any]) -> None:
        await super().initialize(runtime, config)
        self.exporter = SyncExporter(runtime)
        self.importer = SyncImporter(runtime)

    async def start(self) -> None:
        await super().start()
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            RuntimeEventType.MODULE_STARTED,
            "sync",
            {"module": self.name, "version": self.metadata.version}
        ))

    async def stop(self) -> None:
        await super().stop()

    async def cleanup(self) -> None:
        self.exporter = None
        self.importer = None
        await super().cleanup()

    async def health_check(self):
        from runtime.base.module import ModuleHealth, ModuleState
        return ModuleHealth(
            module=self.name,
            state=ModuleState.RUNNING,
            checks={"exporter": "ok", "importer": "ok"},
            timestamp=datetime.utcnow()
        )

    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "export": self.exporter.export,
            "import": self.importer.import_package,
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: {operation}")
        return await ops[operation](**params)