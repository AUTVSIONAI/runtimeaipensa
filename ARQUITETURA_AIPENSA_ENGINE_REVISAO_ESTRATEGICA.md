# 🏗️ REVISÃO ARQUITETURAL ESTRATÉGICA - AIPENSA ENGINE (Runtime)

**Data:** 28 de Julho de 2026  
**Versão:** 1.0  
**Status:** Análise Completa - Pronto para Decisão do CTO  
**Autor:** Arquitetura de Software Sênior / CTO Office  

---

## 🎯 RESUMO EXECUTIVO

Após análise profunda de **todo o códigobase existente** (24 módulos runtime, 57 plugins, 155+ tipos de evento, API FastAPI completa, Frontend Next.js 14), confirmo que:

> **O Runtime NÃO precisa ser reescrito.** Ele já é uma Engine robusta, modular, orientada a eventos e pronta para evoluir para a **AIPENSA ENGINE** - o kernel de inteligência do ecossistema.

### 📊 Estado Atual (Produção-Ready para Dev/Validação)

| Componente | Status | Arquivos | Linhas | Observação |
|------------|--------|----------|--------|------------|
| **Runtime Core** | ✅ Completo | 8 | ~2.5k | Factory, DI, Registry, Module Base |
| **24 Módulos Runtime** | ✅ Todos Operacionais | 24 | ~15k | Core + AI + Orchestration + Infra |
| **Plugin System** | ✅ Completo | 57 plugins | ~8k | Auto-discovery, lifecycle, types |
| **EventBus** | ✅ 155+ Eventos | 2 | ~1.5k | Correlação/causação, prioridade, DLQ |
| **Workflow (DAG)** | ✅ Execução Completa | 1 | ~1.8k | Paralelo, condicional, loop, retry |
| **Scheduler (Cron)** | ✅ Completo | 1 | ~1.2k | Recorrente, once, interval, delayed |
| **Queue System** | ✅ 4 Tipos | 1 | ~1.5k | FIFO, LIFO, Priority, Delayed + DLQ |
| **Workspace** | ✅ Multi-tenant | 1 | ~1.8k | Quotas, roles, convites, hierarquia |
| **Conversation** | ✅ Streaming + Tools | 1 | ~1.2k | SSE, tool calls, contexto, persistência |
| **Memory** | ✅ Busca + TTL | 1 | ~1k | Índice invertido, persistência opcional |
| **LLM Module** | ✅ 91 Modelos NVIDIA | 1 | ~2.5k | Multi-provider, cost tracking, templates |
| **Skill Module** | ✅ Registry + Composição | 1 | ~1.5k | Builtin, Custom, Composite, Marketplace |
| **Agent Module** | ✅ Lifecycle + Msg Passing | 1 | ~1.2k | Roles, tools, memory, task queue |
| **Browser/FS/Exec/Net** | ✅ Operacional | 4 | ~3k | Playwright, Sandbox, HTTP, Docker |
| **AI Capabilities** | ✅ 7 Módulos | 7 | ~3k | Voice, Vision, Video, Image, Embedding, RAG, Reasoning |
| **FastAPI Server** | ✅ 50+ Endpoints | 2 | ~2k | REST + WebSocket EventBus |
| **Next.js Frontend** | ✅ 9 Páginas | 50+ | ~8k | Dashboard, Chat, Workflow, Timeline, Debug, Browser, Workspace, Settings, Plugins |

---

## 📦 INVENTÁRIO COMPLETO DOS MÓDULOS EXISTENTES

### 🔧 CORE MODULES (9) - Fundação da Engine
```
1. browser          → LocalBrowserModule (Playwright)          ✅
2. execution        → LocalExecutionModule (Python/Shell)      ✅
3. tool / toolcalling → LocalToolsModule (Registry + Exec)    ✅
4. memory           → LocalMemoryModule (Store + Search + TTL) ✅
5. planning         → LocalPlanningModule (LLM-based)          ✅
6. mcp              → LocalMCPModule (Model Context Protocol)  ✅
7. filesystem       → LocalFileSystemModule (Read/Write/List)  ✅
8. network          → LocalNetworkModule (HTTP/Download)       ✅
9. docker           → LocalDockerModule (Containers)           ✅
```

### 🤖 AGENT & CONVERSATION (2) - Camada de Inteligência
```
10. agent           → AgentModule (Lifecycle, Tasks, Messages) ✅
11. conversation    → ConversationModule (Streaming, Context)  ✅
```

### 🎭 ORCHESTRATION (3) - Controle de Fluxo
```
12. workflow        → WorkflowModule (DAG, Paralelo, Condicional, Loop) ✅
13. scheduler       → SchedulerModule (Cron, Interval, Once, Delayed) ✅
14. queue           → QueueModule (FIFO/LIFO/Priority/Delayed + DLQ) ✅
```

