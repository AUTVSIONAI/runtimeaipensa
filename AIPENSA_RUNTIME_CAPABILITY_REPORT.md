# AIPENSA Runtime - Relatório de Capacidades (20 Exemplos)

**Data:** 2025-07-22  
**Versão:** 1.0  
**Destino:** Integração com aipensa.com (backend service)  
**Finalidade:** Documentar todas as capacidades do Runtime para tomada de decisão de arquitetura

---

## Sumário Executivo

O AIPENSA Runtime é um **motor de execução modular, orientado a eventos e multi-agente** com 25 módulos especializados. Ele roda como um serviço backend independente (FastAPI na porta 8006) e expõe APIs REST + WebSocket para integração. A interface Next.js (porta 3000) é apenas um painel de desenvolvimento/validação - **não é o produto final**.

---

## 20 Exemplos de Capacidades

### 1. **Execução de Código Python em Sandbox Isolado**
```python
# Backend API
POST /api/execution/python
{
  "code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.describe())",
  "timeout_seconds": 30,
  "packages": ["pandas"],
  "env_vars": {"API_KEY": "xxx"}
}
```
**Uso:** Análise de dados, ETL, computação científica, execução de código usuário.

---

### 2. **Automação de Navegador (Playwright)**
```python
# Criar sessão
POST /api/browser/session {"url": "https://example.com"}

# Executar ações
POST /api/browser/session/{id}/action
{"action": "click", "params": {"selector": "#login-button"}}

# Screenshot
POST /api/browser/session/{id}/screenshot {"full_page": true}
```
**Uso:** Web scraping, testes E2E, automação de formulários, captura de evidências.

---

### 3. **Chat/Conversação com Streaming LLM (NVIDIA NIM - 95+ Modelos Gratuitos)**
```python
# Criar conversa
POST /api/conversation/create {"title": "Suporte", "system_prompt": "Você é um assistente..."}

# Streaming de resposta
POST /api/conversation/{id}/stream
{"role": "user", "content": "Como faço X?", "message_type": "text"}
# Retorna Server-Sent Events com chunks em tempo real
```
**Modelos disponíveis:** Llama 3.1 (8B/70B/405B), Nemotron 3 Ultra, Mistral Large 2, Gemma 2, Phi-3, Qwen 2.5, CodeLlama, etc.

---

### 4. **Orquestração de Workflows Visuais (ReactFlow)**
- Nós: Start, Agent, Tool, Condition, End
- Execução passo-a-passo com tracking de estado
- Persistência (save/load/export JSON)
- Minimapa, zoom, grid snap

---

### 5. **Agendamento de Tarefas (Cron-like)**
```python
POST /api/modules/scheduler/execute
{"operation": "schedule", "params": {
  "cron": "0 2 * * *",  # 2AM daily
  "task": {"type": "workflow", "action": "execute", "params": {"workflow_id": "etl_daily"}}
}}
```
**Uso:** Jobs recorrentes, backups, relatórios, limpeza.

---

### 6. **Fila de Mensagens/Jobs (Queue Module)**
```python
POST /api/modules/queue/execute
{"operation": "enqueue", "params": {
  "queue": "email_notifications",
  "payload": {"to": "user@email.com", "template": "welcome"},
  "priority": 10,
  "delay_seconds": 0
}}
```
**Uso:** Processamento assíncrono, retry automático, dead-letter queue.

---

### 7. **Memória Vetorial / Semântica (RAG Ready)**
```python
# Armazenar
POST /api/memory/search {"query": "política de reembolso", "memory_type": "knowledge", "limit": 5}

# Buscar contexto para LLM
GET /api/memory/search?query=como+cancelar+assinatura&limit=10
```
**Uso:** RAG, conhecimento persistente, embeddings para busca semântica.

---

### 8. **Sistema de Arquivos Virtualizado**
```python
# Ler
GET /api/filesystem/read?path=workspace/data/report.pdf

# Escrever
POST /api/filesystem/write
{"path": "workspace/output/result.json", "content": "{...}", "create_dirs": true}

# Listar
GET /api/filesystem/list?path=workspace/&recursive=true
```
**Uso:** Workspace isolado por tenant, artefatos de workflow, upload/download.

---

### 9. **Rede/HTTP Client (Network Module)**
```python
POST /api/modules/local-network/execute
{"operation": "http_request", "params": {
  "method": "POST",
  "url": "https://api.external.com/webhook",
  "headers": {"Authorization": "Bearer xxx"},
  "body": {"event": "user_signup"}
}}
```
**Uso:** Integrações externas, webhooks, chamadas a APIs terceiras.

