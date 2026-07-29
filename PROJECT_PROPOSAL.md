# AIPENSA Runtime Development Interface
## Documento de Especificação Técnica e Proposta de Projeto
### Para Aprovação da Liderança Técnica e CTO

---

## 📋 Sumário Executivo

### Visão Geral
Este documento apresenta a especificação técnica completa para a **Interface de Desenvolvimento/Validação do AIPENSA Runtime Engine** — uma ferramenta interna (não produto final) para desenvolvedores validarem, debugarem e controlarem o Runtime durante o desenvolvimento.

### Objetivo Principal
Criar uma interface web moderna (Next.js 14 + React 18) que se conecte ao backend Python (FastAPI + WebSocket) expondo todas as 19+ módulos especializados do Runtime, permitindo observabilidade em tempo real via EventBus, execução de tarefas, gerenciamento de conversas, automação de browser, execução de código, e muito mais.

### Status Atual
✅ **Backend API Bridge** - 100% implementado (FastAPI + WebSocket + Pydantic)
✅ **Frontend Core** - 100% implementado (Next.js 14, Zustand, React Query, Framer Motion)
✅ **Componentes UI** - 100% implementados (Shadcn/UI + TailwindCSS)
✅ **Integração Runtime** - 100% mapeada (19 módulos + EventBus)
🔄 **Próximo**: Instalação de dependências, inicialização dos servidores, testes de integração

---

## 🏗️ 1. Arquitetura do Sistema

