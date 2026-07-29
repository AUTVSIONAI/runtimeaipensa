# 🏗️ ENGINE_ARCHITECTURE.md - Arquitetura Completa da AIPENSA Engine

**Versão:** 1.0  
**Baseado em:** ENGINE_SPEC.md (Constituição)  
**Data:** 28 Julho 2026  

---

## 📐 VISÃO GERAL DA ARQUITETURA

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              AIPENSA CORE (Produto Final)                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │  CRM    │ │Delivery │ │Finance  │ │Clinics  │ │Market   │ │Restaurant│ ...       │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘            │
└───────┼────────────┼────────────┼────────────┼────────────┼────────┼────────────────┘
        │            │            │            │            │
        │   HTTP/REST API v1      │   WebSocket (Events)      │   Sync Package (YAML)  │
        │            │            │            │            │            │
        ▼            ▼            ▼            ▼            ▼            ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                        AIPENSA ENGINE (Runtime - ESTA ARQUITETURA)                   │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │                        LAYER 5: EXTERNAL INTERFACES                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │  │
│  │  │  REST API   │  │  WebSocket  │  │   GraphQL   │  │    CLI      │            │  │
│  │  │  (FastAPI)  │  │  (Events)   │  │  (Opcional) │  │  (Typer)    │            │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │                        LAYER 4: ORCHESTRATION                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │  │
│  │  │  Workflow   │  │  Scheduler  │  │    Queue    │  │  Planning   │            │  │
│  │  │  Module     │  │  Module     │  │  Module     │  │  Module     │            │  │
│  │  │  (DAG Exec) │  │  (Cron/Int) │  │ (Priority/  │  │  (LLM-based)│            │  │
│  │  │             │  │             │  │  DLQ/Backpr)│  │             │            │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │  │
│  └─────────┼────────────────┼────────────────┼────────────────┼────────────────────┘  │
│            │                │                │                │                       │
│  ┌─────────▼────────────────▼────────────────▼────────────────▼────────────────┐    │
│  │                    LAYER 3: INTELLIGENCE                                     │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │    │
│  │  │   Agent     │  │Conversation │  │    Skill    │  │    LLM      │          │    │
│  │  │   Module    │  │   Module    │  │   Module    │  │   Module    │          │    │
│  │  │             │  │  (Streaming)│  │ (Registry/  │  │             │          │    │
│  │  │ (Lifecycle/ │  │  Tool Calls) │  │  Composite/ │  │ (91 Models/ │          │    │
│  │  │  Msg Pass)  │  │             │  │  Marketplace)│  │ Multi-Prov) │          │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │    │
│  │         │                │                │                │                   │    │
│  │  ┌──────▼──────┐ ┌───────▼───────┐ ┌──────▼──────┐ ┌───────▼───────┐          │    │
│  │  │ Provider    │ │  Employee   │ │  Team       │ │ Company       │          │    │
│  │  │  Registry   │ │  Factory    │ │  Manager    │ │ Context       │          │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └───────────────┘          │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │                        LAYER 2: CAPABILITIES                                   │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │  │
│  │  │ Browser │ │Execution│ │ FileSys │ │ Network │ │ Docker  │ │   MCP   │      │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘      │  │
│  └───────┼───────────┼───────────┼───────────┼───────────┼───────────┼────────────┘  │
│          │           │           │           │           │           │               │
│  ┌───────▼───────────▼───────────▼───────────▼───────────▼───────────▼────────────┐  │
│  │                      LAYER 1: FOUNDATION                                       │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │  │
│  │  │ Memory   │ │ Storage  │ │  Auth    │ │Notify    │ │Workspace │             │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘             │  │
│  └───────┼────────────┼────────────┼────────────┼────────────┼────────────────────┘  │
│          │            │            │            │            │                       │
│  ┌───────▼────────────▼────────────▼────────────▼────────────▼────────────────┐    │
│  │                        LAYER 0: KERNEL                                       │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │    │
│  │  │  Runtime    │ │  Module     │ │   Event     │ │  Plugin     │            │    │
│  │  │  (Factory)  │ │  Registry   │ │    Bus      │ │  Manager    │            │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                       │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 KERNEL (Layer 0) - CORAÇÃO DA ENGINE

### Runtime (Factory & Lifecycle)

```python
# runtime/runtime.py
class Runtime:
    """Factory e orquestrador principal da Engine."""
    
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.module_registry = ModuleRegistry()
        self.event_bus = get_event_bus()
        self.plugin_manager = PluginManager()
        self.module_states: Dict[str, ModuleState] = {}
        
    async def initialize(self) -> None:
        # 1. Carregar plugins auto-descobertos
        await self.plugin_manager.discover_and_load()
        
        # 2. Instanciar módulos builtin + plugin modules
        for module_class in BUILTIN_MODULES + self.plugin_manager.get_runtime_modules():
            module = module_class(self)
            await self.module_registry.register(module)
            
        # 3. Resolver dependências e ordenar inicialização
        init_order = self.module_registry.resolve_dependencies()
        
        # 4. Inicializar em ordem topológica
        for module_name in init_order:
            module = self.module_registry.get(module_name)
            await module.initialize(self)
            self.module_states[module_name] = ModuleState.INITIALIZING
            
        # 5. Start todos módulos
        for module_name in init_order:
            module = self.module_registry.get(module_name)
            await module.start()
            self.module_states[module_name] = ModuleState.RUNNING
            
        # 6. Start EventBus
        await self.event_bus.start()
        
        await self.event_bus.emit(RuntimeEvent(
            event_type=RuntimeEventType.RUNTIME_STARTED,
            source="runtime",
            payload={"version": __version__}
        ))
```

