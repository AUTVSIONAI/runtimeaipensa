# AIPENSA Runtime Engine - Documentação Técnica Completa

## Visão Geral do Projeto

O **AIPENSA Runtime Engine** é um **motor de execução de agentes de IA de nível enterprise** que fornece infraestrutura completa para construir, orquestrar e escalar sistemas multi-agente autônomos. Não é apenas uma biblioteca — é um **kernel de IA** modular, observável e extensível, pronto para produção.

### Status Atual (Julho 2026)
- ✅ **27 Módulos Runtime** (13 Core + 14 Extensões IA)
- ✅ **FastAPI Backend** (Porta 8000) com WebSocket tempo real + REST API
- ✅ **Next.js 14 Frontend** (Porta 3000) com Dashboard Dev completo
- ✅ **Event-Driven Architecture** com 150+ tipos de eventos via RuntimeEventBus
- ✅ **Plugin System** com auto-descoberta, hot-reload, validação YAML
- ✅ **Streaming Agent Loop** compatível OpenAI + NVIDIA NIM
- ✅ **GitHub**: https://github.com/AUTVSIONAI/runtimeaipensa.git

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AIPENSA RUNTIME ENGINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │   FRONTEND       │  │   BACKEND        │  │   CORE KERNEL            │  │
│  │   (Next.js 14)   │◄─│  (FastAPI)       │◄─│  (Python Runtime)        │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│         │                       │                        │                  │
│         ▼                       ▼                        ▼                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    RUNTIME EVENT BUS (WebSocket + REST)              │  │
│  │  • 150+ Event Types  • Correlation/Causation Tracking  • Replay     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│         ┌──────────────────────────┼──────────────────────────┐           │
│         ▼                          ▼                          ▼           │
│  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐   │
│  │ CORE MODULES│            │AI MODULES   │            │EXTENSIONS   │   │
│  │ (13)        │            │ (6)         │            │ (7+)        │   │
│  └─────────────┘            └─────────────┘            └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. MÓDULOS CORE (13) - Infraestrutura Base

| Módulo | Responsabilidade | Capacidades Principais |
|--------|------------------|------------------------|
| **browser** | Automação web headless | Sessões persistentes, screenshots, DOM inspection, actions (click, type, navigate), Stealth mode |
| **execution** | Execução de código sandboxed | Python sandbox, Docker containers, timeout, resource limits, package installation |
| **tools** | Registry & execução de ferramentas | 50+ tools built-in, schema validation, approval flow, async execution |
| **memory** | Memória vetorial e episódica | Embeddings, RAG, similarity search, memory types (semantic, episodic, procedural) |
| **planning** | Planejamento hierárquico | Task decomposition, DAG execution, replanning, goal-oriented planning |
| **mcp** | Model Context Protocol | MCP server/client, resource discovery, tool exposure via MCP |
| **filesystem** | Operações de arquivo seguras | Read/write/list, sandboxed paths, encoding, diff, watch |
| **network** | Requisições HTTP/WebSocket | Rate limiting, retry, auth, proxy, circuit breaker |
| **docker** | Container orchestration | Create/start/stop, exec, logs, volumes, networks |
| **agent** | Agentes autônomos | Personas, skills, delegation, multi-agent coordination |
| **conversation** | Chat & message management | Threads, streaming, tool calls, history, context window mgmt |
| **workflow** | Orquestração visual | DAG editor, ReactFlow UI, parallel/sequential, conditional branches |
| **scheduler** | Agendamento de tarefas | Cron, one-shot, recurring, timezone, distributed locking |

### Módulos de Infraestrutura (4)
| Módulo | Responsabilidade |
|--------|------------------|
| **queue** | Filas de mensagens (Redis/RabbitMQ), dead letter, priority |
| **notification** | Multi-channel (email, Slack, Discord, WhatsApp, Push) |
| **storage** | Object storage (S3, MinIO, local), versioning, CDN |
| **authentication** | JWT, OAuth2, API Keys, RBAC, session management |
| **workspace** | Isolamento de projetos, multi-tenancy, resource quotas |

---

## 2. MÓDULOS IA (6) - Capacidades Cognitivas