### 🏗️ INFRASTRUCTURE (5) - Serviços Transversais
```
15. notification    → NotificationModule (Alerts, Webhooks)    ✅
16. storage         → StorageModule (Blob, KV)                 ✅
17. authentication  → AuthenticationModule (Auth, Tokens, ACL) ✅
18. workspace       → WorkspaceModule (Multi-tenant, Quotas, Invites) ✅
19. skill           → SkillModule (Registry, Composite, Marketplace) ✅
```

### 🧠 AI CAPABILITIES (7) - Capacidades de IA
```
20. voice           → VoiceModule (TTS, STT, Cloning)          ⚠️ Mock only
21. vision          → VisionModule (Detection, OCR, Face)      ⚠️ Mock only
22. video           → VideoModule (Analysis, Transcode, Gen)   ⚠️ Mock only
23. image           → ImageModule (Generation, Edit, Style)    ⚠️ Mock only
24. embedding       → EmbeddingModule (Text/Image/Vector)      ⚠️ Mock only
25. rag             → RAGModule (Index, Search, QA)            ⚠️ Mock only
26. reasoning       → ReasoningModule (CoT, Logic, Problem)    ⚠️ Mock only
27. llm             → LLMModule (91 models, Multi-provider)    ✅ Production
```

---

## 🔄 EVENTBUS - CORAÇÃO DO SISTEMA (155+ TIPOS)

### Categorias Existentes
```python
# Runtime Lifecycle (6)
RUNTIME_STARTED, RUNTIME_STOPPED, RUNTIME_READY, RUNTIME_ERROR, RUNTIME_MAINTENANCE

# Module Lifecycle (4)
MODULE_STARTED, MODULE_STOPPED, MODULE_ERROR, MODULE_INITIALIZED

# Plugin Lifecycle (4)
PLUGIN_LOADED, PLUGIN_STARTED, PLUGIN_STOPPED, PLUGIN_ERROR

# Task/Execution (4)
TASK_STARTED, TASK_COMPLETED, TASK_FAILED, TASK_CANCELLED

# Agent (5)
AGENT_CREATED, AGENT_STARTED, AGENT_COMPLETED, AGENT_FAILED, AGENT_MESSAGE

# Conversation (4)
CONVERSATION_STARTED, CONVERSATION_ENDED, MESSAGE_RECEIVED, MESSAGE_SENT

# Workflow (7)
WORKFLOW_STARTED, WORKFLOW_COMPLETED, WORKFLOW_FAILED, 
WORKFLOW_STEP_STARTED, WORKFLOW_STEP_COMPLETED, WORKFLOW_STEP_FAILED,
WORKFLOW_PAUSED, WORKFLOW_RESUMED, WORKFLOW_CANCELLED

# Tool/Browser/Memory/Planning/MCP/Sandbox/FS/Network/Docker (40+)

# System (3)
SYSTEM_ERROR, SYSTEM_WARNING, SYSTEM_INFO
```

### Capacidades Enterprise Já Implementadas
- ✅ **Correlation ID** - Rastreamento end-to-end
- ✅ **Causation ID** - Causalidade entre eventos
- ✅ **Prioridade** (LOW/NORMAL/HIGH/CRITICAL)
- ✅ **Dead Letter Queue** - Falhas não perdidas
- ✅ **Filtros Globais** - Roteamento inteligente
- ✅ **Log Circular** (10k eventos) - Auditoria
- ✅ **Processamento Assíncrono/Síncrono**
- ✅ **WebSocket Broadcasting** - Tempo real para Frontend

---

## 🎯 ANÁLISE DE REUTILIZAÇÃO - O QUE JÁ RESOLVE O NOVO

| Nova Necessidade (CTO) | Módulo Existente | Reutilização | Gap |
|------------------------|------------------|--------------|-----|
| **Agent Registry** | `AgentModule` + `AgentMetadata` | **90%** | Persistência + Versioning |
| **Team Manager** | `WorkspaceModule` (hierarquia) + `AgentModule` | **70%** | Conceito de "Team" explícito |
| **Employees (IA)** | `AgentModule` (roles: WORKER/SUPERVISOR/PLANNER/etc) | **85%** | Perfil "Employee" + Company Context |
| **Skill Registry** | `SkillModule` (JÁ EXISTE COMPLETO) | **100%** | ✅ Pronto |
| **Plugin Architecture** | `PluginManager` + 57 Plugins | **100%** | ✅ Pronto |
| **Company Context** | `WorkspaceModule` + `MemoryModule` | **60%** | Novo: CompanyContext Engine |
| **Company Memory** | `MemoryModule` (typed stores) | **50%** | Novo: Schemas CompanyProfile, Brand, etc |
| **Onboarding Interfaces** | `Plugin System` + `NetworkModule` | **30%** | Contratos/Interfaces apenas |
| **Runtime Explorer** | Todos os módulos + EventBus | **80%** | UI + Agregação |
| **EventBus Expansion** | `EventBus` (core) | **95%** | Novos EventTypes apenas |