### ModuleRegistry (Dependency Resolution)

```python
# runtime/base/module.py
class ModuleRegistry:
    """Registry com resolução topológica de dependências."""
    
    def __init__(self):
        self._modules: Dict[str, RuntimeModule] = {}
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
    def register(self, module: RuntimeModule) -> None:
        name = module.name
        if name in self._modules:
            raise ModuleAlreadyRegistered(name)
        self._modules[name] = module
        # Declared dependencies
        for dep in module.metadata.dependencies:
            self._dependency_graph[name].add(dep)
            
    def resolve_dependencies(self) -> List[str]:
        """Kahn's algorithm para ordenação topológica."""
        in_degree = {name: 0 for name in self._modules}
        for name, deps in self._dependency_graph.items():
            for dep in deps:
                in_degree[dep] += 1
                
        queue = deque([name for name, deg in in_degree.items() if deg == 0])
        result = []
        
        while queue:
            name = queue.popleft()
            result.append(name)
            for dependent in self._get_dependents(name):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    
        if len(result) != len(self._modules):
            raise CircularDependencyError(self._find_cycle())
            
        return result
```

### EventBus (Source of Truth)

```python
# runtime/events/__init__.py
class RuntimeEventBus:
    """Event Bus Enterprise-grade com 155+ tipos de evento."""
    
    def __init__(self):
        self._handlers: Dict[RuntimeEventType, List[EventHandler]] = defaultdict(list)
        self._global_handlers: List[EventHandler] = []
        self._event_history: deque[RuntimeEvent] = deque(maxlen=10000)
        self._filters: List[EventFilter] = []
        self._dlq: deque[RuntimeEvent] = deque(maxlen=1000)
        self._priority_queues: Dict[EventPriority, asyncio.Queue] = {
            p: asyncio.Queue() for p in EventPriority
        }
        self._processing_task: Optional[asyncio.Task] = None
        
    def subscribe(self, event_type: RuntimeEventType, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)
        
    def subscribe_global(self, handler: EventHandler) -> None:
        self._global_handlers.append(handler)
        
    async def emit(self, event: RuntimeEvent) -> None:
        # 1. Correlation/Causation tracking
        event.correlation_id = event.correlation_id or generate_correlation_id()
        event.causation_id = event.causation_id or event.event_id
        event.timestamp = datetime.utcnow()
        
        # 2. Apply filters
        if not all(f.matches(event) for f in self._filters):
            return
            
        # 3. Queue by priority
        await self._priority_queues[event.priority].put(event)
        
    async def _process_events(self) -> None:
        while True:
            # Process by priority (CRITICAL first)
            for priority in [EventPriority.CRITICAL, EventPriority.HIGH, 
                           EventPriority.NORMAL, EventPriority.LOW]:
                try:
                    event = await asyncio.wait_for(
                        self._priority_queues[priority].get(), 
                        timeout=0.01
                    )
                    await self._dispatch(event)
                except asyncio.TimeoutError:
                    continue
                    
    async def _dispatch(self, event: RuntimeEvent) -> None:
        # 1. Store in history
        self._event_history.append(event)
        
        # 2. Global handlers
        for handler in self._global_handlers:
            await self._safe_call(handler, event)
            
        # 3. Type-specific handlers
        for handler in self._handlers[event.event_type]:
            await self._safe_call(handler, event)
            
        # 4. WebSocket broadcast (async, fire-and-forget)
        asyncio.create_task(self._broadcast_ws(event))
```

### PluginManager (Auto-discovery & Lifecycle)

```python
# runtime/plugins/base.py
class PluginManager:
    """Gerencia 11 tipos de plugins com auto-discovery."""
    
    PLUGIN_DIRS = {
        PluginType.TOOL: "runtime/plugins/tools",
        PluginType.MCP: "runtime/plugins/mcp", 
        PluginType.BROWSER: "runtime/plugins/browser",
        PluginType.RUNTIME: "runtime/plugins/runtime",
        PluginType.SANDBOX: "runtime/plugins/sandbox",
        PluginType.MEMORY: "runtime/plugins/memory",
        PluginType.LLM: "runtime/plugins/llm",
        PluginType.AUTH: "runtime/plugins/auth",
        PluginType.STORAGE: "runtime/plugins/storage",
        PluginType.NETWORK: "runtime/plugins/network",
        PluginType.CUSTOM: "runtime/plugins/custom",
    }
    
    async def discover_and_load(self) -> List[PluginInstance]:
        instances = []
        for plugin_type, dir_path in self.PLUGIN_DIRS.items():
            for plugin_dir in Path(dir_path).iterdir():
                if plugin_dir.is_dir() and (plugin_dir / "plugin.yaml").exists():
                    instance = await self._load_plugin(plugin_dir, plugin_type)
                    instances.append(instance)
        return instances
        
    async def _load_plugin(self, path: Path, ptype: PluginType) -> PluginInstance:
        # 1. Read manifest
        manifest = PluginManifest.parse_yaml(path / "plugin.yaml")
        
        # 2. Validate schema
        self._validate_manifest(manifest)
        
        # 3. Load entry point
        spec = importlib.util.spec_from_file_location(
            manifest.name, path / manifest.entry_point
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 4. Instantiate
        plugin_class = getattr(module, manifest.class_name)
        instance = plugin_class(manifest.config)
        
        # 5. Initialize
        await instance.initialize(self.runtime)
        
        return PluginInstance(
            manifest=manifest,
            instance=instance,
            status=PluginStatus.LOADED,
            plugin_type=ptype
        )
```