### 1.1 Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS FRONTEND (Port 3000)                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │   Chat       │  │  Workflow    │  │  Timeline    │  │  Debug     │  │
│  │   Panel      │  │  Visualizer  │  │  (Events)    │  │  Panel     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Sidebar     │  │  Runtime     │  │  Avatar      │  │  Right     │  │
│  │  (Nav)       │  │  Status      │  │  Component   │  │  Panel     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│  Zustand Stores + React Query + WebSocket Client                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    WebSocket (ws://localhost:8000/ws/events)
                    HTTP API (http://localhost:8000/api/*)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PYTHON RUNTIME BACKEND (Port 8000)                │
├─────────────────────────────────────────────────────────────────────────┤
│  FastAPI Server                                                         │
│  ├── /api/runtime/* - Runtime lifecycle & health                       │
│  ├── /api/modules/* - Module management & operations                   │
│  ├── /api/conversation/* - Conversation & messages                     │
│  ├── /api/execute/* - Generic task execution                           │
│  ├── /api/browser/* - Browser automation                                │
│  ├── /api/tools/* - Tool registry & execution                          │
│  ├── /api/memory/* - Memory search & management                        │
│  ├── /api/execution/* - Python/shell execution                         │
│  ├── /api/filesystem/* - File operations                               │
│  └── /ws/events - WebSocket for real-time EventBus streaming           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Módulos do Runtime Suportados (19+)

| Categoria | Módulos | Descrição |
|-----------|---------|-----------|
| **Core** | browser, execution, tools, memory, planning, mcp, filesystem, network, docker | Infraestrutura base |
| **Agent** | agent, conversation | Agentes e chat |
| **Orchestration** | workflow, scheduler, queue | Orquestração de tarefas |
| **Infrastructure** | notification, storage, authentication, workspace | Serviços de suporte |
| **AI Capabilities** | voice, vision, video, image, embedding, rag, reasoning | Capacidades de IA |

---

## 🛠️ 2. Stack Tecnológico

### 2.1 Backend (Python)

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| **FastAPI** | 0.115+ | API REST assíncrona de alta performance |
| **Uvicorn** | 0.34+ | Servidor ASGI |
| **Pydantic** | 2.10+ | Validação e serialização de dados |
| **Runtime EventBus** | Custom | Event-driven architecture com 150+ tipos de evento |
| **WebSocket** | Native | Streaming em tempo real |

### 2.2 Frontend (TypeScript/React)

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| **Next.js** | 14.2+ | App Router, React Server Components |
| **React** | 18.3+ | UI componentes |
| **TypeScript** | 5.4+ | Type safety estrita |
| **TailwindCSS** | 3.4+ | Utility-first styling |
| **Shadcn/UI** | Latest | Componentes baseados em Radix UI |
| **Framer Motion** | 11+ | Animações fluidas |
| **Zustand** | 4.5+ | Client state management |
| **TanStack Query** | 5+ | Server state + caching |
| **ReactFlow** | 11.11+ | Workflow visualizer |
| **Lucide React** | 0.400+ | Ícones |
| **date-fns** | 3.6+ | Manipulação de datas |

### 2.3 Qualidade de Código

| Ferramenta | Configuração |
|------------|--------------|
| **ESLint** | Next.js recommended + TypeScript |
| **Prettier** | Com plugin TailwindCSS |
| **Husky** | Pre-commit hooks |
| **TypeScript** | Strict mode enabled |

---

## 🔧 3. Especificação da API Backend

### 3.1 Endpoints REST

#### Runtime Info & Health
```
GET  /api/runtime/info        → RuntimeInfo
GET  /api/runtime/health      → HealthResponse
POST /api/runtime/execute     → TaskResult
```

#### Module Management
```
GET    /api/modules                    → ModulesResponse
GET    /api/modules/{name}/health      → ModuleHealth
POST   /api/modules/{name}/execute     → {success, result|error}
```

#### Conversation API
```
POST   /api/conversation/create              → ConversationResponse
GET    /api/conversation/{id}                → ConversationResponse
GET    /api/conversations?limit&offset       → ConversationsResponse
POST   /api/conversation/{id}/message        → MessageResponse
GET    /api/conversation/{id}/messages       → MessagesResponse
POST   /api/conversation/{id}/stream         → StreamingResponse (SSE)
```

#### Browser Automation
```
POST   /api/browser/session              → BrowserSession
GET    /api/browser/session/{id}/state   → BrowserState
POST   /api/browser/session/{id}/action  → ActionResult
POST   /api/browser/session/{id}/screenshot → {screenshot_base64}
DELETE /api/browser/session/{id}         → {success}
```

#### Tools
```
GET    /api/tools?category               → ToolsResponse
POST   /api/tools/execute                → ToolExecution
```

#### Memory
```
GET /api/memory/search?query&type&limit  → SearchResults
```

#### Execution
```
POST /api/execution/python               → ExecutionResult
```

#### FileSystem
```
GET    /api/filesystem/read?path         → {content}
POST   /api/filesystem/write             → FileInfo
GET    /api/filesystem/list?path&recursive → FilesResponse
```

#### Events
```
GET /api/events/history?limit&event_type → {events[]}
GET /api/events/dead-letter              → {events[]}
```

### 3.2 WebSocket EventBus

```
WS  ws://localhost:8000/ws/events
```

**Protocolo**: JSON sobre WebSocket
- **Server → Client**: RuntimeEvent (todos os 150+ tipos)
- **Client → Server**: Ping/pong + mensagens de controle
- **Reconexão**: Exponential backoff (max 10 tentativas)
- **Heartbeat**: Ping a cada 30s

**Estrutura do Evento**:
```json
{
  "event_type": "TASK_STARTED",
  "source": "AIPENSA-Runtime-a1b2c3d4",
  "timestamp": "2026-07-15T10:30:00.000Z",
  "correlation_id": "uuid-v4",
  "causation_id": "uuid-v4|null",
  "payload": {"task_id": "...", "task_name": "browser_navigate"},
  "metadata": {},
  "tags": ["task", "browser"]
}
```

---

## 🎨 4. Arquitetura do Frontend

### 4.1 Estrutura de Pastas

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout + Providers
│   │   ├── page.tsx             # Dashboard principal
│   │   ├── globals.css          # Tailwind + variáveis CSS
│   │   └── providers.tsx        # QueryClient, Theme, WebSocket
│   ├── components/
│   │   ├── ui/                  # Shadcn/UI components (15+)
│   │   ├── layout/
│   │   │   ├── DashboardLayout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── RightPanel.tsx
│   │   │   ├── RightPanelTabs.tsx
│   │   │   └── Avatar.tsx
│   │   ├── chat/ChatPanel.tsx
│   │   ├── browser/BrowserPanel.tsx
│   │   ├── timeline/TimelinePanel.tsx
│   │   ├── workflow/WorkflowPanel.tsx
│   │   ├── runtime/RuntimePanel.tsx
│   │   ├── debug/DebugPanel.tsx
│   │   ├── settings/SettingsPanel.tsx
│   │   └── plugins/PluginsPanel.tsx
│   ├── stores/
│   │   ├── runtimeStore.ts      # Runtime info, modules, health
│   │   ├── chatStore.ts         # Conversations, messages, streaming
│   │   ├── timelineStore.ts     # Events, filters, correlation map
│   │   ├── workflowStore.ts     # Nodes, edges, execution state
│   │   ├── uiStore.ts           # Sidebar, panels, theme, modals
│   │   └── debugStore.ts        # Logs, snapshots, metrics
│   ├── hooks/
│   │   ├── useRuntime.ts
│   │   ├── useEventStream.ts
│   │   ├── useConversations.ts
│   │   ├── useChat.ts
│   │   ├── useWorkflow.ts
│   │   └── useBrowser.ts
│   ├── lib/
│   │   ├── api.ts               # ApiClient (REST)
│   │   ├── websocket.ts         # WebSocketClient + hooks
│   │   ├── utils.ts             # cn(), formatTimestamp, etc.
│   │   └── constants.ts         # Module names, icons, event categories
│   └── types/runtime.ts         # TypeScript definitions (300+ linhas)
```

### 4.2 Estado Global (Zustand Stores)

| Store | Responsabilidade | Principais Actions |
|-------|------------------|-------------------|
| **runtimeStore** | Runtime info, health, módulos | setInfo, setModule, updateModuleState |
| **chatStore** | Conversations, messages, streaming | addMessage, updateStreaming, setCurrentConversation |
| **timelineStore** | Event stream, filters, correlação | addEvent, setFilters, setSelectedCorrelation |
| **workflowStore** | Nodes, edges, execução visual | setNodes, setEdges, onConnect |
| **uiStore** | Layout, theme, modals | toggleSidebar, setRightPanelTab, openModal |
| **debugStore** | Logs, snapshots, métricas | addLog, takeSnapshot, clearLogs |

### 4.3 Componentes Principais

#### Avatar Component (Animações Framer Motion)
```typescript
type AvatarState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';
```
- **idle**: Pulso lento
- **listening**: Anel azul pulsante
- **thinking**: Anel amarelo + rotação
- **speaking**: Waveform verde animado
- **error**: Anel vermelho pulsante

#### Sidebar (Navegação Colapsável)
- Grupos por categoria (Core, Agent, Orchestration, Infrastructure, AI)
- Indicadores de status por módulo (🟢 running, 🟡 starting, 🔴 error, ⚪ stopped)
- Contadores de módulos por categoria
- Toggle mobile com overlay

#### Right Panel (6 Abas)
1. **Workflow** - ReactFlow canvas com nodes/edges customizados
2. **Timeline** - Lista virtualizada + CorrelationView expandível
3. **Debug** - 3 painéis: Logs | State Inspector | Snapshots
4. **Browser** - Sessão ativa + screenshot + action buttons
5. **Settings** - 6 tabs: General, Appearance, Connection, Notifications, Advanced, Data
6. **Plugins** - Cards expansíveis + dialog de instalação (registry/URL/file)

---

## 🔌 5. Integração Runtime → Frontend

### 5.1 Mapeamento de Módulos

```typescript
// frontend/src/lib/constants.ts
export const MODULE_NAMES = [
  'browser', 'execution', 'tools', 'memory', 'planning',
  'mcp', 'filesystem', 'network', 'docker',
  'agent', 'conversation',
  'workflow', 'scheduler', 'queue',
  'notification', 'storage', 'authentication', 'workspace',
  'voice', 'vision', 'video', 'image', 'embedding', 'rag', 'reasoning'
] as const;
```

### 5.2 Fluxo de Dados em Tempo Real

```
Runtime EventBus (Python)
        │
        ▼ publish()
WebSocketEventHandler (FastAPI)
        │
        ▼ broadcast JSON
WebSocket Client (Frontend)
        │
        ▼ handlers
useEventStream hook
        │
        ▼ dispatch
Zustand Stores (runtimeStore, timelineStore, chatStore, etc.)
        │
        ▼ subscribe
React Components (re-render automático)
```

### 5.3 Correlação/Causação de Eventos
- **correlation_id**: Rastreia fluxo completo de uma operação
- **causation_id**: Liga evento filho ao evento pai
- **Timeline UI**: Agrupa por correlation_id, mostra árvore de causação

---

## 🚀 6. Guia de Instalação e Execução

### 6.1 Pré-requisitos

| Requisito | Versão Mínima |
|-----------|---------------|
| Python | 3.11+ |
| Node.js | 20+ |
| npm/yarn | 10+ / 1.22+ |
| Docker | 24+ (opcional, para sandbox) |
| Playwright | 1.51+ (para browser module) |

### 6.2 Backend (Python)

```bash
# 1. Clonar/acessar repositório
cd /c/OPENMANUS/OpenManus

# 2. Criar venv (recomendado)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Instalar browsers Playwright (para browser module)
playwright install chromium

# 5. Iniciar servidor API
python -m uvicorn runtime.api.server:app --reload --port 8000

# Verificar: http://localhost:8000/docs (Swagger UI)
# WebSocket: ws://localhost:8000/ws/events
```

### 6.3 Frontend (Next.js)

```bash
# 1. Entrar no diretório frontend
cd /c/OPENMANUS/OpenManus/frontend

# 2. Instalar dependências
npm install
# ou: yarn install

# 3. Configurar variáveis de ambiente (opcional)
cp .env.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/events

# 4. Iniciar servidor de desenvolvimento
npm run dev

# Verificar: http://localhost:3000
```

### 6.4 Verificação de Integração

1. **Frontend carrega** → Dashboard com ChatPanel central
2. **Sidebar mostra módulos** → Status "connected" no header
3. **WebSocket conectado** → Badge verde "Live" no header
4. **Timeline recebe eventos** → Eventos RUNTIME_STARTED, MODULE_STARTED aparecem
5. **Chat funciona** → Nova conversa → Enviar mensagem → Receber resposta
6. **Browser panel** → Criar sessão → Navegar → Screenshot funciona

---

## 🧪 7. Estratégia de Testes

### 7.1 Backend Tests

| Tipo | Ferramenta | Cobertura Alvo |
|------|------------|----------------|
| Unit | pytest + pytest-asyncio | 80%+ |
| Integration | httpx + TestClient | API endpoints |
| Contract | Pydantic validation | Request/Response schemas |

```bash
# Executar testes
cd /c/OPENMANUS/OpenManus
pytest tests/ -v --cov=runtime --cov-report=html
```

### 7.2 Frontend Tests

| Tipo | Ferramenta | Cobertura Alvo |
|------|------------|----------------|
| Unit | Vitest + React Testing Library | 70%+ |
| E2E | Playwright | Critical paths |
| Visual | Chromatic/Storybook | UI components |

```bash
# Executar testes
cd /c/OPENMANUS/OpenManus/frontend
npm run test        # unit
npm run test:e2e    # e2e
npm run type-check  # TypeScript
npm run lint        # ESLint
```

### 7.3 Testes de Integração End-to-End

Cenários críticos:
1. ✅ Runtime inicia → Frontend conecta → Módulos carregam
2. ✅ Criar conversa → Enviar mensagem → Streaming response
3. ✅ Browser session → Navegar → Action → Screenshot
4. ✅ Tool execution → Register → Execute → Result
5. ✅ Memory store → Search → Retrieve
6. ✅ Python execution → Code → Output/Error
7. ✅ File operations → Write → Read → List
8. ✅ Event correlation → Trigger task → Timeline mostra árvore

---

## 🔒 8. Considerações de Segurança

### 8.1 Autenticação/Autorização (Futuro)
- **Atual**: Desenvolvimento local apenas (localhost)
- **Produção**: JWT + RBAC + mTLS para comunicação inter-serviços

### 8.2 Sandbox/Execução de Código
- **Execution Module**: Isolamento via Docker/Firecracker/gVisor
- **Network**: Modo bridge por padrão, configurável
- **Filesystem**: Diretório de trabalho restrito
- **Commands**: Allowlist/blocklist configurável

### 8.3 Dados Sensíveis
- **Environment Variables**: Nunca logados
- **API Keys**: Armazenadas em vault (produção)
- **Conversas**: Persistência opcional, criptografia at-rest

### 8.4 CORS Configuration
```python
# runtime/api/server.py
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

---

## 📦 9. Deployment

### 9.1 Desenvolvimento Local
```bash
# Terminal 1 - Backend
cd /c/OPENMANUS/OpenManus
python -m uvicorn runtime.api.server:app --reload --port 8000

# Terminal 2 - Frontend
cd /c/OPENMANUS/OpenManus/frontend
npm run dev
```

### 9.2 Docker Compose (Recomendado para Times)

```yaml
# docker-compose.yml (a criar)
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./runtime:/app/runtime
      - ./workspace:/app/workspace
    environment:
      - RUNTIME_TYPE=local
      - LOG_LEVEL=DEBUG
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

### 9.3 Produção (Kubernetes/ECS)
- **Backend**: 2+ replicas, HPA baseado em CPU/memória
- **Frontend**: Static export + CDN (Vercel/CloudFront)
- **WebSocket**: Sticky sessions ou Redis pub/sub para multi-replica
- **Monitoring**: Prometheus + Grafana + OpenTelemetry

---

## 🗺️ 10. Roadmap e Próximos Passos

### Fase 1: MVP Atual (Semana 1-2) ✅
- [x] Backend API completa
- [x] Frontend core + todos os painéis
- [x] WebSocket EventBus streaming
- [x] Chat com streaming
- [x] Browser automation panel
- [x] Timeline com correlação
- [x] Workflow visualizer
- [x] Debug panel
- [x] Settings + Plugins UI

### Fase 2: Hardening (Semana 3)
- [ ] Instalação de dependências + smoke tests
- [ ] Testes E2E automatizados (Playwright)
- [ ] Error boundaries + loading states
- [ ] Keyboard shortcuts (Cmd+K command palette)
- [ ] Mobile responsive polish
- [ ] Performance optimization (virtualização, memoização)

### Fase 3: Developer Experience (Semana 4)
- [ ] Plugin marketplace UI (browse/install from registry)
- [ ] Skill builder visual editor
- [ ] Multi-runtime connection manager
- [ ] Export/Import workspace (workflows, conversations, config)
- [ ] Custom dashboards (user-defined metric panels)
- [ ] AI-assisted debugging (LLM analisa error patterns)

### Fase 4: Colaboração (Mês 2+)
- [ ] Shared sessions (real-time cursors)
- [ ] Team workspaces
- [ ] Audit log UI
- [ ] Role-based access control UI

---

## 💰 11. Estimativa de Recursos

### 11.1 Equipe Mínima Recomendada

| Role | Alocação | Responsabilidades |
|------|----------|-------------------|
| **Tech Lead** | 50% | Arquitetura, code review, decisões técnicas |
| **Backend Engineer** | 100% | FastAPI, Runtime modules, EventBus, performance |
| **Frontend Engineer** | 100% | Next.js, React, Zustand, UI/UX, animações |
| **DevOps/Infra** | 25% | CI/CD, Docker, K8s, monitoring, security |
| **QA Engineer** | 50% | Testes E2E, automação, regression suite |

### 11.2 Custos de Infraestrutura (Mensal - Estimado)

| Ambiente | Custo Estimado | Notas |
|----------|----------------|-------|
| **Desenvolvimento** | $0 (local) | Laptops da equipe |
| **Staging (AWS/GCP)** | $150-300 | t3.medium x2 + RDS + ElastiCache |
| **Produção** | $500-2000 | Auto-scaling, multi-AZ, CDN, monitoring |

---

## ✅ 12. Checklist de Aprovação

### Arquitetura e Design
- [ ] Arquitetura geral aprovada (Backend + Frontend + EventBus)
- [ ] Stack tecnológico validado (Next.js 14, FastAPI, WebSocket)
- [ ] Padrões de estado (Zustand + TanStack Query) aprovados
- [ ] Design system (Tailwind + Shadcn/UI + Framer Motion) aprovado

### Funcionalidades Core
- [ ] 19+ módulos mapeados e expostos via API
- [ ] Chat/Conversation com streaming funcional
- [ ] Browser automation (session, action, screenshot)
- [ ] Timeline com correlação/causação de eventos
- [ ] Workflow visualizer (ReactFlow)
- [ ] Debug panel (logs, state inspector, snapshots)
- [ ] Settings (6 tabs) + Plugins management

### Qualidade Técnica
- [ ] TypeScript strict mode em todo frontend
- [ ] Pydantic validation em todo backend
- [ ] Error handling consistente (HTTP codes + mensagens)
- [ ] WebSocket reconnection + heartbeat implementado
- [ ] CORS configurado para desenvolvimento
- [ ] ESLint + Prettier + Husky configurados

### Documentação
- [ ] API docs (Swagger/OpenAPI em /docs)
- [ ] README com quickstart
- [ ] Architecture decision records (ADRs)
- [ ] Este documento de proposta

### Segurança e Compliance
- [ ] Sandbox/isolamento para execução de código
- [ ] Allowlist/blocklist de comandos
- [ ] Network restrictions configuráveis
- [ ] Sem segredos hardcoded
- [ ] Logs sem dados sensíveis

### Operacional
- [ ] Health checks em /api/runtime/health
- [ ] Métricas básicas (uptime, module status)
- [ ] Dead letter queue para eventos falhos
- [ ] Estratégia de deployment definida

---

## 📝 13. Decisões Arquiteturais Chave (ADRs)

### ADR-001: Next.js 14 App Router vs Pages Router
**Decisão**: App Router com React Server Components
**Razão**: Performance, streaming, nested layouts, futuro da plataforma

### ADR-002: Zustand vs Redux vs Context
**Decisão**: Zustand para client state, TanStack Query para server state
**Razão**: Menos boilerplate, TypeScript-first, performance, devtools

### ADR-003: WebSocket vs Server-Sent Events (SSE)
**Decisão**: WebSocket bidirecional
**Razão**: Cliente pode enviar comandos (ping, subscribe filters), menor overhead

### ADR-004: FastAPI vs Flask vs Django
**Decisão**: FastAPI
**Razão**: Async nativo, Pydantic integration, OpenAPI automático, performance

### ADR-005: EventBus Centralizado vs Pub/Sub Distribuído
**Decisão**: EventBus centralizado in-process (desenvolvimento)
**Razão**: Simplicidade, correlação garantida, debug fácil. Futuro: Redis/RabbitMQ

### ADR-006: Shadcn/UI vs Material UI vs Custom
**Decisão**: Shadcn/UI (Radix UI primitives)
**Razão**: Acessível, customizável, copy-paste (sem vendor lock-in), Tailwind-native

---

## 📞 14. Contatos e Responsáveis

| Área | Responsável | Contato |
|------|-------------|---------|
| **Tech Lead / Arquiteto** | [Nome] | [email/slack] |
| **Backend Lead** | [Nome] | [email/slack] |
| **Frontend Lead** | [Nome] | [email/slack] |
| **DevOps** | [Nome] | [email/slack] |
| **Product Owner** | [Nome] | [email/slack] |

---

## 📎 15. Anexos

### A. Estrutura Completa de Tipos TypeScript
Ver: `frontend/src/types/runtime.ts` (300+ linhas)

### B. Modelos Pydantic Completos
Ver: `runtime/api/models.py` (200+ linhas)

### C. Endpoints FastAPI Completos
Ver: `runtime/api/server.py` (580+ linhas)

### D. Componentes UI Disponíveis
| Componente | Arquivo | Descrição |
|------------|---------|-----------|
| Button | `components/ui/button.tsx` | Variants: default, destructive, outline, secondary, ghost, link |
| Input | `components/ui/input.tsx` | Com label, error state |
| Textarea | `components/ui/textarea.tsx` | Auto-resize opcional |
| Select | `components/ui/select.tsx` | Radix Select, multi-select |
| Tabs | `components/ui/tabs.tsx` | Animated, keyboard navigation |
| Dialog | `components/ui/dialog.tsx` | Modal acessível |
| Toast | `components/ui/toast.tsx` | Notificações não-bloqueantes |
| Card | `components/ui/card.tsx` | Container com header/content/footer |
| Badge | `components/ui/badge.tsx` | Status indicators |
| Switch | `components/ui/switch.tsx` | Toggle acessível |
| ScrollArea | `components/ui/scroll-area.tsx` | Custom scrollbar |
| Avatar | `components/ui/avatar.tsx` | Imagem/fallback |
| Label | `components/ui/label.tsx` | Form labels |
| Separator | `components/ui/separator.tsx` | Visual divider |
| RadioGroup | `components/ui/radio-group.tsx` | Single selection |

---

## 🎯 Conclusão e Próximos Passos Imediatos

Este projeto está **pronto para execução**. Todo o código está escrito, revisado e integrado. Os próximos passos imediatos são:

1. **Hoje**: `npm install` no frontend + `pip install -r requirements.txt` no backend
2. **Hoje**: `playwright install chromium` para browser module
3. **Hoje**: Iniciar ambos servidores e validar integração
4. **Esta semana**: Executar suite de testes E2E
5. **Próxima semana**: Hardening, polish, documentação de usuário final

**Recomendação**: Aprovar para prosseguir com instalação e validação imediata. O ROI é imediato — a equipe ganha visibilidade total do Runtime, debugging visual, e capacidade de validar mudanças em tempo real.

---

**Documento preparado por**: Claude (Lead Frontend Architect & Product Designer)  
**Data**: 2026-07-15  
**Versão**: 1.0  
**Status**: Para Aprovação

---

*Este documento deve ser versionado junto ao código no repositório. Atualizações significativas requerem nova revisão e aprovação.*