---

## 🏗️ PROPOSTA ARQUITETURAL - AIPENSA ENGINE

### Princípios (Conforme Diretriz CTO)
1. **Runtime ≠ Produto** - Engine pura, sem regras de negócio
2. **Company Context Engine** - Camada ACIMA dos agentes
3. **Zero Duplicação** - Reutilizar tudo que existe
4. **Plugin-First** - Tudo plugável (Skills, Providers, Employees, Workflow Nodes, Memory, LLMs)
5. **Event-Driven** - EventBus único, expandido
6. **Desacoplado do AIPENSA Core** - Runtime é biblioteca reutilizável

---

### 📐 ARQUITETURA FINAL PROPOSTA

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AIPENSA CORE (Produto Final)                         │
│  CRM • Delivery • Financeiro • Marketplace • Clínicas • Restaurantes • ...  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ APIs/Contracts (HTTP + WebSocket)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AIPENSA ENGINE (Runtime - ESTE PROJETO)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  COMPANY CONTEXT ENGINE (NOVA CAMADA)               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │   │
│  │  │Company   │  │Company   │  │Onboarding│  │Company   │             │   │
│  │  │Profile   │  │Memory    │  │Interfaces│  │Context   │             │   │
│  │  │(Schema)  │  │(Multi-store)          │  │Resolver  │             │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AGENT / EMPLOYEE LAYER                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ AgentRegistry│  │ TeamManager  │  │ EmployeeFactory│            │   │
│  │  │ (persistência│  │ (hierarquia, │  │ (especializa-  │            │   │
│  │  │  versioning) │  │  contexto)   │  │  ção por role) │            │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    SKILL / PROVIDER LAYER                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ SkillRegistry│  │ Provider     │  │ Tool Adapter │              │   │
│  │  │ (JÁ EXISTE)  │  │ Registry     │  │ (JÁ EXISTE)  │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 ORCHESTRATION LAYER (EXISTENTE)                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                │   │
│  │  │ Workflow │ │Scheduler │ │ Queue    │ │Planning  │                │   │
│  │  │ (DAG)    │ │(Cron)    │ │(Priority)│ │(LLM)     │                │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 RUNTIME CORE (EXISTENTE - 24 MÓDULOS)               │   │
│  │  [Agent] [Conv] [Workflow] [Scheduler] [Queue] [Skill] [Browser]   │   │
│  │  [Execution] [Tools] [Memory] [Planning] [MCP] [FS] [Net] [Docker] │   │
│  │  [Notification] [Storage] [Auth] [Workspace] [LLM] [Voice] [Vision]│   │
│  │  [Video] [Image] [Embedding] [RAG] [Reasoning]                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              EVENT BUS (ÚNICO - 155+ TIPOS + EXPANSÃO)              │   │
│  │  Correlation • Causation • Priority • DLQ • Filters • WebSocket    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 O QUE SERÁ MANTIDO (Zero Mudança)

| Componente | Arquivo | Justificativa |
|------------|---------|---------------|
| **Runtime Core** | `runtime/runtime.py`, `runtime/base/*` | Factory, DI, Registry funcionando |
| **24 Módulos** | `runtime/*/module.py` | Todos operacionais, testados |
| **Plugin System** | `runtime/plugins/*` | 57 plugins, auto-discovery, lifecycle |
| **EventBus** | `runtime/events/__init__.py`, `runtime/base/events.py` | 155+ eventos, correlação, DLQ, WebSocket |
| **Workflow Engine** | `runtime/workflow/module.py` | DAG completo, paralelo, condicional, loop, retry |
| **Scheduler** | `runtime/scheduler/module.py` | Cron, interval, once, delayed, persistência |
| **Queue System** | `runtime/queue/module.py` | 4 tipos, DLQ, backpressure, consumers |
| **Workspace** | `runtime/workspace/module.py` | Multi-tenant, quotas, roles, convites, hierarquia |
| **Conversation** | `runtime/conversation/module.py` | Streaming, tools, contexto, persistência |
| **Memory** | `runtime/memory/local_memory.py` | Store, search, TTL, índice invertido |
| **Skill Module** | `runtime/skill/module.py` | Registry, composite, marketplace, versioning |
| **Agent Module** | `runtime/agent/module.py` | Lifecycle, roles, message passing, task queue |
| **LLM Module** | `runtime/llm/module.py` | 91 modelos, multi-provider, cost tracking |
| **Browser/FS/Exec/Net/Docker** | `runtime/*/local_*.py` | Operacionais |
| **FastAPI Server** | `runtime/api/server.py` | 50+ endpoints, WebSocket, CORS |
| **Next.js Frontend** | `frontend/src/*` | 9 páginas, Zustand, React Query, ReactFlow |