---

## 🧠 INTELLIGENCE LAYER (Layer 3) - CAMADA DE INTELIGÊNCIA

### AgentModule → Employee Factory

```python
# runtime/agent/module.py
class AgentModule(RuntimeModule):
    """Gerencia lifecycle de Agents/Employees."""
    
    name = "agent"
    version = "1.0.0"
    
    def __init__(self, runtime: Runtime):
        super().__init__(runtime)
        self.agents: Dict[str, Agent] = {}
        self.employee_factory = EmployeeFactory(self)
        
    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "create_agent": self._create_agent,
            "create_employee": self.employee_factory.create,
            "start_agent": self._start_agent,
            "stop_agent": self._stop_agent,
            "send_message": self._send_message,
            "assign_task": self._assign_task,
            "get_agent_state": self._get_state,
        }
        if operation not in ops:
            raise UnknownOperation(f"Agent operation '{operation}' not found")
        return await ops[operation](**params)

class EmployeeFactory:
    """Cria Employees (Agents especializados) a partir de perfis."""
    
    EMPLOYEE_ROLES = {
        EmployeeRole.CEO: {
            "system_prompt_template": "ceo_prompt.j2",
            "default_skills": ["strategic_planning", "kpi_analysis", "team_management"],
            "default_model": "meta/llama-3.1-70b-instruct",
            "temperature": 0.3,
        },
        EmployeeRole.MARKETING: {
            "system_prompt_template": "marketing_prompt.j2", 
            "default_skills": ["copywriting", "campaign_management", "seo_analysis"],
            "default_model": "meta/llama-3.1-8b-instruct",
            "temperature": 0.7,
        },
        EmployeeRole.FINANCE: {
            "system_prompt_template": "finance_prompt.j2",
            "default_skills": ["financial_analysis", "budget_planning", "expense_tracking"],
            "default_model": "meta/llama-3.1-70b-instruct", 
            "temperature": 0.1,
        },
        # ... outros 7 roles
    }
    
    async def create(self, profile: EmployeeProfile) -> Employee:
        role_config = self.EMPLOYEE_ROLES[profile.role]
        
        # Resolve Company Context
        company_context = await self.company_resolver.resolve_for_employee(profile.employee_id)
        
        # Build system prompt with context
        system_prompt = self._render_prompt(
            role_config["system_prompt_template"],
            employee=profile,
            company=company_context
        )
        
        # Create Agent with Employee metadata
        agent = Agent(
            agent_id=profile.employee_id,
            name=profile.name,
            role=AgentRole.SPECIALIST,  # Base role
            system_prompt=system_prompt,
            model=profile.configuration.get("model", role_config["default_model"]),
            temperature=profile.configuration.get("temperature", role_config["temperature"]),
            tools=await self._resolve_tools(profile.skills),
            memory_scope=profile.memory_scope,
        )
        
        # Register
        self.module.agents[profile.employee_id] = agent
        
        # Emit event
        await self.module.emit_event(EmployeeCreated(
            employee_id=profile.employee_id,
            company_id=profile.company_id,
            role=profile.role,
            team_id=profile.team_id
        ))
        
        return Employee(agent=agent, profile=profile)
```

### SkillModule (Registry + Composite + Marketplace)

```python
# runtime/skill/module.py
class SkillModule(RuntimeModule):
    """Registry completo de Skills com composição e marketplace."""
    
    name = "skill"
    version = "1.0.0"
    
    def __init__(self, runtime: Runtime):
        super().__init__(runtime)
        self.registry = SkillRegistry()
        self.executors = {
            SkillType.BUILTIN: FunctionSkillExecutor(),
            SkillType.CUSTOM: FunctionSkillExecutor(),
            SkillType.INTEGRATION: ProviderSkillExecutor(self.runtime),
            SkillType.COMPOSITE: CompositeSkillExecutor(self.registry),
            SkillType.AI_GENERATED: AIGeneratedSkillExecutor(self.runtime),
        }
        
    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "register_skill": self.registry.register,
            "get_skill": self.registry.get,
            "list_skills": self.registry.list,
            "execute_skill": self._execute_skill,
            "install_skill": self._install_from_marketplace,
            "compose_skill": self._compose_skills,
        }
        return await ops[operation](**params)
        
    async def _execute_skill(self, skill_id: str, input_data: Dict, 
                            context: SkillContext) -> SkillResult:
        skill = self.registry.get(skill_id)
        executor = self.executors[skill.type]
        
        # Emit start event
        await self.emit_event(SkillExecutionStarted(
            skill_id=skill_id,
            correlation_id=context.correlation_id
        ))
        
        try:
            result = await executor.execute(skill, input_data, context)
            
            await self.emit_event(SkillExecutionCompleted(
                skill_id=skill_id,
                result=result,
                correlation_id=context.correlation_id
            ))
            return result
        except Exception as e:
            await self.emit_event(SkillExecutionFailed(
                skill_id=skill_id,
                error=str(e),
                correlation_id=context.correlation_id
            ))
            raise

class CompositeSkillExecutor:
    """Executa Skills compostas (DAG de steps)."""
    
    async def execute(self, skill: Skill, input_data: Dict, 
                     context: SkillContext) -> SkillResult:
        # skill.definition = {steps: [...], edges: [...]}
        workflow = WorkflowDefinition(
            nodes=[StepNode(**s) for s in skill.definition["steps"]],
            edges=[Edge(**e) for e in skill.definition["edges"]]
        )
        
        execution = await self.workflow_module.execute_workflow(
            workflow_definition=workflow,
            initial_context={**input_data, **context.variables}
        )
        
        return SkillResult(output=execution.final_context, 
                          steps=execution.step_results)
```