| Módulo | Modelo/Provider | Capacidades |
|--------|-----------------|-------------|
| **voice** | Whisper, TTS (ElevenLabs, Coqui) | STT, TTS, voice cloning, real-time streaming |
| **vision** | GPT-4V, Llava, Pixtral | Image analysis, OCR, document understanding, visual QA |
| **video** | Video-LLaMA, custom | Video summarization, frame extraction, temporal reasoning |
| **embedding** | text-embedding-3, BGE, Nomic | Vector generation, semantic search, clustering |
| **rag** | Hybrid (vector + keyword + graph) | Retrieval, reranking, citation, knowledge graphs |
| **reasoning** | CoT, ToT, ReAct, self-reflection | Multi-step reasoning, planning, verification |

---

## 3. EXTENSÕES ENTERPRISE (7+) - Domínio de Negócio

| Extensão | Foco | Use Cases |
|----------|------|-----------|
| **employee** | IA Employees | Digital workers com roles, KPIs, onboarding |
| **team** | Multi-agent teams | Squads autônomas, coordination, handoff |
| **company** | Company simulation | Org charts, processes, governance |
| **provider** | LLM Provider abstraction | Multi-provider, fallback, cost optimization |
| **explorer** | Web research agent | Deep research, fact-checking, synthesis |
| **onboarding** | Employee onboarding | Training, evaluation, certification |
| **sync** | Data synchronization | Multi-source, conflict resolution, CDC |

---

## 4. CAPACIDADES PARA AIPENSA.COM (SaaS CRM + IA)

### 🎯 **Atendimento WhatsApp Automatizado**

```python
# Exemplo: Agente de WhatsApp com memória e ferramentas
from runtime import create_runtime
from runtime.agent.module import AgentModule

runtime = await create_runtime()
agent = runtime.get_module("agent")

whatsapp_agent = await agent.create_agent(
    name="whatsapp-support",
    persona="Especialista em suporte SaaS, empático, resolve em 1ª interação",
    skills=["crm_lookup", "ticket_creation", "knowledge_base", "escalation"],
    tools=["send_whatsapp", "query_crm", "create_ticket", "search_docs"],
    memory="conversation_history",
    channels=["whatsapp", "instagram_dm", "facebook_messenger"]
)

# Event-driven: mensagem chega → evento → agente processa → responde
@runtime.event_bus.subscribe("MESSAGE_RECEIVED")
async def handle_whatsapp(event):
    if event.payload.channel == "whatsapp":
        response = await whatsapp_agent.process(event.payload.message)
        await runtime.get_module("notification").send_whatsapp(
            to=event.payload.from_number,
            message=response
        )
```

**Features prontas:**
- ✅ Webhook Meta/WhatsApp Business API
- ✅ Session management 24h (contexto de conversa)
- ✅ Handoff humano ↔ IA com aprovação
- ✅ Templates aprovados + mensagens livres
- ✅ Métricas: CSAT, tempo resposta, resolução 1ª contato

### 🤖 **Funcionários de IA (AI Employees)**

```python
# Contratar um "SDR de IA" que qualifica leads 24/7
sdr = await runtime.get_module("employee").hire(
    role="SDR",
    name="Ana IA",
    config={
        "working_hours": "24/7",
        "kpis": ["leads_qualified", "meetings_booked", "response_time"],
        "tools": ["linkedin_scraper", "email_finder", "crm_update", "calendar"],
        "memory": "lead_history",
        "reporting": "daily_to_slack"
    }
)

# O SDR roda autonomamente:
# 1. Busca leads no CRM (status=new)
# 2. Enriquece com LinkedIn/email
# 3. Envia sequence personalizada
# 4. Qualifica via chat/voice
# 5. Agenda reunião no Calendly
# 6. Atualiza CRM + notifica closer humano
```

**Roles disponíveis out-of-the-box:**
- **SDR** - Prospecting, qualification, booking
- **Closer** - Demo, negotiation, closing
- **CSM** - Onboarding, health checks, expansion
- **Support L1/L2** - Ticket triage, resolution, escalation
- **Content Creator** - Blog, social, email sequences
- **Data Analyst** - SQL, dashboards, insights