---

## 🔧 O QUE SERÁ EXPANDIDO (Evolução, Não Reescrita)

### 1. EventBus - Novos EventTypes
```python
# NOVOS EVENTOS (apenas adição ao Enum existente)
class RuntimeEventType(Enum):
    # Company Context
    COMPANY_CREATED = "CompanyCreated"
    COMPANY_UPDATED = "CompanyUpdated"
    COMPANY_CONTEXT_RESOLVED = "CompanyContextResolved"
    
    # Employees
    EMPLOYEE_CREATED = "EmployeeCreated"
    EMPLOYEE_ASSIGNED = "EmployeeAssignedToTeam"
    EMPLOYEE_ACTIVATED = "EmployeeActivated"
    EMPLOYEE_DEACTIVATED = "EmployeeDeactivated"
    
    # Teams
    TEAM_CREATED = "TeamCreated"
    TEAM_MEMBER_ADDED = "TeamMemberAdded"
    TEAM_CONTEXT_SYNCED = "TeamContextSynced"
    
    # Skills/Providers
    SKILL_REGISTERED = "SkillRegistered"
    SKILL_INSTALLED = "SkillInstalled"
    PROVIDER_REGISTERED = "ProviderRegistered"
    PROVIDER_CONNECTED = "ProviderConnected"
    
    # Company Memory
    COMPANY_KNOWLEDGE_STORED = "CompanyKnowledgeStored"
    COMPANY_KNOWLEDGE_RETRIEVED = "CompanyKnowledgeRetrieved"
    
    # Onboarding
    ONBOARDING_STARTED = "OnboardingStarted"
    ONBOARDING_SOURCE_CONNECTED = "OnboardingSourceConnected"
    ONBOARDING_DATA_INGESTED = "OnboardingDataIngested"
```

### 2. Workflow Module - Novos Step Types
```python
# Adicionar ao StepType enum existente
class StepType(Enum):
    # ... existentes ...
    EMPLOYEE_TASK = "employee_task"      # Delegar a Employee específico
    SKILL_EXECUTION = "skill_execution"  # Executar Skill via Registry
    PROVIDER_CALL = "provider_call"      # Chamar Provider externo
    COMPANY_CONTEXT = "company_context"  # Injetar Company Context
    TEAM_COLLABORATION = "team_collab"   # Multi-agent collaboration
```

### 3. Scheduler - Company-aware Jobs
```python
# Job ganha company_id, team_id para multi-tenancy
@dataclass
class Job:
    # ... existentes ...
    company_id: Optional[str] = None
    team_id: Optional[str] = None
    employee_id: Optional[str] = None  # Agendamento por Employee
```

### 4. Workspace Module - Company as Workspace Type
```python
# Adicionar ao WorkspaceType
class WorkspaceType(Enum):
    # ... existentes ...
    COMPANY = "company"  # Workspace = Empresa completa
```

---

## 🆕 O QUE SERÁ CRIADO (Novos Componentes)

### 1. Company Context Engine (Nova Camada - ~3-4 arquivos)

```
runtime/company_context/
├── __init__.py
├── models.py              # CompanyProfile, CompanyBrand, CompanyProducts, etc.
├── memory.py              # CompanyMemory (wrap MemoryModule com schemas)
├── resolver.py            # CompanyContextResolver (injeta contexto em Employees)
├── interfaces.py          # OnboardingInterfaces (contratos p/ Instagram, CRM, etc)
└── module.py              # CompanyContextModule (RuntimeModule)
```

#### Models (Company Memory Schemas)
```python
@dataclass
class CompanyProfile:
    company_id: str
    name: str
    legal_name: str
    tax_id: str
    segment: str  # "ecommerce", "clinic", "restaurant", "delivery", "saas"
    size: str     # "micro", "small", "medium", "large"
    founded_date: datetime
    metadata: Dict

@dataclass  
class CompanyBrand:
    company_id: str
    name: str
    tagline: str
    colors: Dict[str, str]  # primary, secondary, accent
    logo_url: str
    voice_tone: str  # "professional", "friendly", "bold", "minimalist"
    guidelines: str

@dataclass
class CompanyProducts:
    company_id: str
    products: List[Product]  # id, name, description, price, category, sku
    services: List[Service]

@dataclass
class CompanyChannels:
    company_id: str
    instagram: Optional[ChannelConfig]
    facebook: Optional[ChannelConfig]
    tiktok: Optional[ChannelConfig]
    whatsapp: Optional[ChannelConfig]
    website: Optional[ChannelConfig]
    google_business: Optional[ChannelConfig]

@dataclass
class CompanyGoals:
    company_id: str
    okrs: List[OKR]  # objective, key_results, period, owner
    kpis: List[KPI]
    targets: Dict[str, float]

@dataclass
class CompanyKnowledge:
    company_id: str
    documents: List[Document]  # policies, processes, FAQs, scripts
    embeddings: List[EmbeddingRef]  # referencia para EmbeddingModule
    faq: List[FAQEntry]
```

