# AIPENSA Runtime Dev Interface — Technical Architecture Document

## Para: Engineering Team
## De: Lead Frontend Architect
## Data: 2026-07-15
## Versão: 1.0

---

## 1. Visão Geral da Arquitetura

### 1.1 Princípios de Design

1. **Separation of Concerns**: Backend = Runtime API + EventBus, Frontend = Visualização + Controle
2. **Real-time First**: WebSocket como fonte de verdade para estado do Runtime
3. **Type Safety End-to-End**: Pydantic (Python) ↔ TypeScript (Frontend) com schemas compartilhados
4. **Optimistic UI**: Estado local imediato + sincronização via EventBus
5. **Modularidade**: Cada painel é independente, comunicando via stores Zustand

### 1.2 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RUNTIME EVENT BUS (Python)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Module    │  │   Module    │  │   Module    │  │    ...      │        │
│  │  (browser)  │  │ (execution) │  │  (tools)    │  │  (19 total) │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│         └────────────────┼────────────────┼────────────────┘               │
│                          ▼                                                │
│                   ┌─────────────┐                                        │
│                   │ EventBus    │                                        │
│                   │ (150+ types)│                                        │
│                   └──────┬──────┘                                        │
│                          │ publish()                                     │
└──────────────────────────┼───────────────────────────────────────────────┘
                           │
                           ▼ WebSocketEventHandler (FastAPI)
                    ┌─────────────┐
                    │  Broadcast  │◄─── active_websockets: List[WebSocket]
                    └──────┬──────┘
                           │
                    WS://localhost:8000/ws/events
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WebSocketClient (singleton)                                         │   │
│  │  - connect() / disconnect()                                         │   │
│  │  - subscribe(handler) → unsubscribe fn                              │   │
│  │  - auto-reconnect (exponential backoff)                             │   │
│  │  - heartbeat (ping 30s)                                             │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                            │
│              ┌────────────────┼────────────────┐                          │
│              ▼               ▼               ▼               ▼             │
│       ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐      │
│       │timelineStore│  │runtimeStore │  │  chatStore  │  │workflowStore│      │
│       │  (events)   │  │ (modules)   │  │(conversations)│ │ (nodes/edges)│      │
│       └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘      │
│             │               │               │               │              │
│             └───────────────┼───────────────┼───────────────┘              │
│                             ▼                                           │
│                    ┌─────────────────┐                                  │
│                    │  React Components │                                 │
│                    │  (auto re-render)   │                                 │
│                    └─────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Backend — FastAPI Server (`runtime/api/server.py`)

### 2.1 Lifespan Management

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global runtime_instance, event_handler_instance
    
    # STARTUP
    config = RuntimeConfig(runtime_type=RuntimeType.LOCAL)
    runtime_instance = await create_runtime(config)
    await event_bus.start()
    
    # Registra handler global para WebSocket broadcast
    event_handler_instance = WebSocketEventHandler()
    for event_type in RuntimeEventType:
        event_bus.subscribe(event_type, event_handler_instance)
    
    yield
    
    # SHUTDOWN
    if runtime_instance:
        await runtime_instance.stop()
    await event_bus.stop()
```

### 2.2 WebSocket Event Handler

```python
class WebSocketEventHandler(EventHandler):
    @property
    def handles_event_types(self) -> List[RuntimeEventType]:
        return list(RuntimeEventType)  # TODOS os 150+ tipos
    
    async def handle(self, event: RuntimeEvent) -> None:
        if not active_websockets:
            return
        
        event_data = event.to_dict()
        message = json.dumps(event_data)
        
        disconnected = []
        for ws in active_websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        
        # Cleanup
        for ws in disconnected:
            active_websockets.remove(ws)