### ProviderRegistry (External Connections)

```python
# runtime/provider/registry.py
class ProviderRegistry:
    """Registry de Providers externos (Meta, Twilio, OpenAI, etc)."""
    
    PROVIDER_TYPES = [
        ProviderType.LLM,
        ProviderType.SOCIAL,        # Meta, TikTok, LinkedIn
        ProviderType.COMMUNICATION, # WhatsApp, Twilio, SendGrid
        ProviderType.STORAGE,       # S3, GCS, Azure Blob
        ProviderType.PAYMENT,       # Stripe, MercadoPago, Asaas
        ProviderType.AI_SERVICE,    # Replicate, ElevenLabs, Runway
        ProviderType.DATA,          # NewsAPI, SerpAPI, Clearbit
    ]
    
    def __init__(self):
        self.providers: Dict[str, Provider] = {}
        self.connections: Dict[str, ProviderConnection] = {}
        self.capabilities_index: Dict[str, List[str]] = {}  # capability -> [provider_ids]
        
    def register(self, provider: Provider) -> None:
        self.providers[provider.provider_id] = provider
        for cap in provider.capabilities:
            self.capabilities_index.setdefault(cap, []).append(provider.provider_id)
            
    async def create_connection(self, connection: ProviderConnection) -> ProviderConnection:
        # Validate credentials against provider's config_schema
        provider = self.providers[connection.provider_id]
        provider.validate_credentials(connection.credentials)
        
        # Test connection
        await provider.health_check(connection.credentials)
        
        # Encrypt and store
        connection.credentials = encrypt(connection.credentials)
        connection.status = ConnectionStatus.CONNECTED
        self.connections[connection.connection_id] = connection
        
        await self.emit_event(ProviderConnected(
            provider_id=connection.provider_id,
            connection_id=connection.connection_id,
            company_id=connection.company_id
        ))
        
        return connection
        
    def get_best_provider(self, capability: str, 
                         company_id: str) -> Optional[ProviderConnection]:
        """Selecionar melhor provider por capability (fallback chain)."""
        provider_ids = self.capabilities_index.get(capability, [])
        for pid in provider_ids:
            conn = self._find_active_connection(pid, company_id)
            if conn:
                return conn
        return None
```

### CompanyContextEngine (Nova Camada - Layer 3+)

```python
# runtime/company_context/engine.py
class CompanyContextEngine:
    """
    Camada ACIMA dos Agents - provê contexto de negócio.
    Engine NÃO conhece schemas - apenas armazena e resolve.
    """
    
    def __init__(self, runtime: Runtime):
        self.runtime = runtime
        self.memory = runtime.get_module("memory")
        self.workspace = runtime.get_module("workspace")
        
    # Company Memory Stores (typed via MemoryModule)
    async def save_profile(self, company_id: str, profile: CompanyProfile) -> None:
        await self.memory.write(
            store=f"company_{company_id}",
            key="profile",
            value=profile.to_dict(),
            ttl=None
        )
        await self.emit_event(CompanyProfileSaved(company_id=company_id))
        
    async def get_profile(self, company_id: str) -> CompanyProfile:
        data = await self.memory.read(store=f"company_{company_id}", key="profile")
        return CompanyProfile.from_dict(data)
        
    # ... save/get para Brand, Products, Channels, Goals, Knowledge
    
    async def resolve_for_employee(self, employee_id: str) -> CompanyContext:
        """Monta contexto completo para um Employee."""
        employee = await self._get_employee(employee_id)
        company = await self.get_profile(employee.company_id)
        
        return CompanyContext(
            profile=company,
            brand=await self.get_brand(employee.company_id),
            products=await self.get_products(employee.company_id),
            channels=await self.get_channels(employee.company_id),
            goals=await self.get_goals(employee.company_id),
            knowledge=await self._search_relevant_knowledge(
                employee.company_id,
                employee.role,
                employee.current_task
            )
        )
        
    async def _search_relevant_knowledge(self, company_id: str, 
                                        role: EmployeeRole,
                                        task: Optional[str]) -> List[KnowledgeEntry]:
        """Busca semântica no knowledge base da empresa."""
        query = f"{role.value} {task or ''}"
        embeddings = await self.runtime.get_module("embedding").embed(query)
        results = await self.memory.vector_search(
            store=f"company_{company_id}_knowledge",
            vector=embeddings,
            top_k=10
        )
        return [KnowledgeEntry.from_dict(r) for r in results]
```

---

## 🎭 ORCHESTRATION LAYER (Layer 4) - CONTROLE DE FLUXO

### WorkflowModule (DAG Execution)