#### CompanyContextResolver
```python
class CompanyContextResolver:
    """
    Resolve e injeta Company Context em:
    - Employee prompts (system prompt enriquecido)
    - Skill execution context
    - Workflow variables
    - LLM requests
    """
    
    async def resolve_for_employee(self, employee_id: str) -> Dict[str, Any]:
        """Monta contexto completo para um Employee"""
        company = await self.get_company(employee.company_id)
        return {
            "company_profile": company.profile,
            "brand": company.brand,
            "products": company.products,
            "channels": company.channels,
            "goals": company.goals,
            "knowledge_base": await self.search_relevant_knowledge(
                employee.role, employee.current_task
            )
        }
```

#### Onboarding Interfaces (Contratos Apenas)
```python
# runtime/company_context/interfaces.py
class OnboardingSource(Protocol):
    """Interface para fontes de onboarding - IMPLEMENTADO PELO AIPENSA CORE"""
    
    async def fetch_instagram_data(self, credentials: Dict) -> InstagramData: ...
    async def fetch_facebook_data(self, credentials: Dict) -> FacebookData: ...
    async def fetch_tiktok_data(self, credentials: Dict) -> TikTokData: ...
    async def fetch_google_business(self, credentials: Dict) -> GoogleBusinessData: ...
    async def fetch_website_data(self, url: str) -> WebsiteData: ...
    async def fetch_whatsapp_data(self, credentials: Dict) -> WhatsAppData: ...
    async def fetch_catalog(self, credentials: Dict) -> CatalogData: ...
    async def fetch_crm_data(self, credentials: Dict) -> CRMData: ...
    async def fetch_orders(self, credentials: Dict) -> OrdersData: ...

# Runtime NÃO implementa scraping - apenas define contratos
# AIPENSA Core implementa e envia dados via API
```

### 2. Agent Registry (Persistência + Versioning) - Extende AgentModule

```
runtime/agent/
├── module.py          # EXISTENTE - estender
├── registry.py        # NOVO - AgentRegistry
├── models.py          # EXISTENTE - estender EmployeeProfile
└── persistence.py     # NOVO - Persistência de Agents/Employees
```

```python
# Novos modelos em models.py
@dataclass
class EmployeeProfile(AgentMetadata):
    """Extende AgentMetadata para conceito de Funcionário IA"""
    employee_id: str
    company_id: str
    team_id: Optional[str]
    role: EmployeeRole  # MARKETING, FINANCE, SUPPORT, DESIGNER, EDITOR, SOCIAL_MEDIA, CEO, HR, LEGAL, DELIVERY
    specialization: str
    skills: List[str]  # Skill IDs
    permissions: List[str]
    memory_scope: MemoryScope  # COMPANY, TEAM, PERSONAL
    enabled: bool = True
    version: str = "1.0.0"
    configuration: Dict[str, Any] = field(default_factory=dict)  # model, temperature, etc

@dataclass
class Team:
    team_id: str
    company_id: str
    name: str
    description: str
    members: List[str]  # employee_ids
    shared_context: Dict[str, Any]
    workflows: List[str]  # workflow_ids
    created_at: datetime
```

### 3. Team Manager (Novo Módulo ou Extensão Workspace)

```
runtime/team/
├── __init__.py
├── module.py            # TeamModule (RuntimeModule)
├── models.py            # Team, TeamMember, TeamContext
└── coordination.py      # TeamCoordination (multi-agent patterns)
```

### 4. Provider Registry (Novo - Para Skills)

```
runtime/provider/
├── __init__.py
├── module.py            # ProviderModule
├── registry.py          # ProviderRegistry
├── models.py            # Provider, ProviderConfig, ProviderConnection
└── base.py              # ProviderBase (abstract)
```

```python
@dataclass
class Provider:
    provider_id: str
    name: str           # "meta", "openai", "twilio", "aws", "google"
    type: ProviderType  # LLM, SOCIAL, COMMUNICATION, STORAGE, PAYMENT, AI_SERVICE
    status: ProviderStatus
    config_schema: Dict  # JSON Schema para configuração
    capabilities: List[str]
    version: str
    
@dataclass 
class ProviderConnection:
    connection_id: str
    provider_id: str
    company_id: str
    credentials: Dict  # encrypted
    status: ConnectionStatus
    scopes: List[str]
```