```

### 2.3 REST Endpoints por Domínio

| Domínio | Endpoints | Module Backend |
|---------|-----------|----------------|
| **Runtime** | GET `/info`, GET `/health`, POST `/execute` | `Runtime` class |
| **Modules** | GET `/`, GET `/{name}/health`, POST `/{name}/execute` | `ModuleRegistry` |
| **Conversation** | POST `/create`, GET `/{id}`, GET `/`, POST `/{id}/message`, GET `/{id}/messages`, POST `/{id}/stream` | `ConversationModule` |
| **Browser** | POST `/session`, GET `/{id}/state`, POST `/{id}/action`, POST `/{id}/screenshot`, DELETE `/{id}` | `BrowserModule` |
| **Tools** | GET `/`, POST `/execute` | `ToolModule` |
| **Memory** | GET `/search` | `MemoryModule` |
| **Execution** | POST `/python` | `ExecutionModule` |
| **Filesystem** | GET `/read`, POST `/write`, GET `/list` | `FileSystemModule` |
| **Events** | GET `/history`, GET `/dead-letter` | `EventBus` |

### 2.4 Modelos Pydantic Principais (`runtime/api/models.py`)

```python
# Request Models
TaskRequestModel(type, action, params, context)
ModuleOperationRequest(operation, params)
CreateConversationRequest(title, system_prompt, context)
AddMessageRequest(role, content, message_type, metadata)
BrowserSessionRequest(url, config)
BrowserActionRequest(action, params)
ExecuteToolRequest(tool_name, arguments, context)
ExecutePythonRequest(code, sandbox_id, timeout_seconds, packages, env_vars)
WriteFileRequest(path, content, encoding, create_dirs)

# Response Models
ModuleInfo(name, state, metadata)
ConversationResponse(conversation_id, title, messages[], system_prompt, ...)
MessageResponse(message_id, role, content, type, tool_calls[], ...)
StreamingResponse(conversation_id, chunk, done, metadata)
BrowserSession(session_id, url)
BrowserState(url, title, tabs[], pixels_above, pixels_below, ...)
ToolDefinition(name, description, parameters, returns, category, tags, requires_approval)
ExecutionResult(success, output, error, execution_time)
FileInfo(path, name, size, is_dir, modified_at)
RuntimeInfo(runtime_id, name, version, status, started_at, modules{}, plugins{})
HealthResponse(runtime{}, modules{}, plugins{})
```

---

## 3. Frontend — Next.js 14 Architecture

### 3.1 Providers (`src/app/providers.tsx`)

```tsx
export function Providers({ children }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: { staleTime: 5000, refetchOnWindowFocus: false, retry: 1 }
    }
  }));

  useEffect(() => {
    wsClient.connect();
    return () => wsClient.disconnect();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        {children}
        <Toaster />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
```

### 3.2 WebSocket Client (`src/lib/websocket.ts`)

```typescript
class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Set<EventHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private pingInterval: NodeJS.Timeout | null = null;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) return;
    
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };
    
    this.ws.onmessage = (event) => {
      const runtimeEvent = JSON.parse(event.data) as RuntimeEvent;
      this.handlers.forEach(h => h(runtimeEvent));
    };
    
    this.ws.onclose = () => {
      this.stopHeartbeat();
      if (this.shouldReconnect) this.attemptReconnect();
    };
  }

  subscribe(handler: EventHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }
}
```

**Hooks disponíveis**:
- `useEventStream(handler, deps[])` — Subscreve a eventos Runtime
- `useConnectionStatus()` — Retorna boolean `connected`

### 3.3 API Client (`src/lib/api.ts`)

```typescript
class ApiClient {
  private baseUrl: string;

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`API Error: ${res.status}`);
    return res.json();
  }

  // Runtime
  getRuntimeInfo() { return this.request<RuntimeInfo>('/api/runtime/info'); }
  getHealth() { return this.request<HealthResponse>('/api/runtime/health'); }
  executeTask(task) { return this.request<TaskResult>('/api/runtime/execute', { method: 'POST', body: JSON.stringify(task) }); }

  // Modules
  listModules() { return this.request<ModulesResponse>('/api/modules'); }
  getModuleHealth(name) { return this.request<ModuleHealth>(`/api/modules/${name}/health`); }
  executeModuleOp(name, op, params) { return this.request(`/api/modules/${name}/execute`, { method: 'POST', body: JSON.stringify({ operation: op, params })}); }

  // Conversations
  createConversation(data) { return this.request('/api/conversation/create', { method: 'POST', body: JSON.stringify(data) }); }
  getConversation(id) { return this.request(`/api/conversation/${id}`); }
  listConversations(limit, offset) { return this.request(`/api/conversations?limit=${limit}&offset=${offset}`); }
  addMessage(id, data) { return this.request(`/api/conversation/${id}/message`, { method: 'POST', body: JSON.stringify(data) }); }
  getMessages(id, limit) { return this.request(`/api/conversation/${id}/messages?limit=${limit}`); }

  // Browser
  createBrowserSession(data) { return this.request('/api/browser/session', { method: 'POST', body: JSON.stringify(data) }); }
  getBrowserState(id) { return this.request(`/api/browser/session/${id}/state`); }
  browserAction(id, action, params) { return this.request(`/api/browser/session/${id}/action`, { method: 'POST', body: JSON.stringify({ action, params })}); }
  browserScreenshot(id, fullPage) { return this.request(`/api/browser/session/${id}/screenshot?full_page=${fullPage}`, { method: 'POST' }); }
  closeBrowserSession(id) { return this.request(`/api/browser/session/${id}`, { method: 'DELETE' }); }

  // Tools
  listTools(category?) { return this.request(`/api/tools${category ? `?category=${category}` : ''}`); }
  executeTool(data) { return this.request('/api/tools/execute', { method: 'POST', body: JSON.stringify(data) }); }

  // Memory
  searchMemory(query, type, limit) { return this.request(`/api/memory/search?query=${encodeURIComponent(query)}&memory_type=${type}&limit=${limit}`); }

  // Execution
  executePython(data) { return this.request('/api/execution/python', { method: 'POST', body: JSON.stringify(data) }); }

  // Filesystem
  readFile(path) { return this.request(`/api/filesystem/read?path=${encodeURIComponent(path)}`); }
  writeFile(path, content, encoding, createDirs) { return this.request('/api/filesystem/write', { method: 'POST', body: JSON.stringify({ path, content, encoding, create_dirs: createDirs })}); }
  listFiles(path, recursive) { return this.request(`/api/filesystem/list?path=${encodeURIComponent(path)}&recursive=${recursive}`); }

  // Events
  getEventHistory(limit, eventType?) { return this.request(`/api/events/history?limit=${limit}${eventType ? `&event_type=${eventType}` : ''}`); }
  getDeadLetter() { return this.request('/api/events/dead-letter'); }
}
```

---

## 4. Zustand Stores — Estado Global

### 4.1 runtimeStore.ts
```typescript
interface ModuleInfo {
  name: string;
  state: ModuleState;
  metadata: ModuleMetadata;
  health: ModuleHealth | null;
}

