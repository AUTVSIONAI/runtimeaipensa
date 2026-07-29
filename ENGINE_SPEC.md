# 📜 ENGINE_SPEC.md - Especificação Principal da AIPENSA Engine

**Versão:** 1.0  
**Status:** Constituição Oficial - Imutável sem aprovação do CTO  
**Data:** 28 Julho 2026  
**Autor:** Arquiteto de Software Sênior / CTO Office  

---

## 🏛️ 1. FILOSOFIA DA ENGINE

> **"A Engine é o Kernel. O Core é o Produto."**

A **AIPENSA Engine** é uma **Runtime Engine de propósito geral** para orquestração de agentes de IA, workflows, habilidades e provedores. Ela **não conhece regras de negócio**, **não implementa features de produto** e **não toma decisões de domínio**.

### Princípios Fundamentais

| Princípio | Descrição |
|-----------|-----------|
| **General Purpose** | Qualquer domínio (e-commerce, clínica, delivery, SaaS) roda na mesma Engine |
| **Zero Business Logic** | Nenhum `if company.segment == "ecommerce"` no código da Engine |
| **Plugin-First** | Toda capacidade externa é um Plugin. Core não cresce por features. |
| **Event-Driven** | Todo estado mutável emite Evento. EventBus é a source of truth. |
| **Decoupled by Contract** | Engine ↔ Core comunicam apenas via API/Eventos versionados. |
| **Observable by Default** | Logs, métricas, traces, eventos - tudo instrumentado nativamente. |
| **Multi-Tenant Native** | Isolamento, quotas, roles, hierarquia desde o Day 1. |

---

## 🎯 2. RESPONSABILIDADES DA ENGINE

### ✅ O QUE A ENGINE FAZ

| Domínio | Responsabilidades |
|---------|-------------------|
| **Runtime Lifecycle** | Start/Stop/Restart/HealthCheck de módulos e plugins |
| **Module Registry** | Descoberta, carregamento, versionamento, dependências de 24+ módulos |
| **Agent Execution** | Lifecycle de Agents/Employees: create, start, stop, message passing, task queue |
| **Workflow Orchestration** | DAG execution: paralelo, condicional, loop, retry, pause/resume/cancel |
| **Scheduler** | Cron/Interval/Once/Delayed jobs com persistência e concorrência controlada |
| **Queue System** | FIFO/LIFO/Priority/Delayed + Dead Letter + Backpressure + Consumers |
| **Skill Registry** | Builtin/Custom/Composite/AI-Generated + Marketplace + Versioning + Deps |
| **Provider Registry** | Conexões externas (Meta, Twilio, OpenAI, AWS, etc) - credenciais, escopos, status |
| **Conversation** | Streaming SSE, tool calls, context window, persistence, multi-turn |
| **Memory** | Typed stores, inverted index, TTL, embeddings, vector search, persistence |
| **LLM Abstraction** | Multi-provider (NVIDIA NIM 91 free, OpenAI, Anthropic), cost tracking, templates |
| **Browser Automation** | Playwright sessions, actions, screenshots, CDP, element inspection |
| **Code Execution** | Python sandbox, package install, env vars, timeout, resource limits |
| **FileSystem** | Read/Write/List/Watch com sandbox paths |
| **Network/HTTP** | Request/Download/Stream com retry, timeout, auth |
| **Docker** | Container lifecycle, exec, logs, networks, volumes |
| **MCP** | Model Context Protocol client/server |
| **Planning** | LLM-based task decomposition |
| **Notifications** | Email, Webhook, Push, In-app |
| **Storage** | Blob, KV, bucket management |
| **Auth** | Tokens, API Keys, ACL, RBAC |
| **Workspace** | Hierárquico, multi-tenant, quotas, roles (OWNER/ADMIN/MEMBER/VIEWER/GUEST) |
| **AI Capabilities** | Voice, Vision, Video, Image, Embedding, RAG, Reasoning (via Providers) |
| **Event Bus** | 155+ tipos, correlation/causation, priority, DLQ, filters, WebSocket broadcast |
| **Plugin System** | 11 PluginTypes, auto-discovery, lifecycle, hot-reload, marketplace |

---

### ❌ O QUE A ENGINE **NUNCA** FAZ