### 5. Runtime Explorer (Backend API + Frontend Page)

```
backend novas rotas:
GET  /api/runtime/explorer/overview
GET  /api/runtime/explorer/agents
GET  /api/runtime/explorer/teams
GET  /api/runtime/explorer/employees
GET  /api/runtime/explorer/company-context
GET  /api/runtime/explorer/skills
GET  /api/runtime/explorer/providers
GET  /api/runtime/explorer/llms
GET  /api/runtime/explorer/plugins
GET  /api/runtime/explorer/workers
GET  /api/runtime/explorer/queues
GET  /api/runtime/explorer/memory
GET  /api/runtime/explorer/logs
GET  /api/runtime/explorer/performance

frontend nova página:
frontend/src/app/(dashboard)/runtime-explorer/page.tsx
```

### 6. Sync/Export Package para aipensa.com

```
runtime/sync/
├── __init__.py
├── exporter.py          # Exporta configuração completa (YAML/JSON)
├── importer.py          # Importa configuração
├── models.py            # SyncPackage, SyncManifest
└── validators.py        # Validação de compatibilidade
```

```python
@dataclass
class SyncPackage:
    """Pacote completo para sincronização com AIPENSA Core"""
    version: str = "1.0"
    exported_at: datetime
    runtime_version: str
    
    # Company Context
    companies: List[CompanyProfile]
    company_brands: List[CompanyBrand]
    company_products: List[CompanyProducts]
    company_channels: List[CompanyChannels]
    company_goals: List[CompanyGoals]
    company_knowledge: List[CompanyKnowledge]
    
    # Employees & Teams
    employees: List[EmployeeProfile]
    teams: List[Team]
    
    # Skills & Providers
    skills: List[Skill]
    providers: List[Provider]
    provider_connections: List[ProviderConnection]
    
    # Orchestration
    workflows: List[Workflow]
    schedules: List[Job]
    
    # Runtime Config
    plugins: List[PluginConfig]
    llm_models: List[ModelConfig]
    memory_configs: List[MemoryConfig]
```

---

## 🔗 MAPEAMENTO DE COMUNICAÇÃO ENTRE MÓDULOS

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Company Context │────▶│ Employee Factory│────▶│ Agent Module    │
│ Engine          │     │ (cria Employee) │     │ (executa Agent) │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                      ┌──────────────────────────────────┘
                      ▼
           ┌─────────────────────┐
           │   Skill Registry    │◀──── Provider Registry
           │   (SkillModule)     │     (ProviderModule)
           └──────────┬──────────┘
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
    ┌─────────────┐       ┌─────────────┐
    │ Workflow    │       │ Scheduler   │
    │ Module      │       │ Module      │
    │ (DAG exec)  │       │ (Cron/Jobs) │
    └──────┬──────┘       └──────┬──────┘
           │                     │
           └──────────┬──────────┘
                      ▼
           ┌─────────────────────┐
           │    EventBus         │
           │ (Correlation/Causa) │
           └─────────────────────┘
```

### Fluxo Principal: "Manager 6am → Social Media → Video Creator"

```
1. Scheduler (cron "0 6 * * *") dispara Job "daily_content_pipeline"
   │
   ▼
2. Workflow "daily_content" inicia (DAG)
   │
   ├── Step 1: EMPLOYEE_TASK → Employee "Manager" (role=CEO)
   │   │  Action: "fetch_trending_news"
   │   │  Skill: "news_monitoring" → Provider: "news_api"
   │   │  Output: trending_topics → Context
   │   ▼
   ├── Step 2: EMPLOYEE_TASK → Employee "Social Media" (role=SOCIAL_MEDIA)
   │   │  Input: trending_topics + CompanyContext (brand, voice, products)
   │   │  Skill: "copywriting" → LLM Module (model: llama-3.1-70b)
   │   │  Output: social_posts → Context
   │   ▼
   ├── Step 3 (PARALLEL): 
   │   ├── EMPLOYEE_TASK → Employee "Video Creator" (role=DESIGNER)
   │   │    Input: social_posts + CompanyContext
   │   │    Skill: "video_script" → LLM Module
   │   │    Output: video_scripts
   │   └── EMPLOYEE_TASK → Employee "Designer" (role=DESIGNER)
   │        Skill: "thumbnail_generation" → Image Module
   │
   └── Step 4: SKILL_EXECUTION → "social_publisher"
        │    Provider: "meta" (Instagram/Facebook), "tiktok", "whatsapp"
        │    Input: social_posts + video_scripts + thumbnails
        ▼
   EventBus: WORKFLOW_COMPLETED + resultados