interface RuntimeState {
  info: RuntimeInfo | null;
  health: HealthResponse | null;
  modules: Record<string, ModuleInfo>;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  
  setInfo: (info: RuntimeInfo) => void;
  setHealth: (health: HealthResponse) => void;
  setModule: (module: ModuleInfo) => void;
  updateModuleState: (name: string, state: ModuleState) => void;
  updateModuleHealth: (name: string, health: ModuleHealth) => void;
  setStatus: (status: RuntimeState['status']) => void;
}
```

### 4.2 chatStore.ts
```typescript
interface ChatState {
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: Record<string, Message[]>;
  streaming: Record<string, StreamingResponse>;
  isStreaming: boolean;
  
  setConversations, addConversation, setCurrentConversation,
  setMessages, addMessage, updateStreaming, clearStreaming, setStreaming
}
```

### 4.3 timelineStore.ts
```typescript
interface TimelineState {
  events: RuntimeEvent[];
  filters: EventFilters;
  correlationMap: Map<string, RuntimeEvent[]>;
  selectedCorrelationId: string | null;
  
  addEvent: (event: RuntimeEvent) => void;
  setFilters: (filters: EventFilters) => void;
  clearEvents: () => void;
  setSelectedCorrelation: (id: string | null) => void;
}
```

### 4.4 workflowStore.ts
```typescript
interface WorkflowState {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  executionState: { activeNodeId: string | null; completedNodes: string[]; ... };
  
  setNodes, setEdges, addNode, updateNode, deleteNode,
  addEdge, updateEdge, deleteEdge,
  setActiveNode, markNodeCompleted, markNodeFailed
}
```

### 4.5 uiStore.ts
```typescript
interface UIState {
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
  rightPanelTab: 'workflow' | 'timeline' | 'debug' | 'browser' | 'settings' | 'plugins';
  theme: 'light' | 'dark' | 'system';
  activeModal: string | null;
  
  toggleSidebar, setSidebarOpen, toggleRightPanel, setRightPanelTab, setTheme, openModal, closeModal
}
```

### 4.6 debugStore.ts
```typescript
interface DebugState {
  logs: DebugLogEntry[];
  snapshots: StateSnapshot[];
  runtimeRef: Runtime | null;
  modulesRef: Record<string, RuntimeModule> | null;
  