```python
# runtime/workflow/module.py
class WorkflowModule(RuntimeModule):
    """Execução DAG completa: paralelo, condicional, loop, retry."""
    
    name = "workflow"
    version = "1.0.0"
    
    NEW_STEP_TYPES = [
        StepType.EMPLOYEE_TASK,      # Delegar a Employee específico
        StepType.SKILL_EXECUTION,    # Executar Skill via Registry
        StepType.PROVIDER_CALL,      # Chamar Provider externo
        StepType.COMPANY_CONTEXT,    # Injetar Company Context
        StepType.TEAM_COLLABORATION, # Multi-agent orchestration
    ]
    
    async def execute_workflow(self, workflow_def: WorkflowDefinition,
                              initial_context: Dict) -> WorkflowExecution:
        execution = WorkflowExecution(
            workflow_id=workflow_def.workflow_id,
            context=initial_context,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        # Build execution graph
        graph = self._build_execution_graph(workflow_def)
        
        # Execute with topological ordering + parallel branches
        await self._execute_graph(graph, execution)
        
        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.utcnow()
        return execution
        
    async def _execute_graph(self, graph: ExecutionGraph, 
                            execution: WorkflowExecution) -> None:
        # Identify ready nodes (no unmet dependencies)
        ready = graph.get_ready_nodes(execution.completed_steps)
        
        while ready:
            # Execute ready nodes in parallel
            tasks = [self._execute_node(node, execution) for node in ready]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for node, result in zip(ready, results):
                if isinstance(result, Exception):
                    execution.mark_failed(node.id, result)
                    if not execution.continue_on_failure:
                        raise
                else:
                    execution.mark_completed(node.id, result)
                    execution.context.update(result.output)
                    
            ready = graph.get_ready_nodes(execution.completed_steps)
            
    async def _execute_node(self, node: WorkflowNode, 
                           execution: WorkflowExecution) -> StepResult:
        step_type = node.step_type
        
        if step_type == StepType.EMPLOYEE_TASK:
            return await self._execute_employee_task(node, execution)
        elif step_type == StepType.SKILL_EXECUTION:
            return await self._execute_skill(node, execution)
        elif step_type == StepType.PROVIDER_CALL:
            return await self._call_provider(node, execution)
        elif step_type == StepType.COMPANY_CONTEXT:
            return await self._inject_company_context(node, execution)
        elif step_type == StepType.TEAM_COLLABORATION:
            return await self._orchestrate_team(node, execution)
        # ... existing step types
```

### SchedulerModule (Company-aware)

```python
# runtime/scheduler/module.py
class SchedulerModule(RuntimeModule):
    """Cron/Interval/Once/Delayed com multi-tenancy."""
    
    name = "scheduler"
    version = "1.0.0"
    
    @dataclass
    class Job:
        job_id: str
        name: str
        cron_expression: Optional[str] = None
        interval_seconds: Optional[int] = None
        run_once_at: Optional[datetime] = None
        delay_seconds: Optional[int] = None
        
        # NOVO: Multi-tenancy
        company_id: Optional[str] = None
        team_id: Optional[str] = None
        employee_id: Optional[str] = None  # Agendar para Employee específico
        
        # Payload para workflow/agent
        target_type: str  # "workflow", "agent", "skill"
        target_id: str
        payload: Dict[str, Any]
        
        # Concurrency
        max_concurrent: int = 1
        semaphore: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(1))
```

### QueueModule (Inter-agent Communication)

```python
# runtime/queue/module.py
class QueueModule(RuntimeModule):
    """Filas tipadas para comunicação assíncrona."""
    
    QUEUE_TYPES = {
        "fifo": FifoQueue,
        "lifo": LifoQueue,
        "priority": PriorityQueue,
        "delayed": DelayedQueue,
    }
    
    async def publish(self, queue_name: str, message: QueueMessage) -> None:
        """Publicar mensagem com correlation_id para tracing."""
        message.correlation_id = message.correlation_id or generate_correlation_id()
        message.causation_id = message.causation_id or message.message_id
        await self.queue_backend.enqueue(queue_name, message)
        
        await self.emit_event(MessagePublished(
            queue=queue_name,
            correlation_id=message.correlation_id
        ))
        
    async def subscribe(self, queue_name: str, 
                       consumer: ConsumerConfig,
                       handler: Callable[[QueueMessage], Awaitable]) -> Consumer:
        """Registrar consumer com concorrência e prefetch controlados."""
        consumer.semaphore = asyncio.Semaphore(consumer.concurrency)
        return await self.queue_backend.register_consumer(queue_name, consumer, handler)
```

---

## 🔌 CAPABILITIES LAYER (Layer 2) - CAPACIDADES TÉCNICAS

### BrowserModule (Playwright)

```python
# runtime/browser/local_browser.py
class LocalBrowserModule(RuntimeModule):
    """Automação de browser com Playwright + CDP."""
    
    name = "browser"
    version = "1.0.0"
    
    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "create_session": self.create_session,
            "navigate": self.navigate,
            "click": self.click,
            "type": self.type_text,
            "screenshot": self.screenshot,
            "get_state": self.get_state,
            "execute_script": self.execute_script,
            "close_session": self.close_session,
        }
        return await ops[operation](**params)
        
    async def create_session(self, url: str = "about:blank", 
                           config: BrowserConfig = None) -> BrowserSession:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=config.headless if config else True,
            args=config.args if config else []
        )
        context = await browser.new_context(
            viewport=config.viewport if config else {"width": 1920, "height": 1080},
            user_agent=config.user_agent if config else None
        )
        page = await context.new_page()
        
        session = BrowserSession(
            session_id=generate_id("sess"),
            browser=browser,
            context=context,
            page=page,
            playwright=playwright,
            url=url
        )
        
        await page.goto(url, wait_until="networkidle")
        self.sessions[session.session_id] = session
        return session
```

### ExecutionModule (Python Sandbox)