### 🏪 **Marketplace de Agentes/Plugins**

```python
# Publicar agente no marketplace interno
await runtime.get_module("plugins").publish(
    plugin_id="crm-lead-scorer",
    version="1.2.0",
    manifest={
        "name": "Lead Scorer Pro",
        "category": "sales",
        "pricing": "per_execution",
        "requirements": ["crm_access", "ml_model"],
        "sla": "99.9% uptime, <500ms p99"
    }
)

# Instalar em outro tenant/workspace
await runtime.get_module("plugins").install(
    workspace_id="client-acme-corp",
    plugin_id="crm-lead-scorer",
    config={"model": "gpt-4o", "threshold": 0.85}
)
```

### 🔗 **Integrações Nativas (Social + CRM)**

| Plataforma | Módulo | Capacidades |
|------------|--------|-------------|
| **WhatsApp** | notification + browser | Business API, webhooks, templates, media |
| **Instagram DM** | browser + notification | Graph API, comments, stories mentions |
| **LinkedIn** | browser + employee | Sales Nav, messaging, profile enrichment |
| **Email (SMTP/IMAP)** | notification | Sequences, tracking, replies parsing |
| **Slack/Teams** | notification | Bots, slash commands, modals |
| **HubSpot/Salesforce/Pipedrive** | tools + network | CRM sync bi-direcional, webhooks |
| **Zapier/Make** | network + webhook | 5000+ apps via webhook |

---

## 5. DEPLOY EM PRODUÇÃO