  addLog, clearLogs, takeSnapshot,
  setRuntimeRef, setModulesRef  // Para integração com Runtime Python
}
```

---

## 5. Componentes Principais — Detalhamento

### 5.1 DashboardLayout (`components/layout/DashboardLayout.tsx`)

```tsx
// Layout principal com:
// - Sidebar fixa (lg) / slide-over (mobile)
// - Header com status + avatar + ações
// - Main content area
// - Right Panel animado (Framer Motion slide from right)
// - Mobile overlay para sidebar

<div className="h-screen w-screen flex overflow-hidden">
  <Sidebar />  {/* z-40 */}
  <div className="flex-1 flex flex-col">
    <Header />
    <main className="flex-1 overflow-auto p-4 lg:p-6">{children}</main>
  </div>
  <AnimatePresence>
    {rightPanelOpen && (
      <motion.div
        initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="fixed lg:relative right-0 top-16 h-[calc(100vh-4rem)] w-full lg:w-96"
      >
        <RightPanel />
      </motion.div>
    )}
  </AnimatePresence>
</div>
```

### 5.2 Sidebar (`components/layout/Sidebar.tsx`)

```tsx
// Módulos agrupados por categoria:
// CORE: browser, execution, tools, memory, planning, mcp, filesystem, network, docker
// AGENT: agent, conversation
// ORCHESTRATION: workflow, scheduler, queue
// INFRASTRUCTURE: notification, storage, authentication, workspace
// AI: voice, vision, video, image, embedding, rag, reasoning

// Cada módulo mostra:
// - Ícone (Lucide)
// - Nome
// - Badge de status (🟢 running, 🟡 starting, 🔴 error, ⚪ stopped)
// - Tooltip com metadata (version, description)
```

### 5.3 Avatar (`components/layout/Avatar.tsx`)

```tsx
// 5 estados animados com Framer Motion:
type AvatarState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';

// idle: pulse lento
// listening: anel azul pulsante
// thinking: anel amarelo + rotação lenta
// speaking: waveform verde (5 barras animadas)
// error: anel vermelho pulsante