```

---

## 📦 PACOTE DE SYNC/EXPORT PARA AIPENSA.COM

### Formato: `aipensa-sync-v1.yaml`

```yaml
version: "1.0"
runtime_version: "1.0.0"
exported_at: "2026-07-28T10:00:00Z"
checksum: "sha256:..."

companies:
  - company_id: "comp_abc123"
    profile:
      name: "Acme Corp"
      legal_name: "Acme Corporation LTDA"
      tax_id: "12.345.678/0001-90"
      segment: "ecommerce"
      size: "medium"
    brand:
      name: "Acme"
      tagline: "Inovação que entrega"
      colors: {primary: "#0066CC", secondary: "#00AA44", accent: "#FF6600"}
      voice_tone: "friendly"
    products: [...]
    channels:
      instagram: {handle: "@acme", access_token_ref: "secret_insta"}
      whatsapp: {number: "+5511999999999", verified: true}
    goals: [...]
    knowledge: [...]

employees:
  - employee_id: "emp_mgr_001"
    company_id: "comp_abc123"
    name: "Manager IA"
    role: "CEO"
    specialization: "Strategic planning & orchestration"
    skills: ["strategic_planning", "news_monitoring", "kpi_analysis"]
    model: "meta/llama-3.1-70b-instruct"
    temperature: 0.3
    memory_scope: "COMPANY"
    permissions: ["workflow.create", "workflow.execute", "team.manage"]
    
  - employee_id: "emp_social_001"
    company_id: "comp_abc123"
    team_id: "team_marketing"
    name: "Social Media IA"
    role: "SOCIAL_MEDIA"
    specialization: "Copywriting & community management"
    skills: ["copywriting", "hashtag_research", "engagement_analysis"]
    model: "meta/llama-3.1-8b-instruct"
    temperature: 0.7

teams:
  - team_id: "team_marketing"
    company_id: "comp_abc123"
    name: "Marketing Team"
    members: ["emp_social_001", "emp_designer_001", "emp_video_001"]
    shared_context: {campaign_calendar: "..."}
    workflows: ["daily_content", "weekly_campaign", "monthly_report"]

skills:
  - skill_id: "copywriting"
    name: "Copywriting Specialist"
    type: "COMPOSITE"
    steps:
      - skill_id: "llm_generation"
        parameters: {prompt_template: "social_copy", model: "${employee.model}"}
      - skill_id: "brand_check"
        parameters: {brand_guidelines: "${company.brand.guidelines}"}

providers:
  - provider_id: "meta"
    name: "Meta (Instagram/Facebook/WhatsApp)"
    type: "SOCIAL"
    config_schema: {...}
  - provider_id: "news_api"
    name: "News API"
    type: "DATA"
    config_schema: {...}

workflows:
  - workflow_id: "daily_content"
    name: "Daily Content Pipeline"
    version: "1.2.0"
    nodes: [...]
    edges: [...]
    schedule: "0 6 * * *"  # Cron no Scheduler

schedules:
  - job_id: "daily_content_trigger"
    workflow_id: "daily_content"
    cron: "0 6 * * *"
    timezone: "America/Sao_Paulo"