```python
# runtime/execution/local_execution.py
class LocalExecutionModule(RuntimeModule):
    """Execução de código Python em sandbox isolado."""
    
    name = "execution"
    version = "1.0.0"
    
    async def execute_python(self, code: str, sandbox_id: str = None,
                           timeout: int = 30, packages: List[str] = None,
                           env_vars: Dict[str, str] = None) -> ExecutionResult:
        # 1. Prepare sandbox (Docker container or subprocess with restrictions)
        sandbox = await self._get_or_create_sandbox(sandbox_id)
        
        # 2. Install packages if needed
        if packages:
            await sandbox.install_packages(packages)
            
        # 3. Execute with timeout
        try:
            result = await asyncio.wait_for(
                sandbox.run(code, env_vars),
                timeout=timeout
            )
            return ExecutionResult(
                success=True,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.return_code,
                artifacts=result.files
            )
        except asyncio.TimeoutError:
            await sandbox.kill()
            return ExecutionResult(
                success=False,
                error="Execution timeout",
                return_code=-1
            )
```

---

## 📦 FOUNDATION LAYER (Layer 1) - FUNDAÇÃO

### MemoryModule (Typed Stores + Vector Search)

```python
# runtime/memory/local_memory.py
class LocalMemoryModule(RuntimeModule):
    """Memory com stores tipados, TTL, índice invertido, vector search."""
    
    name = "memory"
    version = "1.0.0"
    
    STORE_TYPES = {
        "kv": KVStore,           # Key-Value simples
        "document": DocumentStore, # JSON documents with indexing
        "vector": VectorStore,   # Embeddings + similarity search
        "timeseries": TimeSeriesStore, # métricas, logs
        "graph": GraphStore,     # Relacionamentos
    }
    
    async def write(self, store: str, key: str, value: Any, 
                   ttl: int = None, metadata: Dict = None) -> WriteResult:
        # Auto-create store se não existe
        if store not in self.stores:
            store_type = self._infer_store_type(key, value)
            self.stores[store] = self.STORE_TYPES[store_type](store)
            
        return await self.stores[store].write(key, value, ttl, metadata)
        
    async def vector_search(self, store: str, vector: List[float], 
                          top_k: int = 10, filter: Dict = None) -> List[SearchResult]:
        if store not in self.stores or not isinstance(self.stores[store], VectorStore):
            raise ValueError(f"Store {store} is not a vector store")
        return await self.stores[store].search(vector, top_k, filter)
```

### WorkspaceModule (Hierárquico + Quotas)

```python
# runtime/workspace/module.py
class WorkspaceModule(RuntimeModule):
    """Workspaces hierárquicos com quotas e roles."""
    
    name = "workspace"
    version = "1.0.0"
    
    @dataclass
    class Workspace:
        workspace_id: str
        name: str
        parent_id: Optional[str]  # Hierarquia
        workspace_type: WorkspaceType  # COMPANY, TEAM, PERSONAL, PROJECT
        
        # Quotas
        quotas: Dict[ResourceType, ResourceQuota]
        
        # Members
        members: Dict[str, WorkspaceMember]  # user_id -> member
        
        # Settings
        settings: WorkspaceSettings
        
    WORKSPACE_TYPES = [
        WorkspaceType.COMPANY,    # Raiz - representa a empresa
        WorkspaceType.TEAM,       # Filhos de Company
        WorkspaceType.PROJECT,    # Filhos de Team
        WorkspaceType.PERSONAL,   # Filhos de User
    ]
    
    async def create_company_workspace(self, company: CompanyProfile) -> Workspace:
        """Factory para criar workspace tipo COMPANY."""
        workspace = Workspace(
            workspace_id=f"ws_{company.company_id}",
            name=company.name,
            parent_id=None,
            workspace_type=WorkspaceType.COMPANY,
            quotas=self._default_company_quotas(),
            members={},
            settings=WorkspaceSettings(
                allow_public_invite=False,
                require_2fa=True,
                retention_days=2555  # 7 anos
            )
        )
        return await self.create_workspace(workspace)
```

---

## 🔄 FLUXOS DE DADOS PRINCIPAIS

### Fluxo 1: Criação de Employee (Core → Engine)

```
AIPENSA Core                          AIPENSA Engine
     │                                      │
     │ POST /api/employees                  │
     │ {profile: EmployeeProfile}           │
     ▼                                      ▼
┌─────────┐                            ┌─────────┐
│ Validate│                            │Employee │
│ Schema  │                            │Factory  │
└────┬────┘                            └────┬────┘
     │                                      │
     │ 1. Resolve Company Context           │
     │    (CompanyContextEngine)            │
     ▼                                      ▼
┌─────────┐                            ┌─────────┐
│  Get    │                            │  Build  │
│ Company │◄───────────────────────────│ System  │
│ Context │                            │ Prompt  │
└────┬────┘                            └────┬────┘
     │                                      │
     │ 2. Create Agent                      │
     │    with Employee metadata            │
     ▼                                      ▼
┌─────────┐                            ┌─────────┐
│ Register│                            │  Agent  │
│ Agent   │                            │ Module  │
└────┬────┘                            └────┬────┘
     │                                      │
     │ 3. Emit EmployeeCreated Event        │
     │    (EventBus)                        │
     ▼                                      ▼
┌─────────┐                            ┌─────────┐
│ Sync    │◄───────────────────────────│  Event  │
│ State   │                            │   Bus   │
└─────────┘                            └─────────┘
```

### Fluxo 2: Execução de Workflow Diário (Scheduler → Workflow → Employees)