// Tamanhos: sm (w-12), md (w-20), lg (w-32), xl (w-48)
```

### 5.4 ChatPanel (`components/chat/ChatPanel.tsx`)

```tsx
// Funcionalidades:
// - ConversationSelector (dropdown + new conversation dialog)
// - MessageList (virtualized, auto-scroll)
// - MessageBubble (role: user/assistant/tool, type: text/image/tool_call)
// - StreamingIndicator (animated dots durante streaming)
// - MessageInput (textarea auto-resize, Enter=send, Shift+Enter=newline)
// - Integração com chatStore + api.addMessage + streaming endpoint
```

### 5.5 BrowserPanel (`components/browser/BrowserPanel.tsx`)

```tsx
// - SessionManager: create/close sessions, URL nav
// - ActionButtons: click, type, scroll, hover, select, extract, screenshot
// - ScreenshotViewer: base64 image com overlay de elementos interativos
// - Console: log de ações executadas
// - Integração com useBrowser hook + browserStore
```

### 5.6 TimelinePanel (`components/timeline/TimelinePanel.tsx`)

```tsx
// - EventFilter: multi-select por eventType, source, tags + text search
// - VirtualizedList (react-window): renderiza apenas itens visíveis (10k+ events)
// - TimelineEvent: expandível, mostra payload JSON formatado
// - CorrelationView: painel lateral ao clicar correlation_id, mostra árvore de causação
// - Real-time via useEventStream → timelineStore.addEvent
```

### 5.7 WorkflowPanel (`components/workflow/WorkflowPanel.tsx`)

```tsx
// ReactFlow integration:
// - Custom nodes: StartNode, AgentNode, ToolNode, ConditionNode, EndNode
// - Custom edges: Default (animated), Conditional (dashed + label)
// - MiniMap, Controls, Background grid
// - Execution highlighting: node ativo pulsa, completed = checkmark
// - Persistência no workflowStore
```

### 5.8 RuntimePanel (`components/runtime/RuntimePanel.tsx`)

```tsx
// - ModuleGrid: cards responsivos (1 col mobile, 2 tablet, 3 desktop)
// - ModuleCard: nome, status badge, health indicator, quick actions
// - ModuleDetail (modal): metadata completa, health details, resource usage chart
// - ResourceCharts: CPU/Memory/Network via Recharts (mock ou real se telemetry enabled)
```

### 5.9 DebugPanel (`components/debug/DebugPanel.tsx`)

```tsx
// 3 painéis lado a lado (resizable):
// 1. LogViewer: filtros por nível, source, texto; timestamp formatado
// 2. StateInspector: JSON tree view do runtime.info + module health
// 3. Snapshots: lista de snapshots com timestamp, conversation count, workflow count
//    → Click = restore view (time-travel debug)
```

### 5.10 SettingsPanel (`components/settings/SettingsPanel.tsx`)

```tsx
// 6 Tabs:
// 1. General: API URL, WS URL, auto-connect, log level
// 2. Appearance: theme (light/dark/system), density, animations on/off
// 3. Connection: reconnect settings, heartbeat interval, timeout
// 4. Notifications: browser notifications, sound, event types filter
// 5. Advanced: dev tools, debug mode, telemetry opt-in
// 6. Data: export/import workspace, clear all data, persistence path
```

### 5.11 PluginsPanel (`components/plugins/PluginsPanel.tsx`)

```tsx
// - PluginCard: nome, versão, status, descrição, tags, actions
// - Expandable: mostra metadata, config schema, dependencies
// - InstallDialog: 3 métodos
//   a) Registry: nome + versão (npm-style)
//   b) URL: GitHub/HTTP zip/tar.gz
//   c) File: upload .zip/.tar.gz
// - Actions: enable/disable, start/stop, uninstall, configure
```

---

## 6. Hooks Personalizados

### 6.1 useRuntime (`hooks/useRuntime.ts`)
```typescript
// Inicializa runtimeStore:
// - Fetch /api/runtime/info + /health
// - Fetch /api/modules → para cada: /health
// - Poll health a cada 30s
// - Subscreve WebSocket events MODULE_* → updateModuleState
```

### 6.2 useEventStream (`hooks/useEventStream.ts`)
```typescript
// Wrapper sobre websocket.ts:
// - useEventStream(handler, deps) → subscreve + conecta
// - useConnectionStatus() → boolean connected
```

### 6.3 useChat (`hooks/useChat.ts`)
```typescript
// - sendMessage(content): cria conversation se necessário, addMessage, streaming
// - createConversation(title, systemPrompt)
// - loadConversations()
// - selectConversation(id)
```

### 6.4 useBrowser (`hooks/useBrowser.ts`)
```typescript
// - createSession(url)
// - getState(sessionId)
// - executeAction(sessionId, action, params)
// - takeScreenshot(sessionId)
// - closeSession(sessionId)
// - Auto-refresh state a cada 2s para sessão ativa
```

### 6.5 useWorkflow (`hooks/useWorkflow.ts`)
```typescript
// - addNode(type, position)
// - connectNodes(source, target)
// - executeWorkflow() → envia para WorkflowModule
// - Subscreve WORKFLOW_* events → update executionState
```

---

## 7. Tipos TypeScript Compartilhados (`types/runtime.ts`)

```typescript
// Principais interfaces (300+ linhas):
ModuleState, ModuleMetadata, ModuleHealth, RuntimeInfo, HealthResponse
MessageRole, MessageType, Message, Conversation, StreamingResponse
RuntimeEvent, EventFilters
BrowserSession, BrowserState
ToolDefinition, ToolExecution, SearchResult
ExecutionResult, FileInfo
WorkflowNode, WorkflowEdge, WorkflowState
DebugLogEntry, StateSnapshot
```

---

## 8. Integração Runtime Python → Frontend

### 8.1 Mapeamento de Módulos

```python
# runtime/runtime.py → get_* methods
def get_browser(self) -> Optional[BrowserModule]: ...
def get_execution(self) -> Optional[ExecutionModule]: ...
def get_tools(self) -> Optional[ToolModule]: ...
def get_memory(self) -> Optional[MemoryModule]: ...
def get_planning(self) -> Optional[PlanningModule]: ...
def get_mcp(self) -> Optional[MCPModule]: ...
def get_filesystem(self) -> Optional[FileSystemModule]: ...
def get_network(self) -> Optional[NetworkModule]: ...
def get_docker(self) -> Optional[DockerModule]: ...
def get_agent(self) -> Optional[AgentModule]: ...
def get_conversation(self) -> Optional[ConversationModule]: ...
def get_workflow(self) -> Optional[WorkflowModule]: ...
def get_scheduler(self) -> Optional[SchedulerModule]: ...
def get_queue(self) -> Optional[QueueModule]: ...
def get_notification(self) -> Optional[NotificationModule]: ...
def get_storage(self) -> Optional[StorageModule]: ...
def get_authentication(self) -> Optional[AuthenticationModule]: ...
def get_workspace(self) -> Optional[WorkspaceModule]: ...
def get_voice(self) -> Optional[VoiceModule]: ...
def get_vision(self) -> Optional[VisionModule]: ...
def get_video(self) -> Optional[VideoModule]: ...
def get_image(self) -> Optional[ImageModule]: ...
def get_embedding(self) -> Optional[EmbeddingModule]: ...
def get_rag(self) -> Optional[RAGModule]: ...
def get_reasoning(self) -> Optional[ReasoningModule]: ...
```

### 8.2 Event Types para UI Updates

| Event Type | Store Atualizado | UI Afetada |
|------------|------------------|------------|
| `RUNTIME_STARTED/STOPPED/READY/ERROR` | runtimeStore | Header status, RuntimePanel |
| `MODULE_STARTED/STOPPED/ERROR/INITIALIZED` | runtimeStore | Sidebar badges, RuntimePanel cards |
| `TASK_STARTED/COMPLETED/FAILED` | timelineStore, debugStore | Timeline, Debug logs |
| `CONVERSATION_STARTED/ENDED, MESSAGE_RECEIVED/SENT` | chatStore, timelineStore | ChatPanel, Timeline |
| `WORKFLOW_STARTED/COMPLETED/FAILED, WORKFLOW_STEP_*` | workflowStore, timelineStore | WorkflowPanel, Timeline |
| `BROWSER_OPENED/CLOSED/NAVIGATED/ACTION` | timelineStore | BrowserPanel, Timeline |
| `AGENT_CREATED/STARTED/COMPLETED/FAILED/MESSAGE` | timelineStore, chatStore | Timeline, Chat |
| `LLM_REQUEST/RESPONSE/ERROR` | timelineStore, debugStore | Timeline, Debug |
| `*_STARTED/COMPLETED/FAILED` (outros módulos) | timelineStore | Timeline |

---

## 9. Configuração e Variáveis de Ambiente

### 9.1 Backend (`.env` ou variáveis)
```bash
RUNTIME_TYPE=local          # local, docker, cloud
LOG_LEVEL=DEBUG             # DEBUG, INFO, WARNING, ERROR
WORKSPACE_PATH=./workspace  # Diretório de trabalho
BROWSER_HEADLESS=false      # true para CI
SANDBOX_ENABLED=true        # Isolamento execução
```

### 9.2 Frontend (`.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/events
```

### 9.3 Next.js Config (`next.config.js`)
```javascript
const nextConfig = {
  reactStrictMode: true,
  experimental: { optimizePackageImports: ['lucide-react'] },
  async rewrites() {
    return [{
      source: '/api/proxy/:path*',
      destination: 'http://localhost:8000/api/:path*'  // Proxy opcional
    }];
  }
};
```

---

## 10. Testes e Qualidade

### 10.1 Backend — pytest
```python
# tests/test_api.py
async def test_runtime_info(client):
    response = await client.get("/api/runtime/info")
    assert response.status_code == 200
    data = response.json()
    assert "runtime_id" in data
    assert "modules" in data