---

### 10. **MCP (Model Context Protocol) - Integração com Servidores Externos**
```python
POST /api/modules/local-mcp/execute
{"operation": "call_tool", "params": {
  "server": "github",
  "tool": "create_issue",
  "arguments": {"repo": "org/repo", "title": "Bug: login falha"}
}}
```
**Uso:** Conectar LLMs a ferramentas externas (GitHub, Slack, Jira, DBs, etc.)

---

### 11. **Visão Computacional (Vision Module)**
```python
POST /api/modules/vision/execute
{"operation": "analyze_image", "params": {
  "image_base64": "...",
  "tasks": ["object_detection", "ocr", "captioning"]
}}
```
**Uso:** Análise de documentos, OCR, moderação de conteúdo, extração de dados visuais.

---

### 12. **Processamento de Áudio/Voz (Voice Module)**
```python
POST /api/modules/voice/execute
{"operation": "transcribe", "params": {"audio_base64": "...", "language": "pt"}}
{"operation": "synthesize", "params": {"text": "Olá!", "voice": "pt-BR-female"}}
```
**Uso:** Speech-to-text, text-to-speech, IVR, acessibilidade.

---

### 13. **Geração/Edição de Imagens (Image Module)**
```python
POST /api/modules/image/execute
{"operation": "generate", "params": {
  "prompt": "Dashboard executivo moderno, tons azuis, minimalista",
  "model": "stabilityai/sdxl",
  "width": 1024, "height": 768
}}
```
**Uso:** Assets de marketing, prototipagem, geração de thumbnails.

---

### 14. **Embeddings Multimodais (Embedding Module)**
```python
POST /api/modules/embedding/execute
{"operation": "embed", "params": {
  "inputs": ["texto para buscar", "outro documento"],
  "model": "nvidia/nv-embed-v2",
  "input_type": "passage"
}}
```
**Uso:** Busca semântica, clustering, recomendações, RAG.

---

### 15. **RAG Completo (Retrieval-Augmented Generation)**
```python
POST /api/modules/rag/execute
{"operation": "query", "params": {
  "question": "Qual a política de férias?",
  "collection": "hr_docs",
  "top_k": 5,
  "llm_model": "meta/llama-3.1-70b-instruct"
}}
```
**Uso:** Chat com base de conhecimento, suporte técnico, FAQ automatizado.

---

### 16. **Raciocínio Avançado / Chain-of-Thought (Reasoning Module)**
```python
POST /api/modules/reasoning/execute
{"operation": "reason", "params": {
  "problem": "Otimizar rota de entrega para 50 pontos",
  "approach": "tree_of_thought",
  "max_steps": 10,
  "model": "nvidia/nemotron-3-ultra"
}}
```
**Uso:** Resolução de problemas complexos, planejamento, decomposição de tarefas.

---

### 17. **Sistema de Notificações Multi-canal**
```python
POST /api/modules/notification/execute
{"operation": "send", "params": {
  "channels": ["email", "slack", "webhook"],
  "template": "workflow_completed",
  "data": {"workflow": "etl_daily", "status": "success", "duration": "12min"},
  "recipients": ["team@empresa.com", "#alerts"]
}}
```
**Uso:** Alertas operacionais, notificações de usuários, webhooks de integração.

---

### 18. **Autenticação e Multi-tenancy (Auth + Workspace)**
```python
# Criar workspace (tenant)
POST /api/modules/workspace/execute
{"operation": "create", "params": {"name": "Cliente ACME", "owner": "admin@aipensa.com"}}

# Gerar token
POST /api/modules/authentication/execute
{"operation": "create_token", "params": {"workspace_id": "ws_123", "scopes": ["read", "write", "execute"]}}
```
**Uso:** SaaS multi-tenant, isolamento de dados, RBAC, API keys.

---

### 19. **Armazenamento Persistente Abstraído (Storage Module)**
```python
POST /api/modules/storage/execute
{"operation": "put", "params": {
  "bucket": "artifacts",
  "key": "workflow_123/output.csv",
  "content_base64": "...",
  "metadata": {"workflow_id": "123", "content_type": "text/csv"}
}}
```
**Uso:** Artefatos de workflow, backups, compartilhamento de arquivos entre módulos.