```
Scheduler (cron "0 6 * * *")
     │
     │ Job: daily_content_pipeline
     │ target_type: "workflow"
     │ target_id: "daily_content"
     │ company_id: "comp_abc123"
     ▼
WorkflowModule.execute_workflow()
     │
     ├─► Step 1: EMPLOYEE_TASK → Employee "Manager" (CEO)
     │     │
     │     │ Skill: "news_monitoring" → Provider: "news_api"
     │     │ Output: trending_topics
     │     ▼
     ├─► Step 2: EMPLOYEE_TASK → Employee "Social Media" (MARKETING)
     │     │
     │     │ Input: trending_topics + CompanyContext (brand, voice, products)
     │     │ Skill: "copywriting" → LLM Module (llama-3.1-70b)
     │     │ Output: social_posts
     │     ▼
     ├─► Step 3 (PARALLEL):
     │     ├─► EMPLOYEE_TASK → Employee "Video Creator" (DESIGNER)
     │     │     Skill: "video_script" → LLM Module
     │     │     Output: video_scripts
     │     │
     │     └─► EMPLOYEE_TASK → Employee "Designer" (DESIGNER)
     │           Skill: "thumbnail_generation" → Image Module
     │           Output: thumbnails
     │     ▼
     └─► Step 4: SKILL_EXECUTION → "social_publisher"
           │
           │ Provider: "meta" (Instagram/Facebook), "tiktok", "whatsapp"
           │ Input: social_posts + video_scripts + thumbnails
           ▼
     Event: WORKFLOW_COMPLETED + Resultados
```

### Fluxo 3: Sync Package (Engine → Core)

```
AIPENSA Core                    AIPENSA Engine
     │                              │
     │ GET /api/sync/export         │
     ▼                              ▼
┌─────────┐                     ┌─────────┐
│ Request │                     │Exporter │
│ Sync    │                     │         │
└────┬────┘                     └────┬────┘
     │                               │
     │ 1. Aggregate all data         │
     │    - Companies                │
     │    - Employees/Teams          │
     │    - Skills/Providers         │
     │    - Workflows/Schedules      │
     │    - Plugin Configs           │
     ▼                               ▼
┌─────────┐                     ┌─────────┐
│ Receive │◄────────────────────│ Generate│
│ YAML    │                     │ aipensa-│
│ Package │                     │ sync-v1 │
└────┬────┘                     │ .yaml   │
     │                         └─────────┘
     │
     │ 2. Validate checksum
     │ 3. Import to Core DB
     ▼
┌─────────┐
│ Core DB │
│ Updated │
└─────────┘
```

---

## 📊 OBSERVABILIDADE NATIVA

### Structured Logging

```python
# runtime/base/logging.py
import structlog

logger = structlog.get_logger()

# Uso padrão em toda Engine
logger.info(
    "workflow_step_started",
    workflow_id=execution.workflow_id,
    step_id=node.id,
    step_type=node.step_type.value,
    correlation_id=execution.correlation_id,
    causation_id=execution.causation_id,
    company_id=execution.company_id,
    employee_id=getattr(node, 'employee_id', None)
)
```

### Metrics (Prometheus)

```python
# runtime/base/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Counters
EVENTS_EMITTED = Counter('engine_events_emitted_total', 'Events emitted', ['event_type'])
WORKFLOWS_EXECUTED = Counter('engine_workflows_executed_total', 'Workflows executed', 
                             ['workflow_id', 'status'])
SKILLS_EXECUTED = Counter('engine_skills_executed_total', 'Skills executed',
                          ['skill_id', 'status'])
AGENT_TASKS = Counter('engine_agent_tasks_total', 'Agent tasks', ['agent_id', 'status'])

# Histograms
WORKFLOW_DURATION = Histogram('engine_workflow_duration_seconds', 'Workflow duration',
                              ['workflow_id'])
SKILL_LATENCY = Histogram('engine_skill_latency_seconds', 'Skill latency', ['skill_id'])
LLM_TOKEN_USAGE = Histogram('engine_llm_tokens_total', 'LLM tokens', ['model', 'type'])

# Gauges
ACTIVE_AGENTS = Gauge('engine_active_agents', 'Active agents', ['company_id'])
ACTIVE_WORKFLOWS = Gauge('engine_active_workflows', 'Active workflows')
QUEUE_DEPTH = Gauge('engine_queue_depth', 'Queue depth', ['queue_name'])
```

### Distributed Tracing (OpenTelemetry)

```python
# runtime/base/tracing.py
from opentelemetry import trace
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer("aipensa.engine")

# Em todo handler de evento / operação
@tracer.start_as_current_span("execute_skill", kind=SpanKind.INTERNAL)
async def execute_skill(self, skill_id: str, input_data: Dict, context: SkillContext):
    span = trace.get_current_span()
    span.set_attribute("skill.id", skill_id)
    span.set_attribute("correlation_id", context.correlation_id)
    span.set_attribute("company_id", context.company_id)
    
    # ... execution
```

---