| Categoria | Proibido na Engine | Onde Pertence |
|-----------|-------------------|---------------|
| **Business Rules** | `if order.value > 1000: approve()` | AIPENSA Core (Skills/Workflows) |
| **Domain Models** | `class Order`, `class Patient`, `class Product` | AIPENSA Core (Company Memory) |
| **UI/UX Logic** | Render React, HTML, CSS, componentes visuais | AIPENSA Core (Frontend) |
| **External Scraping** | `fetch_instagram()`, `scrape_google_maps()` | AIPENSA Core (Onboarding Adapters) |
| **Integrations Específicas** | `send_whatsapp_template()`, `create_meta_ad()` | Providers (implementados no Core) |
| **Authentication Negócio** | `login_with_cpf()`, `validate_cnpj()` | AIPENSA Core (Auth Providers) |
| **Relatórios de Negócio** | `generate_monthly_sales_report()` | Workflows/Skills do Core |
| **Dashboards Específicos** | `render_kpi_dashboard()` | AIPENSA Core (Frontend) |
| **Migração de Dados Legados** | `migrate_from_vtex()`, `import_erp_totvs()` | AIPENSA Core (ETL Skills) |
| **Compliance Setorial** | LGPD, HIPAA, PCI-DSS logic | AIPENSA Core (Compliance Skills) |

> **Regra de Ouro:** Se o código contém conhecimento sobre *como um negócio específico opera*, ele **NÃO** pertence à Engine.

---

## 🔄 3. SEPARAÇÃO ENGINE ↔ AIPENSA CORE

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AIPENSA CORE (Produto)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │   CRM       │  │  Delivery   │  │  Finance    │  │ Clinics   │  │
│  │   Vertical  │  │  Vertical   │  │  Vertical   │  │ Vertical  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘  │
│         │                │                │               │         │
│         └────────────────┼────────────────┼───────────────┘         │
│                          ▼                ▼                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              COMPANY CONTEXT LAYER (Core)                   │   │
│  │  CompanyProfile │ Brand │ Products │ Channels │ Goals │ KB  │   │
│  │  Onboarding Adapters (Instagram, CRM, WhatsApp, Website)   │   │
│  │  Employee Definitions (Marketing, Finance, Support, etc)   │   │
│  │  Workflows de Negócio  │  Skills Compostas  │  Providers   │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │  HTTP + WebSocket (Versioned API)  │
└───────────────────────────────┼────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AIPENSA ENGINE (Runtime)                       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            │
│  │Agent   │ │Workflow│ │Scheduler│ │Queue   │ │Skill   │  ... 24  │
│  │Module  │ │Module  │ │Module  │ │Module  │ │Module  │  Módulos  │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    EVENT BUS (Source of Truth)              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            │
│  │Plugin  │ │Provider│ │Memory  │ │LLM     │ │Browser │  Plugins │
│  │Manager │ │Registry│ │Module  │ │Module  │ │Module  │            │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

### Contrato de Dependência

```
AIPENSA Core  ──depends on──▶  AIPENSA Engine
       │                            │
       │  HTTP API (REST)           │
       │  WebSocket (Events)        │
       │  YAML Sync Package         │
       ▼                            ▼
  Engine NUNCA importa Core      Core SEMPRE importa Engine
```

---

## 🏗️ 4. PRINCÍPIOS ARQUITETURAIS

### 4.1 Layered Architecture (Strict)

```
Layer 5: EXTERNAL INTERFACES     → HTTP API, WebSocket, CLI, SDK
Layer 4: ORCHESTRATION           → Workflow, Scheduler, Queue, Planning
Layer 3: INTELLIGENCE            → Agent, Conversation, Skill, LLM, Provider
Layer 2: CAPABILITIES            → Browser, Execution, FS, Network, Docker, MCP
Layer 1: FOUNDATION              → Memory, Storage, Auth, Notification, Workspace
Layer 0: KERNEL                  → Runtime, ModuleRegistry, EventBus, PluginManager
```

**Regra:** Camada N **só** depende de camadas < N. Nunca o inverso.

### 4.2 Module Contract

Todo módulo **DEVE** implementar:

```python
class RuntimeModule(ABC):
    # Identity
    name: str                    # Único, snake_case (ex: "browser")
    version: str                 # SemVer
    metadata: ModuleMetadata     # Description, capabilities, deps
    
    # Lifecycle (obrigatório)
    async def initialize(self, runtime: "Runtime") -> None
    async def start(self) -> None
    async def stop(self) -> None
    async def health_check(self) -> ModuleHealth
    
    # Operations (opcional)
    async def execute(self, operation: str, **params) -> Any
    
    # Events (automático via decorator)
    @event_handler(EventType.MODULE_STARTED)
    async def on_started(self, event: RuntimeEvent) -> None
```

### 4.3 Plugin Types (Exaustivo)

```python
class PluginType(Enum):
    TOOL           = "tool"              # Funções chamáveis por Agents/LLM
    MCP            = "mcp"               # Model Context Protocol servers
    BROWSER        = "browser"           # Playwright/Selenium adapters
    RUNTIME        = "runtime"           # Novos RuntimeModules
    SANDBOX        = "sandbox"           # Code execution environments
    MEMORY         = "memory"            # Memory backends (Redis, PGVector, etc)
    LLM            = "llm"               # LLM Providers (OpenAI, Anthropic, NVIDIA)
    AUTH           = "auth"              # Auth providers (OAuth, SAML, OIDC)
    STORAGE        = "storage"           # Blob/KV backends (S3, GCS, MinIO)
    NETWORK        = "network"           # HTTP clients, proxies, DNS
    CUSTOM         = "custom"            # Extensibilidade livre
```

---

## 📦 5. REGRAS PARA NOVOS MÓDULOS

| Regra | Obrigatório |
|-------|-------------|
| Herdar de `RuntimeModule` | ✅ |
| Registrar no `ModuleRegistry` | ✅ |
| Emitir eventos de lifecycle (`MODULE_STARTED/STOPPED/ERROR`) | ✅ |
| Implementar `health_check()` retornando `ModuleHealth` | ✅ |
| Declarar dependências em `metadata.dependencies` | ✅ |
| Expor operações via `execute(operation, **params)` | ✅ |
| Persistir estado via `StorageModule` (nunca arquivo local) | ✅ |
| Respeitar `ModuleState` (INITIALIZING/RUNNING/STOPPED/ERROR) | ✅ |
| Documentar todas operações no `ENGINE_API_CONTRACT.md` | ✅ |
| Tests: unit + integration + health check | ✅ |

**Proibido:**
- Importar outros módulos diretamente (usa `runtime.get_module()`)
- Manter estado em memória não recuperável
- Bloquear event loop (>100ms sem `await`)
- Hardcoded config (usa `ModuleConfig` via DI)

---

## 🔌 6. REGRAS PARA PLUGINS

| Regra | Descrição |
|-------|-----------|
| **Auto-discovery** | Plugins em `runtime/plugins/<type>/` são carregados automaticamente |
| **Manifest obrigatório** | `plugin.yaml` com: name, version, type, entry_point, capabilities, config_schema |
| **Isolamento** | Plugins rodam no mesmo processo mas com config/state isolados |
| **Hot-reload** | `PluginManager.reload(plugin_id)` suportado em dev |
| **Versionamento** | SemVer no manifest. Engine valida compatibilidade na carga |
| **Dependências** | Declaradas no manifest. Engine resolve ordem de inicialização |
| **Config Schema** | JSON Schema válido. Engine valida na instalação |
| **Health Check** | Plugins DEVEM implementar `health_check()` |
| **Eventos** | Podem subscrever/emitir via `EventBus` injetado |

---

## 🎯 7. REGRAS PARA SKILLS

| Regra | Descrição |
|-------|-----------|
| **Tipos válidos** | `BUILTIN`, `CUSTOM`, `INTEGRATION`, `COMPOSITE`, `AI_GENERATED` |
| **Executor obrigatório** | Toda Skill tem `SkillExecutor` (Function/Composite/Provider) |
| **Composite = DAG** | Skills compostas são mini-workflows (steps + edges) |
| **Marketplace** | Skills publicáveis, versionadas, com dependências |
| **Rate Limiting** | Configurável por skill (requests/min, tokens/min) |
| **Permissões** | Scopes: `company`, `team`, `employee`, `personal` |
| **Input/Output Schema** | JSON Schema obrigatório para validação |
| **Idempotência** | Skills DEVEM ser idempotentes (mesmo input = mesmo output) |
| **Observabilidade** | Emit `SKILL_EXECUTED`, `SKILL_FAILED`, `SKILL_STARTED` |

---