async def test_websocket_events(client):
    async with client.websocket_connect("/ws/events") as ws:
        # Trigger event
        await client.post("/api/runtime/execute", json={"type": "test", "action": "ping", "params": {}})
        event = await ws.receive_json()
        assert event["event_type"] == "TASK_STARTED"
```

### 10.2 Frontend — Vitest + React Testing Library
```typescript
// src/components/chat/__tests__/ChatPanel.test.tsx
test('sends message and shows streaming response', async () => {
  render(<ChatPanel />, { wrapper: Providers });
  
  await userEvent.type(screen.getByPlaceholderText('Type a message...'), 'Hello');
  await userEvent.click(screen.getByText('Send'));
  
  expect(await screen.findByText('Hello')).toBeInTheDocument();
  expect(await screen.findByText(/streaming/i)).toBeInTheDocument();
});
```

### 10.3 E2E — Playwright
```typescript
// tests/e2e/dashboard.spec.ts
test('full dashboard flow', async ({ page }) => {
  await page.goto('http://localhost:3000');
  
  // WebSocket conectado
  await expect(page.locator('[data-testid="ws-status"]')).toHaveText('Live');
  
  // Nova conversa
  await page.click('[data-testid="new-conversation"]');
  await page.fill('[data-testid="conv-title"]', 'Test');
  await page.click('[data-testid="conv-create"]');
  
  // Enviar mensagem
  await page.fill('[data-testid="message-input"]', 'Hello');
  await page.press('[data-testid="message-input"]', 'Enter');
  
  // Resposta aparece
  await expect(page.locator('[data-testid="message-bubble"]').last()).toContainText('Hello');
});
```

---

## 11. Deployment

### 11.1 Dockerfile (Backend)
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN playwright install-deps chromium && playwright install chromium

EXPOSE 8000
CMD ["uvicorn", "runtime.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 11.2 Dockerfile (Frontend)
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

### 11.3 docker-compose.yml
```yaml
version: '3.8'
services:
  backend:
    build: .
    ports: ["8000:8000"]
    volumes: ["./workspace:/app/workspace"]
    environment:
      - RUNTIME_TYPE=local
      - LOG_LEVEL=INFO
    depends_on: [redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on: [backend]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

---

## 12. Troubleshooting Guide

| Sintoma | Causa Provável | Solução |
|---------|----------------|---------|
| WS não conecta | Backend não iniciou | Verificar logs uvicorn, porta 8000 |
| Módulos "error" | Dependências faltando | `pip install -r requirements.txt`, `playwright install` |
| Chat não responde | ConversationModule não carregado | Verificar `/api/modules/conversation/health` |
| Browser falha | Chromium não instalado | `playwright install chromium` |
| Timeline vazia | WS handler não registrado | Verificar `event_bus.subscribe_all` no lifespan |
| TypeScript errors | Types desatualizados | `npm run type-check`, regenerar se schema mudou |
| Build falha | Dependências desatualizadas | `rm -rf node_modules package-lock.json && npm install` |

---

## 13. Extensibilidade — Adicionando Novo Módulo

### 13.1 Backend
1. Criar módulo em `runtime/<novo_modulo>/`
2. Implementar `RuntimeModule` interface
3. Registrar no `Runtime._register_core_modules()` ou via plugin
4. Adicionar endpoints em `runtime/api/server.py` (seguir padrão existente)
5. Adicionar modelos Pydantic em `runtime/api/models.py`

### 13.2 Frontend
1. Adicionar em `MODULE_NAMES` e `MODULE_CATEGORIES` (`lib/constants.ts`)
2. Adicionar ícone em `MODULE_ICONS`
3. Criar tipos em `types/runtime.ts` se necessário
4. Adicionar métodos no `api.ts`
5. Sidebar mostra automaticamente (usa `runtimeStore.modules`)

---

## 14. Referências Rápidas

| Arquivo | Descrição |
|---------|-----------|
| `runtime/api/server.py` | FastAPI app, endpoints, lifespan, WS handler |
| `runtime/api/models.py` | Pydantic models (request/response) |
| `runtime/runtime.py` | Runtime class, módulos, execução de tasks |
| `runtime/base/events.py` | EventBus, RuntimeEvent, RuntimeEventType |
| `frontend/src/lib/api.ts` | ApiClient — todos endpoints REST |
| `frontend/src/lib/websocket.ts` | WebSocketClient + hooks |
| `frontend/src/stores/*.ts` | 6 Zustand stores |
| `frontend/src/components/layout/DashboardLayout.tsx` | Layout principal |
| `frontend/src/types/runtime.ts` | TypeScript types completos |
| `frontend/src/lib/constants.ts` | MODULE_NAMES, ICONS, CATEGORIES, EVENT_CATEGORIES |

---

## 15. Checklist de Code Review

- [ ] TypeScript strict: sem `any`, tipos explícitos
- [ ] React: sem hooks rules violations, keys em listas
- [ ] Zustand: imutabilidade correta (`set(state => ({...}))`)
- [ ] API: error handling consistente, status codes corretos
- [ ] WebSocket: reconnection testado, cleanup no unmount
- [ ] Performance: `React.memo`, `useMemo`, `useCallback` onde apropriado
- [ ] Acessibilidade: labels, roles, keyboard nav, contrast
- [ ] Testes: unit + integration para novas features
- [ ] Documentação: README atualizado, comentários em lógica complexa

---

**Documento vivo** — Atualizar a cada mudança arquitetural significativa.  
**Próxima revisão**: Sprint planning ou quando adicionar novo módulo core.