---

### 20. **Event Bus Tempo Real + Correlação (150+ Tipos de Evento)**
```javascript
// WebSocket: ws://localhost:8006/ws/events
// Recebe eventos com correlation_id e causation_id para tracing distribuído

{
  "event_type": "TASK_COMPLETED",
  "source": "workflow",
  "correlation_id": "corr-abc-123",  // rastreia toda a cadeia
  "causation_id": "evt-xyz-789",     // evento que causou este
  "timestamp": "2025-07-22T10:30:00Z",
  "payload": {"task_id": "task-456", "output": {...}},
  "tags": ["workflow", "etl", "success"]
}
```
**Uso:** Observabilidade completa, debugging distribuído, auditoria, dashboards tempo real.

---

## Arquitetura de Integração para aipensa.com

```
┌─────────────────────────────────────────────────────────────────┐
│                      aipensa.com (Backend)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ API Gateway  │  │ Auth Service │  │ Tenant Mgmt  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼─────────────────┼──────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AIPENSA RUNTIME (Porta 8006)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Runtime EventBus                        │   │
│  │  (Correlation/Causation Tracking - 150+ Event Types)      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Core    │ │ Agent   │ │Orchestr.│ │ Infra   │ │ AI      │   │
│  │(9 mods) │ │(2 mods) │ │(3 mods) │ │(4 mods) │ │(7 mods) │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
└───────┼───────────┼───────────┼───────────┼───────────┼────────┘
        │           │           │           │           │
   ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐
   │ Browser │ │Execution│ │ Workflow│ │ Storage │ │  LLM    │
   │ Tools   │ │ Memory  │ │Scheduler│ │  Auth   │ │ Vision  │
   │Network  │ │Planning │ │ Queue   │ │Notific. │ │ Voice   │
   │ Filesys │ │MCP      │ │         │ │Workspace│ │ Embedding│
   │ Docker  │ │Conversation    │         │         │ RAG      │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

## Pontos de Integração Recomendados

| Camada | Endpoint | Protocolo | Autenticação |
|--------|----------|-----------|--------------|
| **Comandos** | `POST /api/runtime/execute` | REST | Bearer Token |
| **Módulos** | `POST /api/modules/{name}/execute` | REST | Bearer Token |
| **Chat/Streaming** | `POST /api/conversation/{id}/stream` | SSE | Bearer Token |
| **Eventos Tempo Real** | `ws://localhost:8006/ws/events` | WebSocket | Token na query |
| **Health Check** | `GET /api/runtime/health` | REST | Público |

---

## Decisões Arquiteturais para aipensa.com

| Decisão | Recomendação | Justificativa |
|---------|--------------|---------------|
| **Deploy** | Container separado (Docker/K8s) | Isolação de recursos, escala independente |
| **Comunicação** | gRPC interno + REST externo | Performance + compatibilidade |
| **Auth** | JWT validado pelo Runtime | Zero-trust, multi-tenant nativo |
| **Eventos** | Consumir via WebSocket ou Kafka bridge | Real-time + durability |
| **Modelos LLM** | Usar NVIDIA NIM (95+ grátis) + fallback próprio | Custo zero, baixa latência, 70+ modelos |
| **Persistência** | PostgreSQL + Redis (já no Runtime) | Reutilizar infra existente |
| **Monitoramento** | Prometheus + Grafana (events exportados) | Observabilidade nativa |

---

## Próximos Passos Sugeridos

1. **POC de Integração** - Conectar um endpoint da aipensa.com ao Runtime (ex: `/api/runtime/execute`)
2. **Multi-tenancy** - Configurar workspaces isolados por cliente aipensa.com
3. **Model Registry** - Centralizar gestão de modelos (NIM + customizados)
4. **Rate Limiting/Quotas** - Implementar no API Gateway da aipensa.com
5. **Audit Log** - Consumir EventBus para trilha de auditoria completa

---

## Contato / Suporte Técnico

- **Runtime Repo:** `/runtime` (Python/FastAPI)
- **Frontend Dev:** `/frontend` (Next.js 14) - *apenas para validação*
- **Config:** `runtime.toml` (todos os módulos e parâmetros)
- **API Docs:** `http://localhost:8006/docs` (Swagger)
- **WebSocket Test:** `ws://localhost:8006/ws/events`

---

*Este documento serve como base para decisões de arquitetura de integração. O Runtime é production-ready para uso como backend service da aipensa.com.*