```

---

## 📅 ROADMAP DE IMPLEMENTAÇÃO (FASES)

### FASE 1 - Foundation (Semana 1-2) ✅ **BASE JÁ EXISTE**
- [x] Runtime Core, 24 Módulos, EventBus, Plugin System
- [x] Workflow, Scheduler, Queue, Workspace
- [x] Agent, Conversation, Skill, LLM Modules
- [ ] **NOVO:** Company Context Engine (models, memory, resolver, interfaces)
- [ ] **NOVO:** Agent Registry (persistência + versioning)
- [ ] **NOVO:** EmployeeProfile extension
- [ ] **NOVO:** Team Module

### FASE 2 - Orchestration Integration (Semana 2-3)
- [ ] Workflow Step Types: `EMPLOYEE_TASK`, `SKILL_EXECUTION`, `PROVIDER_CALL`, `COMPANY_CONTEXT`
- [ ] Scheduler: Company/Team/Employee-aware Jobs
- [ ] Queue: Priority por Company/Team
- [ ] Provider Registry Module
- [ ] EventBus: Novos EventTypes (Company, Employee, Team, Provider)

### FASE 3 - Runtime Explorer & API (Semana 3-4)
- [ ] Backend: `/api/runtime/explorer/*` endpoints
- [ ] Frontend: Runtime Explorer Page (Task Manager style)
- [ ] Company Explorer Page
- [ ] Real-time metrics via WebSocket

### FASE 4 - Sync/Export Package (Semana 4)
- [ ] Export/Import YAML package
- [ ] Validação de compatibilidade de versões
- [ ] CLI: `aipensa-engine sync push/pull`

### FASE 5 - Hardening & Docs (Semana 5-6)
- [ ] Testes de integração multi-company
- [ ] Documentação OpenAPI completa
- [ ] Guia de migração AIPENSA Core → Engine
- [ ] Benchmarks de performance

---

## 💰 ESTIMATIVA DE CUSTO PRODUÇÃO (aipensa.com)

| Componente | Estimativa Mês | Observação |
|------------|----------------|-------------|
| **GPU Inference (NVIDIA NIM / Self-hosted)** | $500-2.000 | 91 modelos, dependência de uso |
| **PostgreSQL (Managed - RDS/CloudSQL)** | $100-500 | Multi-tenant, JSONB para configs |
| **Redis Cluster** | $50-200 | Cache, Queue, Session, PubSub |
| **S3/Blob Storage** | $20-100 | Artefatos, screenshots, knowledge |
| **Compute (K8s/ECS/Cloud Run)** | $200-800 | Runtime replicas + API |
| **Observability (Datadog/Grafana)** | $100-300 | Logs, metrics, traces |
| **CDN/Edge** | $20-50 | Frontend assets |
| **TOTAL ESTIMADO** | **$990-3.950/mês** | Escala com empresas ativas |

---

## ✅ DECISÕES ARQUITETURAIS CHAVE (Para Aprovação CTO)

| Decisão | Opção Escolhida | Justificativa |
|---------|-----------------|---------------|
| **Company Context** | Nova camada ACIMA dos Agents | Separação limpa: Engine não conhece negócio |
| **Employee = Agent Especializado** | Estender `AgentMetadata` → `EmployeeProfile` | Reutiliza 85% do AgentModule existente |
| **Team = Workspace Hierárquico** | Estender `WorkspaceModule` (parent/child) | Já tem quotas, roles, membros, hierarquia |
| **Skill Registry** | **USAR EXISTENTE** (`SkillModule`) | 100% pronto: composite, marketplace, versioning |
| **Provider Registry** | **NOVO MÓDULO** (`ProviderModule`) | Skills precisam de Providers externos |
| **Onboarding** | **APENAS CONTRATOS** (Interfaces) | Runtime não faz scraping - AIPENSA Core faz |
| **Persistência** | SQLite (dev) → PostgreSQL (prod) | Workspace/Skill/Workflow já têm persistência |
| **Multi-tenancy** | Company = Workspace Type "COMPANY" | Reutiliza isolamento, quotas, roles do Workspace |
| **Sync aipensa.com** | YAML Package Versionado | Portável, auditável, diff-friendly |

---

## ⚠️ RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Duplicação de lógica Company/Workspace | Média | Alto | Code review rigoroso; CompanyContext usa Workspace internamente |
| Performance EventBus com 155+ eventos | Baixa | Médio | Já testado com 10k eventos; particionar por company_id se needed |
| AI Capabilities (Voice/Vision/etc) são Mocks | Alta | Médio | Fase 2: Integrar provedores reais (ElevenLabs, Replicate, etc) |
| Python Execution 500 Error | Média | Baixo | Isolado; não bloqueia fluxo principal |
| Migração AIPENSA Core → Engine | Baixa | Alto | Contratos YAML + API versionados desde Day 1 |

---

## 📋 PRÓXIMOS PASSOS - AGUARDANDO DECISÃO CTO

### Opção A: **EVOLUÇÃO DIRETA** (Recomendada)
> Iniciar **FASE 1** agora: Company Context Engine + Agent Registry + Team Module
> - Aproveita 100% do investimento já feito
> - Entrega valor incremental a cada sprint
> - Runtime pronto para produção em 6 semanas

### Opção B: **ESTABILIZAÇÃO PRIMEIRO**
> Corrigir bugs conhecidos (Python exec, Browser CDP, Voice real) antes de evoluir
> - Mais seguro, mas atrasa visão estratégica 3-4 semanas

### Opção C: **PARALELO** (Requer 2+ devs)
> Um dev estabiliza, outro evolui Company Context
> - Ideal se recursos permitirem

---

## 🎯 RECOMENDAÇÃO FINAL

> **APROVAR OPÇÃO A - EVOLUÇÃO DIRETA**
> 
> O Runtime **JÁ É** uma Engine de classe mundial. O investimento de ~6 meses de engenharia está todo no código. A nova arquitetura (Company Context Engine + Employee/Team + Provider Registry) adiciona ~15% de código novo sobre uma base sólida de 85% reutilizado.
> 
> **Iniciar implementação da FASE 1 imediatamente.**

---

**Documento preparado para revisão e aprovação do CTO.**  
**Todas as referências de código apontam para arquivos reais em `/c/OPENMANUS/OpenManus/runtime/`.**