## 🌐 8. REGRAS PARA PROVIDERS

| Regra | Descrição |
|-------|-----------|
| **Abstração** | Provider = Credenciais + Capabilities + Config Schema + Health Check |
| **Tipos** | `LLM`, `SOCIAL`, `COMMUNICATION`, `STORAGE`, `PAYMENT`, `AI_SERVICE`, `DATA` |
| **Conexão** | `ProviderConnection` = instância credenciada para uma Company |
| **OAuth Support** | Providers DEVEM suportar fluxo OAuth 2.0 + refresh tokens |
| **Scoped Credentials** | Credenciais criptografadas, escopo por Company/Team |
| **Capabilities Discovery** | `provider.discover_capabilities()` retorna operações disponíveis |
| **Rate Limits** | Respeitar headers `X-RateLimit-*` e implementar backoff |
| **Fallback** | Chain de providers por capability (ex: LLM: NVIDIA → OpenAI → Anthropic) |

---

## 👥 9. REGRAS PARA EMPLOYEES (Agents Especializados)

| Regra | Descrição |
|-------|-----------|
| **Herança** | `EmployeeProfile` extende `AgentMetadata` |
| **Roles Fixos** | `CEO`, `MARKETING`, `FINANCE`, `SUPPORT`, `DESIGNER`, `EDITOR`, `SOCIAL_MEDIA`, `HR`, `LEGAL`, `DELIVERY` |
| **Especialização** | Prompt base + Skills permitidas + Model config + Permissions |
| **Memory Scope** | `COMPANY` (global), `TEAM` (compartilhado), `PERSONAL` (isolado) |
| **Versioning** | `EmployeeProfile.version` - SemVer. Rollback suportado |
| **Ativação** | `enabled: bool` - permite desligar sem deletar |
| **Team Membership** | Um Employee pertence a 1 Team (pode ser `null`) |
| **Configuration** | JSON configurável: model, temperature, max_tokens, tools, skills |

---

## 🏢 10. REGRAS PARA COMPANY CONTEXT

| Regra | Descrição |
|-------|-----------|
| **Engine-Agnostic** | Engine NÃO conhece schemas Company. Core define, Engine armazena. |
| **Typed Memory** | `CompanyMemory` usa `MemoryModule` com stores tipados por schema |
| **Resolver Pattern** | `CompanyContextResolver.resolve_for(employee_id) → Dict` |
| **Onboarding = Interfaces** | Engine define `OnboardingSource` Protocol. Core implementa. |
| **Context Injection** | Injetado em: Employee system_prompt, Skill execution, Workflow variables |
| **Cache** | Resolver cacheia por `company_id` + `employee_role` (TTL configurável) |
| **Event Sourcing** | Mudanças em Company Context emitem `COMPANY_KNOWLEDGE_STORED/UPDATED` |

---

## 💻 11. CONVENÇÕES DE CÓDIGO

### Python (Runtime/Backend)

| Convenção | Regra |
|-----------|-------|
| **Type Hints** | Obrigatório 100% (strict mypy) |
| **Async First** | Todas I/O são `async`. Sync só para CPU-bound. |
| **Dataclasses** | `@dataclass(slots=True, frozen=True)` para DTOs |
| **Pydantic** | Para validação de input/output API |
| **Naming** | `snake_case` tudo. Classes: `PascalCase`. Constantes: `UPPER_SNAKE`. |
| **Imports** | Stdlib → Third-party → Local. `from __future__ import annotations` |
| **Error Handling** | Custom Exceptions (`EngineError`, `ModuleError`, `SkillError`) |
| **Logging** | `structlog` com `correlation_id` automático |
| **Tests** | `pytest-asyncio`, `pytest-mock`, coverage ≥ 80% |

### TypeScript (Frontend)

| Convenção | Regra |
|-----------|-------|
| **Strict Mode** | `strict: true`, `noUncheckedIndexedAccess: true` |
| **Zustand** | Client state apenas. Server state = TanStack Query |
| **Components** | Function components + hooks. Sem classes. |
| **Styling** | Tailwind + CSS Variables (design tokens) |
| **Animations** | Framer Motion. `reduceMotion` respeitado. |
| **API Client** | `openapi-typescript` + `zod` validation |
| **WebSocket** | Reconnection exponential backoff + heartbeat |

---

## 📦 12. ESTRATÉGIA DE VERSIONAMENTO