## 🚀 DEPLOY ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         KUBERNETES CLUSTER                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ENGINE DEPLOYMENT (StatefulSet)              │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │   │
│  │  │ Pod 1   │ │ Pod 2   │ │ Pod 3   │ │ Pod N   │  (Horizontal  │   │
│  │  │ Engine  │ │ Engine  │ │ Engine  │ │ Engine  │   Scaling)    │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘               │   │
│  └───────┼───────────┼───────────┼───────────┼────────────────────┘   │
│          │           │           │           │                        │
│  ┌───────▼───────────▼───────────▼───────────▼────────────────┐     │
│  │              SHARED STATE (External)                       │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │     │
│  │  │PostgreSQL│ │  Redis   │ │  S3/MinIO│ │  Vector DB   │  │     │
│  │  │(State/   │ │(Cache/   │ │(Artifacts/│ │(Embeddings/  │  │     │
│  │  │ Workflows)│ │ Queue/   │ │ Screenshots)│ │ Knowledge)   │  │     │
│  │  │          │ │ Sessions)│ │           │ │              │  │     │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    INGRESS / SERVICE MESH                        │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│  │  │REST API  │  │WebSocket │  │  GraphQL │  │  Metrics │        │ │
│  │  │  :8000   │  │  :8001   │  │  :8002   │  │  :9090   │        │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### Resource Requirements (Production)

| Componente | CPU | RAM | Storage | Replicas |
|------------|-----|-----|---------|----------|
| Engine Pod | 2-4 cores | 4-8 GB | 10 GB ephemeral | 3+ (HPA) |
| PostgreSQL | 4 cores | 16 GB | 500 GB SSD | 1 Primary + 1 Replica |
| Redis Cluster | 2 cores | 8 GB | 50 GB | 3 Masters + 3 Replicas |
| S3/MinIO | - | - | 1 TB+ | Distributed |
| Vector DB (Qdrant/PGVector) | 4 cores | 16 GB | 200 GB | 3+ |
| NVIDIA NIM (GPU) | 8 cores | 32 GB | 100 GB | 2+ (GPU nodes) |

---

## 🔐 SEGURANÇA & COMPLIANCE

### Network Policies

```yaml
# k8s/network-policy-engine.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: engine-egress
spec:
  podSelector:
    matchLabels:
      app: aipensa-engine
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - namespaceSelector:
        matchLabels:
          name: external
    ports:
    - protocol: TCP
      port: 443  # HTTPS para Providers externos
```

### Secrets Management

```python
# runtime/base/secrets.py
class SecretsManager:
    """Integração com Vault / AWS Secrets Manager / Azure Key Vault."""
    
    async def get_secret(self, path: str) -> str:
        # Cache local com TTL 5min
        # Fallback: env var -> file -> vault
        pass
        
    async def rotate_credentials(self, provider_id: str, 
                                company_id: str) -> None:
        # Rotaciona credenciais de ProviderConnection
        # Emite ProviderCredentialsRotated event
        pass
```

---

## 📦 PACOTE DE SYNC (Engine ↔ Core)

### Estrutura do Arquivo

```
aipensa-sync-v1.yaml
├── version: "1.0"
├── exported_at: "2026-07-28T10:00:00Z"
├── engine_version: "1.2.0"
├── checksum: "sha256:..."
├── companies: []
├── employees: []
├── teams: []
├── skills: []
├── providers: []
├── workflows: []
├── schedules: []
├── plugins: []
├── llm_models: []
└── memory_configs: []
```

### Exemplo Mínimo

```yaml
version: "1.0"
engine_version: "1.2.0"
exported_at: "2026-07-28T10:00:00Z"
checksum: "sha256:a1b2c3d4..."

companies:
  - company_id: "comp_abc123"
    profile:
      name: "Acme Corp"
      segment: "ecommerce"
    brand:
      name: "Acme"
      voice_tone: "friendly"
    channels:
      instagram: {handle: "@acme", access_token_ref: "secret:insta_token"}
      whatsapp: {number: "+5511999999999", verified: true}

employees:
  - employee_id: "emp_mgr_001"
    company_id: "comp_abc123"
    name: "Manager IA"
    role: "CEO"
    skills: ["strategic_planning", "news_monitoring"]
    model: "meta/llama-3.1-70b-instruct"
    temperature: 0.3
    memory_scope: "COMPANY"

teams:
  - team_id: "team_marketing"
    company_id: "comp_abc123"
    members: ["emp_social_001", "emp_video_001"]
    workflows: ["daily_content", "weekly_campaign"]

workflows:
  - workflow_id: "daily_content"
    version: "1.2.0"
    nodes: [...]
    edges: [...]

schedules:
  - job_id: "daily_content_trigger"
    workflow_id: "daily_content"
    cron: "0 6 * * *"
    timezone: "America/Sao_Paulo"
```

---

## ✅ VALIDAÇÃO ARQUITETURAL

### Checklist de Revisão (Para PRs)

- [ ] **Layering** - Camada N só depende de < N?
- [ ] **No Business Logic** - Zero `if company.segment`?
- [ ] **Events Emitted** - Toda mudança de estado emite evento?
- [ ] **Multi-tenant** - `company_id`/`workspace_id` em todas operações?
- [ ] **Plugin Contract** - Novos plugins seguem `ENGINE_PLUGIN_GUIDE.md`?
- [ ] **Observability** - Logs estruturados + métricas + traces?
- [ ] **Error Handling** - Exceptions customizadas + DLQ para eventos?
- [ ] **Tests** - Unit + Integration + Contract tests?
- [ ] **Docs Updated** - `ENGINE_API_CONTRACT.md`, `ENGINE_EVENTS.md`?
- [ ] **Backward Compat** - Nenhum breaking change sem RFC?

---

**ESTA ARQUITETURA É A IMPLEMENTAÇÃO DA ENGINE_SPEC.md. QUALQUER DESVIO REQUER RFC APROVADO PELO CTO.**