### Arquitetura Recomendada para aipensa.com

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION DEPLOYMENT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   Load       │────►│  Frontend    │────►│   CDN        │                │
│  │   Balancer   │     │  (Vercel/    │     │  (CloudFlare)│                │
│  │   (ALB)      │     │   Netlify)   │     │              │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│         │                                           │                        │
│         ▼                                           ▼                        │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │                     API GATEWAY (Kong/Traefik)                   │       │
│  │  • Rate limiting  • Auth (JWT/OAuth)  • Routing  • Observability │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                    │                                       │
│         ┌──────────────────────────┼──────────────────────────┐           │
│         ▼                          ▼                          ▼           │
│  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐   │
│  │ Runtime     │            │ Runtime     │            │ Runtime     │   │
│  │ Pod 1       │            │ Pod 2       │            │ Pod N       │   │
│  │ (FastAPI)   │            │ (FastAPI)   │            │ (FastAPI)   │   │
│  └──────┬──────┘            └──────┬──────┘            └──────┬──────┘   │
│         │                          │                          │           │
│         └──────────────────────────┼──────────────────────────┘           │
│                                    ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │                    SHARED STATE (Redis Cluster)                   │       │
│  │  • Session store  • Event bus pub/sub  • Distributed locks      │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                    │                                       │
│         ┌──────────────────────────┼──────────────────────────┐           │
│         ▼                          ▼                          ▼           │
│  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐   │
│  │ PostgreSQL  │            │ Vector DB   │            │ Object      │   │
│  │ (Primary)   │            │ (Qdrant/    │            │ Storage     │   │
│  │             │            │  Pinecone)  │            │ (S3/MinIO)  │   │
│  └─────────────┘            └─────────────┘            └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Docker Compose (Dev/Staging)

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  runtime-api:
    build: ./runtime
    image: aipensa/runtime:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
    environment:
      - NIM_API_KEY=${NIM_API_KEY}
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis-cluster:6379
      - QDRANT_URL=http://qdrant:6333
      - S3_ENDPOINT=http://minio:9000
    ports:
      - "8000:8000"
    depends_on: [postgres, redis, qdrant, minio]

  frontend:
    build: ./frontend
    image: aipensa/frontend:latest
    deploy:
      replicas: 2
    environment:
      - NEXT_PUBLIC_API_URL=https://api.aipensa.com
      - NEXT_PUBLIC_WS_URL=wss://api.aipensa.com/ws/events
    ports:
      - "3000:3000"

  postgres:
    image: pgvector/pgvector:pg16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=aipensa
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:7-cluster
    command: redis-server --cluster-enabled yes
    volumes:
      - redis_data:/data

  qdrant:
    image: qdrant/qdrant:v1.8
    volumes:
      - qdrant_data:/qdrant/storage

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=${MINIO_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  minio_data:
```

### Kubernetes (Produção)

```yaml
# k8s/runtime-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aipensa-runtime
  namespace: aipensa-prod
spec:
  replicas: 6
  selector:
    matchLabels:
      app: aipensa-runtime
  template:
    metadata:
      labels:
        app: aipensa-runtime
    spec:
      containers:
      - name: runtime
        image: aipensa/runtime:v1.2.0
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: aipensa-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /api/runtime/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/runtime/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: aipensa-runtime-svc
  namespace: aipensa-prod
spec:
  selector:
    app: aipensa-runtime
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

---

## 6. OBSERVABILIDADE & DEBUG

### Dashboard Dev (Já Incluso)

Acesse `http://localhost:3000/dashboard`:

| Aba | Funcionalidade |
|-----|----------------|
| **Chat** | Testar agentes, ver streaming, tool calls em tempo real |
| **Timeline** | 150+ eventos, correlação/causação, replay, filtros |
| **Workflow** | Visual DAG editor (ReactFlow), execução step-by-step |
| **Debug** | Logs estruturados, state inspector, performance metrics |
| **Runtime** | Module health grid, resource usage, quick actions |
| **Browser** | Live screenshot, DOM inspector, action recorder |
| **Settings** | Configuração runtime, plugins, API keys |

### Métricas Chave (Prometheus/Grafana)

```prometheus
# Métricas custom do runtime
aipensa_runtime_uptime_seconds
aipensa_module_health{module="browser",status="healthy"}
aipensa_agent_iterations_total{agent="sdr",result="success"}
aipensa_tool_execution_duration_seconds{tool="crm_query"}
aipensa_llm_tokens_total{provider="nvidia",model="llama-3.1-70b"}
aipensa_event_bus_throughput_events_per_second
aipensa_workflow_execution_duration_seconds{workflow="lead_qualification"}
```

### Distributed Tracing (OpenTelemetry)

```python
# Auto-instrumentação
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter

tracer = trace.get_tracer("aipensa.runtime")

@runtime.event_bus.subscribe("*")
async def trace_events(event):
    with tracer.start_as_current_span(
        f"event.{event.event_type}",
        context=set_span_in_context(event.trace_context)
    ) as span:
        span.set_attribute("correlation_id", event.correlation_id)
        span.set_attribute("causation_id", event.causation_id)
        span.add_event("event_received", event.to_dict())
```

---

## 7. SEGURANÇA & COMPLIANCE

### Multi-Tenancy (Workspace Isolation)

```python
# Cada cliente = workspace isolado
workspace = await runtime.get_module("workspace").create(
    name="acme-corp",
    quotas={
        "agents": 50,
        "executions_per_hour": 10000,
        "storage_gb": 10,
        "llm_tokens_per_day": 1000000
    },
    network_policies={
        "egress": ["api.hubspot.com", "graph.facebook.com"],
        "deny_all_other": True
    },
    data_residency="br-south-1"  # LGPD compliance
)

# Agentes só veem dados do seu workspace
agent = await workspace.create_agent(...)
# agent.tools.crm_query() → automaticamente filtra por workspace_id
```

### Auditoria Completa

```python
# Todos os eventos são imutáveis e auditáveis
audit_log = await runtime.get_module("storage").query(
    collection="audit_events",
    filters={
        "workspace_id": "acme-corp",
        "event_type": "TOOL_EXECUTED",
        "timestamp": {"gte": "2026-01-01", "lte": "2026-01-31"}
    }
)
# Retorna: quem executou, qual tool, parâmetros, resultado, duração
```

---

## 8. ROADMAP DE INTEGRAÇÃO PARA AIPENSA.COM

### Fase 1 - Fundação (Semanas 1-2)
- [ ] Deploy runtime em staging (k8s)
- [ ] Configurar workspaces por cliente
- [ ] Integrar auth (SSO + API Keys)
- [ ] Setup observabilidade (Grafana + Jaeger)

### Fase 2 - WhatsApp & Social (Semanas 3-4)
- [ ] Webhook Meta Business API
- [ ] Agente de suporte L1 com handoff
- [ ] Templates aprovados + resposta livre
- [ ] Métricas: CSAT, SLA, resolução

### Fase 3 - AI Employees (Semanas 5-8)
- [ ] SDR IA (qualificação + agendamento)
- [ ] CSM IA (health checks + expansão)
- [ ] Dashboard de KPIs por "funcionário"
- [ ] A/B test: IA vs humano

### Fase 4 - Marketplace & Ecosystem (Semanas 9-12)
- [ ] Plugin store interno
- [ ] Revenue sharing com parceiros
- [ ] SDK para devs terceiros
- [ ] Certificação de plugins

### Fase 5 - Escala Enterprise (Mês 4+)
- [ ] Multi-region (BR + US + EU)
- [ ] SOC2 Type II compliance
- [ ] SLA 99.9% com créditos
- [ ] Professional services team

---

## 9. POR QUE ISSO DÁ "SUPERPODERES" AO AIPENSA.COM?

| Antes (CRM Tradicional) | Com AIPENSA Runtime |
|-------------------------|---------------------|
| Automações = regras if/then rígidas | Agentes com **raciocínio**, planejamento, uso de ferramentas |
| WhatsApp = respostas automáticas simples | **Conversas contextuais** com memória, ferramentas, escalation |
| Leads = qualificação manual | **SDR IA 24/7** que pesquisa, qualifica, agenda |
| Relatórios = dashboards estáticos | **Analyst IA** que escreve SQL, gera insights, alerta |
| Integrações = Zapier frágil | **Tools nativas** com retry, rate limit, observabilidade |
| Escalabilidade = contratar gente | **Contratar agentes** (deploy em segundos, custo marginal ~0) |
| Debug = logs espalhados | **Timeline unificada** com correlação/causação completa |
| Inovação = meses de dev | **Plugins** instaláveis em minutos, hot-reload |

---

## 10. QUICK START PARA O CTO

```bash
# 1. Clone
git clone https://github.com/AUTVSIONAI/runtimeaipensa.git
cd runtimeaipensa

# 2. Configure secrets
cp .env.example .env
# Edite: NIM_API_KEY=sua_chave_nvidia

# 3. Suba tudo (dev)
docker-compose -f docker-compose.prod.yml up -d

# 4. Acesse
# Frontend: http://localhost:3000
# API:      http://localhost:8000/docs
# WS:       ws://localhost:8000/ws/events

# 5. Teste primeiro agente
curl -X POST http://localhost:8000/api/agent/create \
  -H "Content-Type: application/json" \
  -d '{"name":"test-agent","persona":"você é um assistente útil"}'

# 6. Veja eventos em tempo real
# Abra http://localhost:3000/dashboard/timeline
```

---

## 11. RECURSOS & LINKS ÚTEIS

| Recurso | Link |
|---------|------|
| **GitHub Repo** | https://github.com/AUTVSIONAI/runtimeaipensa.git |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **Dashboard Dev** | http://localhost:3000/dashboard |
| **Event Catalog** | `ENGINE_EVENTS.md` |
| **Plugin Guide** | `ENGINE_PLUGIN_GUIDE.md` |
| **API Contracts** | `ENGINE_API_CONTRACT.md` |
| **Architecture** | `ENGINE_ARCHITECTURE.md` |
| **Roadmap** | `ENGINE_ROADMAP.md` |

---

## Conclusão

O **AIPENSA Runtime Engine** transforma o aipensa.com de um "SaaS CRM com algumas automações" para uma **plataforma nativa de IA** onde:

1. **Cada funcionalidade** pode ser um agente autônomo
2. **Cada integração** é uma tool tipada, versionada, observável
3. **Cada workflow** é visual, debugável, replayável
4. **Cada cliente** tem workspace isolado com quotas e compliance
5. **A inovação** acontece via plugins, não refatoração de core

> **"Não estamos adicionando IA ao CRM. Estamos construindo o CRM COMO IA."**

---

*Documento gerado em: Julho 2026*
*Versão: 1.0.0*
*Runtime: AIPENSA Engine v1.2.0*