### Engine Versioning (SemVer)

```
MAJOR.MINOR.PATCH
  │     │    │
  │     │    └─ Bug fixes, hotfixes, security patches
  │     └────── Novas features compatíveis (novos módulos, endpoints, eventos)
  └──────────── Breaking changes: API removida, evento estrutural alterado, schema incompatível
```

### Versionamento por Componente

| Componente | Estratégia |
|------------|------------|
| **Runtime Core** | Engine Version (ex: v1.2.0) |
| **Módulos** | Version independentes (ex: `workflow@2.1.0`) |
| **Plugins** | Version no manifest (ex: `plugin.yaml: version: "1.0.3"`) |
| **Event Types** | Aditivos apenas. NUNCA remover/renomear. Deprecação = `@deprecated` no doc. |
| **API REST** | URL versioning: `/api/v1/`, `/api/v2/` |
| **WebSocket** | `protocol_version` no handshake |
| **Sync Package** | `sync_version` no YAML (ex: `aipensa-sync-v1.yaml`) |

### Compatibility Matrix

```
Engine v1.x  ←→  Core v1.x     ✅ Compatível
Engine v1.x  ←→  Core v2.x     ⚠️  Core deve adaptar
Engine v2.x  ←→  Core v1.x     ❌  Incompatível (breaking)
```

---

## 🔮 13. ESTRATÉGIA DE COMPATIBILIDADE FUTURA

### Princípios

1. **Additive Only** - Novos campos opcionais, novos endpoints, novos eventos
2. **Deprecation Cycle** - 2 versões MINIMAS antes de remover
3. **Migration Path** - Scripts de migração automática para breaking changes
4. **Feature Flags** - Novas funcionalidades atrás de flags (`ENGINE_FEATURE_X=1`)
5. **Schema Registry** - Avro/Protobuf para EVENTOS (futuro), JSON Schema hoje

### Garantias

| Garantia | Prazo |
|----------|-------|
| API v1 mantida | Mínimo 24 meses após v2 launch |
| Event schemas v1 | Nunca removidos, apenas deprecated |
| Plugin API | Estável dentro de Major version |
| Module interface | Estável dentro de Major version |
| Sync Package format | Forward compatible (v1 lê v2, ignora desconhecido) |

---

## 📋 14. CHECKLIST DE CONFORMIDADE (Para PRs)

Antes de merge, todo PR de Engine deve passar:

- [ ] **Zero Business Logic** - Nenhum `if company.segment`, `if order.type`, etc.
- [ ] **Interfaces Públicas Documentadas** - Atualizou `ENGINE_API_CONTRACT.md`?
- [ ] **Eventos Documentados** - Atualizou `ENGINE_EVENTS.md`?
- [ ] **Plugins/Skills/Providers** - Segue `ENGINE_PLUGIN_GUIDE.md`?
- [ ] **Type Hints 100%** - `mypy --strict` passa?
- [ ] **Testes** - Unit + Integration + Health check?
- [ ] **Observabilidade** - Logs estruturados + Eventos emitidos?
- [ ] **Multi-tenant** - Respeita `company_id`, `workspace_id`?
- [ ] **Config via DI** - Zero hardcoded config?
- [ ] **Comentários em PT-BR** - Docstrings e comentários em português?

---

## 📝 15. GOVERNANÇA

| Papel | Responsabilidade |
|-------|------------------|
| **CTO** | Aprova mudanças breaking, nova Major version, exceções a esta spec |
| **Tech Lead Engine** | Review arquitetural, merge Engine PRs, mantém docs atualizados |
| **Tech Lead Core** | Review integração Core→Engine, define Company Context schemas |
| **Contributors** | Seguem esta spec. Abrem Issue/RFC para dúvidas arquiteturais. |

### Processo de Mudança (RFC)

1. Abrir Issue com label `rfc` + template
2. Discussão mínima 48h
3. Aprovação CTO + Tech Lead Engine
4. Implementação atrás de Feature Flag
5. Rollout gradual (canary → 10% → 100%)
6. Documentação atualizada **no mesmo PR**

---

**ESTE DOCUMENTO É A CONSTITUIÇÃO. NENHUM CÓDIGO PODE CONTRARIÁ-LO.**

> *"Qualquer violação intencional desta spec deve ser tratada como bug crítico de arquitetura."*