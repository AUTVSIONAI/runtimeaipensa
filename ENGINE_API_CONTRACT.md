# 📋 ENGINE_API_CONTRACT.md - Contratos Públicos da AIPENSA Engine

**Versão:** 1.0  
**Base:** ENGINE_SPEC.md + ENGINE_ARCHITECTURE.md  
**Data:** 28 Julho 2026  
**Status:** Constituição da API - Imutável sem RFC aprovado  

---

## 🏛️ PRINCÍPIOS DO CONTRATO

| Princípio | Regra |
|-----------|-------|
| **Engine Independente** | Engine NUNCA importa `aipensa_core`. Core SEMPRE importa Engine. |
| **Versioned API** | `/api/v1/` no URL. v2 = novo endpoint, não quebra v1. |
| **Additive Only** | Novos campos = opcionais. Nunca remover/renomear campos existentes. |
| **Event Sourcing** | Toda mutação de estado emite Evento no EventBus. |
| **Multi-Tenant** | Todo endpoint exige `company_id` ou `workspace_id` (header ou path). |
| **Idempotency** | `POST` com `Idempotency-Key` header para operações não-idempotentes. |
| **OpenAPI 3.1** | Spec auto-gerada em `/openapi.json` + `/openapi.yaml`. |

---

## 🌐 BASE URLS

| Ambiente | REST API | WebSocket | GraphQL (Opcional) |
|----------|----------|-----------|-------------------|
| Development | `http://localhost:8000/api/v1` | `ws://localhost:8000/ws/events` | `http://localhost:8000/graphql` |
| Staging | `https://engine-staging.aipensa.com/api/v1` | `wss://engine-staging.aipensa.com/ws/events` | `https://engine-staging.aipensa.com/graphql` |
| Production | `https://engine.aipensa.com/api/v1` | `wss://engine.aipensa.com/ws/events` | `https://engine.aipensa.com/graphql` |

---

## 🔐 AUTENTICAÇÃO E AUTORIZAÇÃO

### Headers Obrigatórios

```http
# Para todas as requisições
Authorization: Bearer <jwt_token>
X-Company-ID: <company_uuid>           # Obrigatório para operações multi-tenant
X-Workspace-ID: <workspace_uuid>       # Obrigatório se workspace ≠ company
Idempotency-Key: <uuid_v4>             # Obrigatório para POST/PUT/DELETE não-idempotentes
X-Request-ID: <uuid_v4>                # Recomendado para tracing
Accept: application/json
Content-Type: application/json
```

### JWT Claims (Engine valida)

```json
{
  "sub": "user_uuid",
  "company_id": "company_uuid",
  "workspace_id": "workspace_uuid",
  "roles": ["OWNER", "ADMIN", "MEMBER", "VIEWER"],
  "permissions": ["workflow.execute", "agent.create", "skill.install"],
  "exp": 1735689600,
  "engine_version": "1.2.0"
}
```

### Permission Matrix

| Recurso | Permissão Mínima | Roles Padrão |
|---------|------------------|--------------|
| `/runtime/*` | `runtime.read` | VIEWER+ |
| `/agents/*` | `agent.read` / `agent.write` | MEMBER+ / ADMIN+ |
| `/workflows/*` | `workflow.read` / `workflow.execute` | MEMBER+ / ADMIN+ |
| `/skills/*` | `skill.read` / `skill.install` | MEMBER+ / ADMIN+ |
| `/providers/*` | `provider.read` / `provider.connect` | ADMIN+ / OWNER |
| `/company-context/*` | `company.read` / `company.write` | MEMBER+ / ADMIN+ |
| `/sync/*` | `sync.export` / `sync.import` | OWNER |

---

## 📡 REST API ENDPOINTS

### Runtime & Health

#### GET `/api/v1/runtime/info`
Retorna informações da Engine.

**Response 200**
```json
{
  "version": "1.2.0",
  "build_date": "2026-07-28T10:00:00Z",
  "git_commit": "a1b2c3d4",
  "modules_loaded": 24,
  "plugins_loaded": 57,
  "uptime_seconds": 3600,
  "status": "healthy"
}
```

#### GET `/api/v1/runtime/health`
Health check detalhado por módulo.

**Response 200**
```json
{
  "status": "healthy",
  "timestamp": "2026-07-28T10:00:00Z",
  "modules": {
    "agent": {"status": "healthy", "latency_ms": 5},
    "workflow": {"status": "healthy", "latency_ms": 12},
    "skill": {"status": "degraded", "latency_ms": 200, "reason": "provider_timeout"},
    "llm": {"status": "healthy", "latency_ms": 50}
  },
  "dependencies": {
    "postgresql": {"status": "healthy", "latency_ms": 3},
    "redis": {"status": "healthy", "latency_ms": 1},
    "vector_db": {"status": "healthy", "latency_ms": 10}
  }
}
```

#### GET `/api/v1/runtime/metrics`
Métricas Prometheus-friendly.

**Response 200**
```json
{
  "events_processed_total": 15234,
  "events_failed_total": 12,
  "workflows_executed_total": 342,
  "workflows_failed_total": 5,
  "agents_active": 12,
  "skills_executed_total": 1205,
  "llm_tokens_consumed_total": 45000000,
  "llm_cost_usd_total": 12.50
}
```

---

### Modules

#### GET `/api/v1/modules`
Lista todos módulos carregados.

**Query Params**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `state` | string | - | Filtrar por estado (RUNNING, STOPPED, ERROR) |
| `category` | string | - | Filtrar por categoria (core, ai, orchestration, infra) |

**Response 200**
```json
{
  "modules": [
    {
      "name": "agent",
      "version": "1.0.0",
      "state": "RUNNING",
      "category": "intelligence",
      "metadata": {
        "description": "Agent lifecycle and message passing",
        "capabilities": ["create_agent", "message_passing", "task_queue"],
        "dependencies": ["conversation", "skill", "llm"]
      },
      "health": {"status": "healthy", "last_check": "2026-07-28T10:00:00Z"}
    }
  ],
  "total": 24
}
```

#### GET `/api/v1/modules/{module_name}/health`
Health check específico do módulo.

**Response 200**
```json
{
  "module": "workflow",
  "status": "healthy",
  "checks": {
    "dag_executor": "ok",
    "persistence": "ok",
    "scheduler_integration": "ok"
  },
  "latency_ms": 15,
  "timestamp": "2026-07-28T10:00:00Z"
}
```

#### POST `/api/v1/modules/{module_name}/execute`
Executar operação customizada do módulo.

**Request**
```json
{
  "operation": "pause_all_workflows",
  "params": {"reason": "maintenance"}
}
```

**Response 200**
```json
{
  "success": true,
  "result": {"paused": 5, "already_paused": 2},
  "execution_id": "exec_abc123"
}
```

---

### Agents / Employees

#### GET `/api/v1/companies/{company_id}/employees`
Lista employees da empresa.

**Query Params**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `team_id` | string | - | Filtrar por team |
| `role` | string | - | Filtrar por role (CEO, MARKETING, etc) |
| `enabled` | boolean | true | Apenas habilitados |
| `limit` | int | 50 | Max resultados |
| `offset` | int | 0 | Paginação |

**Response 200**
```json
{
  "employees": [
    {
      "employee_id": "emp_mgr_001",
      "company_id": "comp_abc123",
      "team_id": "team_leadership",
      "name": "Manager IA",
      "role": "CEO",
      "specialization": "Strategic planning & orchestration",
      "skills": ["strategic_planning", "news_monitoring", "kpi_analysis"],
      "model": "meta/llama-3.1-70b-instruct",
      "temperature": 0.3,
      "memory_scope": "COMPANY",
      "permissions": ["workflow.create", "workflow.execute", "team.manage"],
      "enabled": true,
      "version": "1.2.0",
      "configuration": {
        "max_tokens": 4096,
        "timeout_seconds": 120,
        "retry_attempts": 3
      },
      "status": "idle",
      "current_task": null,
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-07-20T14:30:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 50
}
```

#### POST `/api/v1/companies/{company_id}/employees`
Criar novo Employee.

**Request**
```json
{
  "employee_id": "emp_social_001",
  "name": "Social Media IA",
  "role": "SOCIAL_MEDIA",
  "specialization": "Copywriting & community management",
  "team_id": "team_marketing",
  "skills": ["copywriting", "hashtag_research", "engagement_analysis"],
  "model": "meta/llama-3.1-8b-instruct",
  "temperature": 0.7,
  "memory_scope": "TEAM",
  "permissions": ["skill.execute:copywriting", "provider.use:meta"],
  "configuration": {
    "max_tokens": 2048,
    "system_prompt_addendum": "Use emojis. Tom descontraído."
  }
}
```

**Response 201**
```json
{
  "employee_id": "emp_social_001",
  "status": "created",
  "version": "1.0.0",
  "agent_id": "emp_social_001"
}
```

#### GET `/api/v1/companies/{company_id}/employees/{employee_id}`
Detalhes completos do Employee.

**Response 200**
```json
{
  "employee_id": "emp_social_001",
  "...": "campos do list +",
  "agent_state": {
    "status": "running",
    "memory_usage_mb": 45,
    "tasks_completed": 127,
    "tasks_failed": 3,
    "avg_response_time_ms": 1200,
    "last_activity": "2026-07-28T09:45:00Z"
  },
  "skill_permissions": [
    {"skill_id": "copywriting", "allowed": true, "rate_limit": 60},
    {"skill_id": "image_generation", "allowed": false}
  ],
  "provider_access": [
    {"provider_id": "meta", "scopes": ["instagram_post", "facebook_post"]}
  ]
}
```

#### PATCH `/api/v1/companies/{company_id}/employees/{employee_id}`
Atualizar Employee (partial update).

**Request**
```json
{
  "temperature": 0.8,
  "skills": ["copywriting", "hashtag_research", "engagement_analysis", "trend_analysis"],
  "configuration": {
    "max_tokens": 2048,
    "system_prompt_addendum": "Use emojis. Tom descontraído. Foque em engajamento."
  }
}
```

#### DELETE `/api/v1/companies/{company_id}/employees/{employee_id}`
Desativar Employee (soft delete - mantém histórico).

**Response 200**
```json
{
  "employee_id": "emp_social_001",
  "status": "deactivated",
  "deactivated_at": "2026-07-28T10:00:00Z"
}
```

#### POST `/api/v1/companies/{company_id}/employees/{employee_id}/execute`
Executar task no Employee.

**Request**
```json
{
  "task": "create_social_post",
  "input": {
    "topic": "Black Friday sale",
    "platform": "instagram",
    "tone": "urgent"
  },
  "context": {"campaign_id": "camp_bf_2026"},
  "async": true
}
```

**Response 202 (async) / 200 (sync)**
```json
{
  "task_id": "task_xyz789",
  "status": "queued",
  "employee_id": "emp_social_001",
  "correlation_id": "corr_abc123"
}
```

---

### Teams

#### GET `/api/v1/companies/{company_id}/teams`
Lista teams da empresa.

**Response 200**
```json
{
  "teams": [
    {
      "team_id": "team_marketing",
      "company_id": "comp_abc123",
      "name": "Marketing Team",
      "description": "Responsável por conteúdo, campanhas e social media",
      "members": ["emp_social_001", "emp_designer_001", "emp_video_001"],
      "shared_context": {
        "brand_guidelines_ref": "company:brand",
        "campaign_calendar_ref": "workspace:marketing_calendar"
      },
      "workflows": ["daily_content", "weekly_campaign", "monthly_report"],
      "created_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total": 3
}
```

#### POST `/api/v1/companies/{company_id}/teams`
Criar Team.

**Request**
```json
{
  "team_id": "team_support",
  "name": "Support Team",
  "description": "Atendimento ao cliente e suporte técnico",
  "members": ["emp_support_001", "emp_support_002"],
  "shared_context": {"kb_ref": "company:knowledge_base"}
}
```

#### POST `/api/v1/companies/{company_id}/teams/{team_id}/members`
Adicionar membro ao Team.

**Request**
```json
{
  "employee_id": "emp_support_003"
}
```

---

### Skills

#### GET `/api/v1/skills`
Lista skills disponíveis (Marketplace + Custom).

**Query Params**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | - | BUILTIN, CUSTOM, INTEGRATION, COMPOSITE, AI_GENERATED |
| `category` | string | - | Filtrar por categoria |
| `company_id` | string | - | Skills da empresa (custom) |
| `installed` | boolean | false | Apenas instaladas na empresa |

**Response 200**
```json
{
  "skills": [
    {
      "skill_id": "copywriting",
      "name": "Copywriting Specialist",
      "type": "COMPOSITE",
      "category": "marketing",
      "version": "1.3.0",
      "description": "Gera copy para social media, email, ads com brand check",
      "input_schema": {
        "type": "object",
        "properties": {
          "topic": {"type": "string"},
          "platform": {"type": "string", "enum": ["instagram", "linkedin", "twitter", "email"]},
          "tone": {"type": "string", "enum": ["professional", "casual", "urgent", "friendly"]},
          "target_audience": {"type": "string"}
        },
        "required": ["topic", "platform"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "copy": {"type": "string"},
          "hashtags": {"type": "array", "items": {"type": "string"}},
          "cta": {"type": "string"}
        }
      },
      "definition": {
        "steps": [
          {"step_id": "generate", "skill_id": "llm_generation", "params": {"template": "social_copy"}},
          {"step_id": "brand_check", "skill_id": "brand_voice_check", "params": {}}
        ],
        "edges": [{"from": "generate", "to": "brand_check"}]
      },
      "dependencies": ["llm_generation", "brand_voice_check"],
      "rate_limit": {"requests_per_minute": 60},
      "permissions_required": ["skill.execute:llm_generation"],
      "provider_requirements": ["llm"],
      "installed": true,
      "marketplace": true,
      "author": "aipensa",
      "tags": ["marketing", "social", "copywriting"]
    }
  ],
  "total": 45
}
```

#### POST `/api/v1/companies/{company_id}/skills/{skill_id}/install`
Instalar skill na empresa.

**Request**
```json
{
  "version": "1.3.0",
  "configuration": {
    "default_platform": "instagram",
    "brand_strictness": "high"
  }
}
```

#### POST `/api/v1/companies/{company_id}/skills`
Criar Custom Skill.

**Request**
```json
{
  "skill_id": "custom_competitor_analysis",
  "name": "Análise de Concorrentes Personalizada",
  "type": "CUSTOM",
  "category": "marketing",
  "description": "Analisa concorrentes específicos da empresa",
  "executor": "function",
  "entry_point": "skills.custom.competitor_analysis.run",
  "input_schema": {...},
  "output_schema": {...},
  "configuration": {
    "competitors": ["competitor_a", "competitor_b"],
    "metrics": ["followers", "engagement", "post_frequency"]
  }
}
```

---

### Providers

#### GET `/api/v1/providers`
Lista providers registrados na Engine.

**Response 200**
```json
{
  "providers": [
    {
      "provider_id": "meta",
      "name": "Meta (Instagram/Facebook/WhatsApp)",
      "type": "SOCIAL",
      "version": "2.1.0",
      "description": "APIs oficiais Meta Graph API",
      "capabilities": [
        "instagram_post", "instagram_story", "instagram_reel",
        "facebook_post", "facebook_ads",
        "whatsapp_message", "whatsapp_template"
      ],
      "config_schema": {
        "type": "object",
        "properties": {
          "app_id": {"type": "string"},
          "app_secret": {"type": "string", "format": "password"},
          "default_page_id": {"type": "string"}
        },
        "required": ["app_id", "app_secret"]
      },
      "oauth": {
        "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scopes": ["instagram_basic", "instagram_content_publish", "pages_show_list", "whatsapp_business_messaging"]
      },
      "rate_limits": {
        "instagram_post": 25,
        "facebook_post": 200,
        "whatsapp_message": 1000
      }
    }
  ],
  "total": 12
}
```

#### POST `/api/v1/companies/{company_id}/providers/{provider_id}/connect`
Conectar provider à empresa (OAuth ou credenciais diretas).

**Request (Credenciais Diretas)**
```json
{
  "connection_id": "conn_meta_acme",
  "credentials": {
    "app_id": "123456789",
    "app_secret": "***",
    "access_token": "EAA***",
    "page_id": "987654321",
    "instagram_business_id": "17841400008462056"
  },
  "scopes": ["instagram_post", "facebook_post", "whatsapp_message"]
}
```

**Request (OAuth Initiate)**
```json
{
  "connection_id": "conn_meta_acme_oauth",
  "oauth": true,
  "redirect_uri": "https://app.aipensa.com/oauth/callback",
  "scopes": ["instagram_basic", "instagram_content_publish"]
}
```

**Response 200 (OAuth)**
```json
{
  "connection_id": "conn_meta_acme_oauth",
  "status": "pending_oauth",
  "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth?client_id=...&redirect_uri=...&scope=...&state=...",
  "expires_at": "2026-07-28T10:10:00Z"
}
```

**Response 201 (Credenciais Diretas)**
```json
{
  "connection_id": "conn_meta_acme",
  "provider_id": "meta",
  "company_id": "comp_abc123",
  "status": "connected",
  "capabilities_granted": ["instagram_post", "facebook_post", "whatsapp_message"],
  "connected_at": "2026-07-28T10:00:00Z"
}
```

#### GET `/api/v1/companies/{company_id}/providers/connections`
Lista conexões ativas da empresa.

---

### Workflows

#### GET `/api/v1/companies/{company_id}/workflows`
Lista workflows da empresa.

**Query Params**
| Param | Type | Description |
|-------|------|-------------|
| `team_id` | string | Filtrar por team |
| `status` | string | ACTIVE, INACTIVE, ARCHIVED |
| `tag` | string | Tag personalizada |

**Response 200**
```json
{
  "workflows": [
    {
      "workflow_id": "daily_content",
      "name": "Daily Content Pipeline",
      "version": "1.2.0",
      "description": "Gera conteúdo diário: Manager → Social Media → Designer/Video → Publisher",
      "team_id": "team_marketing",
      "tags": ["daily", "marketing", "content"],
      "definition": {
        "nodes": [
          {"node_id": "fetch_trends", "type": "EMPLOYEE_TASK", "config": {"employee_role": "CEO", "action": "fetch_trending_news"}},
          {"node_id": "write_copy", "type": "EMPLOYEE_TASK", "config": {"employee_role": "SOCIAL_MEDIA", "action": "create_social_posts"}},
          {"node_id": "create_visuals", "type": "PARALLEL", "branches": [
            {"node_id": "design_images", "type": "EMPLOYEE_TASK", "config": {"employee_role": "DESIGNER", "action": "create_images"}},
            {"node_id": "create_videos", "type": "EMPLOYEE_TASK", "config": {"employee_role": "VIDEO_CREATOR", "action": "create_video_scripts"}}
          ]},
          {"node_id": "publish", "type": "SKILL_EXECUTION", "config": {"skill_id": "social_publisher", "params": {}}}
        ],
        "edges": [
          {"from": "fetch_trends", "to": "write_copy"},
          {"from": "write_copy", "to": "create_visuals"},
          {"from": "create_visuals", "to": "publish"}
        ]
      },
      "status": "ACTIVE",
      "schedule": {"cron": "0 6 * * *", "timezone": "America/Sao_Paulo"},
      "stats": {
        "executions_total": 180,
        "success_rate": 0.97,
        "avg_duration_seconds": 45
      },
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-07-20T14:30:00Z"
    }
  ],
  "total": 12
}
```

#### POST `/api/v1/companies/{company_id}/workflows`
Criar workflow.

**Request**
```json
{
  "workflow_id": "weekly_campaign",
  "name": "Weekly Campaign Generator",
  "version": "1.0.0",
  "description": "Gera campanha semanal completa",
  "team_id": "team_marketing",
  "definition": {
    "nodes": [...],
    "edges": [...]
  },
  "schedule": {"cron": "0 9 * * 1", "timezone": "America/Sao_Paulo"}
}
```

#### POST `/api/v1/companies/{company_id}/workflows/{workflow_id}/execute`
Executar workflow manualmente.

**Request**
```json
{
  "input": {"campaign_theme": "Black Friday"},
  "context": {"budget": 5000, "target_audience": "young_adults"},
  "async": true
}
```

**Response 202**
```json
{
  "execution_id": "exec_weekly_001",
  "workflow_id": "weekly_campaign",
  "status": "queued",
  "correlation_id": "corr_campaign_001"
}
```

#### GET `/api/v1/companies/{company_id}/workflows/executions/{execution_id}`
Status de execução.

**Response 200**
```json
{
  "execution_id": "exec_weekly_001",
  "workflow_id": "weekly_campaign",
  "status": "running",
  "current_node": "create_visuals",
  "progress": 0.6,
  "started_at": "2026-07-28T09:00:00Z",
  "nodes": [
    {"node_id": "fetch_trends", "status": "completed", "duration_ms": 2300, "output": {...}},
    {"node_id": "write_copy", "status": "completed", "duration_ms": 4500, "output": {...}},
    {"node_id": "create_visuals", "status": "running", "branches": {
      "design_images": {"status": "completed"},
      "create_videos": {"status": "running"}
    }},
    {"node_id": "publish", "status": "pending"}
  ],
  "correlation_id": "corr_campaign_001"
}
```

#### POST `/api/v1/companies/{company_id}/workflows/executions/{execution_id}/pause`
Pausar execução.

#### POST `/api/v1/companies/{company_id}/workflows/executions/{execution_id}/resume`
Retomar execução.

#### POST `/api/v1/companies/{company_id}/workflows/executions/{execution_id}/cancel`
Cancelar execução.

---

### Scheduler

#### GET `/api/v1/companies/{company_id}/schedules`
Lista jobs agendados.

#### POST `/api/v1/companies/{company_id}/schedules`
Criar job agendado.

**Request**
```json
{
  "job_id": "daily_content_trigger",
  "name": "Daily Content Pipeline Trigger",
  "workflow_id": "daily_content",
  "cron": "0 6 * * *",
  "timezone": "America/Sao_Paulo",
  "enabled": true,
  "max_concurrent": 1,
  "retry_policy": {"max_attempts": 3, "backoff_seconds": 300}
}
```

---

### Company Context

#### GET `/api/v1/companies/{company_id}/context`
Retorna contexto completo da empresa (resolver).

**Response 200**
```json
{
  "company_id": "comp_abc123",
  "profile": {
    "name": "Acme Corp",
    "legal_name": "Acme Corporation LTDA",
    "tax_id": "12.345.678/0001-90",
    "segment": "ecommerce",
    "size": "medium",
    "founded_date": "2020-01-15"
  },
  "brand": {
    "name": "Acme",
    "tagline": "Inovação que entrega",
    "colors": {"primary": "#0066CC", "secondary": "#00AA44", "accent": "#FF6600"},
    "logo_url": "https://cdn.acme.com/logo.png",
    "voice_tone": "friendly",
    "guidelines": "Sempre use linguagem inclusiva. Evite jargões técnicos..."
  },
  "products": {
    "products": [
      {"id": "prod_001", "name": "Acme Widget Pro", "price": 299.90, "category": "electronics"}
    ],
    "services": [
      {"id": "svc_001", "name": "Acme Care+", "price": 29.90, "recurring": true}
    ]
  },
  "channels": {
    "instagram": {"handle": "@acme", "followers": 15000, "verified": true},
    "whatsapp": {"number": "+5511999999999", "verified": true, "business_account": true}
  },
  "goals": {
    "okrs": [
      {"objective": "Aumentar receita 30%", "key_results": [{"metric": "monthly_revenue", "target": 1300000}]}
    ],
    "kpis": [{"name": "CAC", "current": 150, "target": 100}]
  },
  "knowledge_summary": {
    "documents_count": 42,
    "faqs_count": 15,
    "last_updated": "2026-07-25T10:00:00Z"
  }
}
```

#### PUT `/api/v1/companies/{company_id}/context/profile`
Atualizar CompanyProfile.

#### PUT `/api/v1/companies/{company_id}/context/brand`
Atualizar CompanyBrand.

#### POST `/api/v1/companies/{company_id}/context/knowledge`
Adicionar documento ao Knowledge Base.

**Request**
```json
{
  "document_id": "doc_return_policy",
  "title": "Política de Trocas e Devoluções",
  "content": "Produtos podem ser devolvidos em até 30 dias...",
  "category": "policy",
  "tags": ["returns", "customer_service", "legal"]
}
```

#### GET `/api/v1/companies/{company_id}/context/knowledge/search`
Busca semântica no Knowledge Base.

**Query Params**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | - | Query de busca |
| `role` | string | - | Filtrar relevância para role |
| `limit` | int | 10 | Max resultados |

---

### Sync Package (Export/Import)

#### GET `/api/v1/companies/{company_id}/sync/export`
Exportar pacote completo de sincronização.

**Query Params**
| Param | Type | Description |
|-------|------|-------------|
| `version` | string | Versão do sync package (default: latest) |
| `include_secrets` | boolean | false - Incluir referências a secrets (não valores) |

**Response 200** - `application/x-yaml` ou `application/json`
```yaml
version: "1.0"
engine_version: "1.2.0"
exported_at: "2026-07-28T10:00:00Z"
checksum: "sha256:a1b2c3d4..."
companies: [...]
employees: [...]
teams: [...]
skills: [...]
providers: [...]
provider_connections: [...]  # apenas connection_ids, credenciais em secrets
workflows: [...]
schedules: [...]
plugins: [...]
llm_models: [...]
memory_configs: [...]
```

#### POST `/api/v1/companies/{company_id}/sync/import`
Importar pacote de sincronização.

**Request** - `multipart/form-data` com arquivo YAML/JSON

**Response 200**
```json
{
  "import_id": "imp_abc123",
  "status": "completed",
  "summary": {
    "companies": 1,
    "employees": 10,
    "teams": 3,
    "skills": 25,
    "providers": 5,
    "workflows": 12,
    "schedules": 8
  },
  "warnings": [
    "Provider connection 'conn_meta_acme' requires credential update"
  ],
  "errors": []
}
```

#### GET `/api/v1/companies/{company_id}/sync/imports/{import_id}/status`
Status de importação assíncrona.

---

### Runtime Explorer (Dev/Debug)

#### GET `/api/v1/explorer/overview`
Visão geral estilo Task Manager.

**Response 200**
```json
{
  "runtime": {"status": "healthy", "uptime": "2d 5h", "version": "1.2.0"},
  "modules": {
    "total": 24, "running": 23, "degraded": 1, "stopped": 0
  },
  "agents": {"active": 12, "idle": 8, "busy": 4, "error": 0},
  "workflows": {"running": 3, "queued": 5, "completed_today": 42, "failed_today": 1},
  "queues": {"messages_pending": 156, "processing": 12, "dlq": 3},
  "memory": {"stores": 45, "total_keys": 120000, "size_mb": 512},
  "llm": {"requests_today": 12500, "tokens_today": 45000000, "cost_usd_today": 12.50},
  "events": {"per_second": 45, "history_size": 9847, "dlq_size": 12}
}
```

#### GET `/api/v1/explorer/agents`
Lista todos agents/employees com estado runtime.

#### GET `/api/v1/explorer/workflows`
Workflows ativos com execuções recentes.

#### GET `/api/v1/explorer/queues`
Detalhes das filas (pending, processing, dlq por queue).

#### GET `/api/v1/explorer/memory`
Stores, keys, tamanho, TTLs.

#### GET `/api/v1/explorer/events/recent`
Últimos N eventos (com filtros).

#### GET `/api/v1/explorer/performance`
Métricas de latência, throughput, erros por módulo.

---

## 🔌 WEBSOCKET EVENT STREAM

### Conexão

```javascript
const ws = new WebSocket('wss://engine.aipensa.com/ws/events', {
  headers: {
    'Authorization': 'Bearer <token>',
    'X-Company-ID': '<company_id>',
    'X-Workspace-ID': '<workspace_id>'
  }
});

ws.onopen = () => {
  // Subscrever a event types específicos (opcional)
  ws.send(JSON.stringify({
    type: 'subscribe',
    event_types: ['WORKFLOW_*', 'SKILL_*', 'AGENT_*', 'COMPANY_*'],
    filters: {company_id: '<company_id>'}
  }));
};

ws.onmessage = (event) => {
  const runtimeEvent = JSON.parse(event.data);
  // Processar evento
  console.log(runtimeEvent.event_type, runtimeEvent.payload);
};
```

### Handshake

```json
// Client → Server
{
  "type": "hello",
  "protocol_version": "1.0",
  "company_id": "comp_abc123",
  "event_types": ["*"]  // ou lista específica
}

// Server → Client
{
  "type": "welcome",
  "session_id": "ws_sess_abc123",
  "server_time": "2026-07-28T10:00:00Z",
  "supported_event_types": 155
}
```

### Heartbeat

```json
// Client → Server (cada 30s)
{"type": "ping"}

// Server → Client
{"type": "pong", "server_time": "2026-07-28T10:00:30Z"}
```

### Event Format (RuntimeEvent)

```json
{
  "event_id": "evt_abc123def456",
  "event_type": "WORKFLOW_STEP_COMPLETED",
  "source": "workflow_module",
  "timestamp": "2026-07-28T10:00:00.123Z",
  "correlation_id": "corr_campaign_001",
  "causation_id": "evt_prev_step_started",
  "priority": "NORMAL",
  "tags": ["workflow", "marketing", "daily_content"],
  "payload": {
    "workflow_id": "daily_content",
    "execution_id": "exec_001",
    "step_id": "write_copy",
    "employee_id": "emp_social_001",
    "duration_ms": 4500,
    "output": {"posts_created": 3, "platform": "instagram"}
  }
}
```

### Subscribe/Unsubscribe (Dinâmico)

```json
// Subscribe
{"type": "subscribe", "event_types": ["WORKFLOW_*", "AGENT_MESSAGE"]}

// Unsubscribe
{"type": "unsubscribe", "event_types": ["AGENT_MESSAGE"]}

// Response
{"type": "subscribed", "event_types": ["WORKFLOW_*", "AGENT_MESSAGE"]}
```

---

## 📦 PYDANTIC MODELS (Referência)

### Core Models

```python
# runtime/api/models.py

class RuntimeInfo(BaseModel):
    version: str
    build_date: datetime
    git_commit: str
    modules_loaded: int
    plugins_loaded: int
    uptime_seconds: int
    status: Literal["healthy", "degraded", "unhealthy"]

class ModuleHealth(BaseModel):
    module: str
    status: Literal["healthy", "degraded", "unhealthy"]
    latency_ms: int
    checks: Dict[str, str]
    timestamp: datetime

class ModuleOperationRequest(BaseModel):
    operation: str
    params: Dict[str, Any] = {}

class ModuleOperationResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_id: str
```

### Employee Models

```python
class EmployeeRole(str, Enum):
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

class EmployeeProfile(BaseModel):
    employee_id: str
    company_id: str
    team_id: Optional[str] = None
    name: str
    role: EmployeeRole
    specialization: str
    skills: List[str] = []
    model: str = "meta/llama-3.1-8b-instruct"
    temperature: float = 0.7
    memory_scope: MemoryScope = MemoryScope.COMPANY
    permissions: List[str] = []
    enabled: bool = True
    version: str = "1.0.0"
    configuration: Dict[str, Any] = {}
    
    created_at: datetime
    updated_at: datetime

class EmployeeCreateRequest(EmployeeProfile):
    pass  # employee_id optional (auto-generated if not provided)

class EmployeeUpdateRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[EmployeeRole] = None
    specialization: Optional[str] = None
    skills: Optional[List[str]] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    memory_scope: Optional[MemoryScope] = None
    permissions: Optional[List[str]] = None
    enabled: Optional[bool] = None
    configuration: Optional[Dict[str, Any]] = None
    version: Optional[str] = None  # Para optimistic locking
```

### Workflow Models

```python
class StepType(str, Enum):
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    WAIT = "wait"
    START = "start"
    END = "end"
    EMPLOYEE_TASK = "employee_task"      # NOVO
    SKILL_EXECUTION = "skill_execution"  # NOVO
    PROVIDER_CALL = "provider_call"      # NOVO
    COMPANY_CONTEXT = "company_context"  # NOVO
    TEAM_COLLABORATION = "team_collab"   # NOVO

class WorkflowNode(BaseModel):
    node_id: str
    type: StepType
    label: str
    config: Dict[str, Any] = {}
    position: Dict[str, float] = {}  # x, y para UI
    
    # Para EMPLOYEE_TASK
    employee_role: Optional[EmployeeRole] = None
    employee_action: Optional[str] = None
    
    # Para SKILL_EXECUTION
    skill_id: Optional[str] = None
    skill_params: Optional[Dict[str, Any]] = None
    
    # Para PROVIDER_CALL
    provider_id: Optional[str] = None
    provider_capability: Optional[str] = None
    provider_params: Optional[Dict[str, Any]] = None

class WorkflowEdge(BaseModel):
    edge_id: str
    from_node: str
    to_node: str
    condition: Optional[str] = None  # Para edges condicionais
    label: Optional[str] = None

class WorkflowDefinition(BaseModel):
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]

class WorkflowExecutionRequest(BaseModel):
    input: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    async_execution: bool = True

class WorkflowExecutionStatus(BaseModel):
    execution_id: str
    workflow_id: str
    status: Literal["queued", "running", "paused", "completed", "failed", "cancelled"]
    current_node: Optional[str] = None
    progress: float = 0.0
    started_at: datetime
    completed_at: Optional[datetime] = None
    nodes: List[NodeExecutionStatus] = []
    correlation_id: str
    error: Optional[str] = None
```

### Provider Models

```python
class ProviderType(str, Enum):
    LLM = "LLM"
    SOCIAL = "SOCIAL"
    COMMUNICATION = "COMMUNICATION"
    STORAGE = "STORAGE"
    PAYMENT = "PAYMENT"
    AI_SERVICE = "AI_SERVICE"
    DATA = "DATA"

class ProviderConnectionStatus(str, Enum):
    PENDING = "pending"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    EXPIRED = "expired"
    REVOKED = "revoked"

class ProviderConnection(BaseModel):
    connection_id: str
    provider_id: str
    company_id: str
    credentials_ref: str  # Reference to encrypted secrets
    status: ProviderConnectionStatus
    scopes: List[str] = []
    capabilities_granted: List[str] = []
    connected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    error: Optional[str] = None
```

### Company Context Models

```python
class CompanyProfile(BaseModel):
    company_id: str
    name: str
    legal_name: str
    tax_id: str
    segment: Literal["ecommerce", "clinic", "restaurant", "delivery", "saas", "marketplace", "other"]
    size: Literal["micro", "small", "medium", "large", "enterprise"]
    founded_date: date
    metadata: Dict[str, Any] = {}

class CompanyBrand(BaseModel):
    company_id: str
    name: str
    tagline: str
    colors: Dict[str, str]  # primary, secondary, accent, background, text
    logo_url: str
    voice_tone: Literal["professional", "friendly", "bold", "minimalist", "playful", "authoritative"]
    guidelines: str

class CompanyProducts(BaseModel):
    company_id: str
    products: List[Product] = []
    services: List[Service] = []

class CompanyChannels(BaseModel):
    company_id: str
    instagram: Optional[ChannelConfig] = None
    facebook: Optional[ChannelConfig] = None
    tiktok: Optional[ChannelConfig] = None
    whatsapp: Optional[ChannelConfig] = None
    website: Optional[ChannelConfig] = None
    google_business: Optional[ChannelConfig] = None
    linkedin: Optional[ChannelConfig] = None
    youtube: Optional[ChannelConfig] = None

class CompanyContext(BaseModel):
    company_id: str
    profile: CompanyProfile
    brand: CompanyBrand
    products: CompanyProducts
    channels: CompanyChannels
    goals: CompanyGoals
    knowledge: List[KnowledgeEntry] = []
```

---

## ❌ CÓDIGOS DE ERRO PADRONIZADOS

| HTTP | Code | Message | Quando |
|------|------|---------|--------|
| 400 | `VALIDATION_ERROR` | Request validation failed | Schema inválido |
| 401 | `UNAUTHORIZED` | Authentication required | Token inválido/ausente |
| 403 | `FORBIDDEN` | Insufficient permissions | Role não tem permissão |
| 404 | `NOT_FOUND` | Resource not found | ID inexistente |
| 409 | `CONFLICT` | Resource already exists | Duplicate ID |
| 409 | `VERSION_CONFLICT` | Resource version mismatch | Optimistic lock fail |
| 422 | `UNPROCESSABLE_ENTITY` | Business rule violation | Regra de negócio falhou |
| 429 | `RATE_LIMITED` | Too many requests | Rate limit excedido |
| 500 | `INTERNAL_ERROR` | Internal server error | Bug não tratado |
| 503 | `SERVICE_UNAVAILABLE` | Module unavailable | Módulo stopped/error |
| 504 | `TIMEOUT` | Operation timed out | Timeout execução |

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {"field": "employee_id", "message": "must be valid UUID", "code": "INVALID_UUID"},
      {"field": "skills", "message": "skill 'unknown_skill' not found", "code": "SKILL_NOT_FOUND"}
    ],
    "request_id": "req_abc123",
    "timestamp": "2026-07-28T10:00:00Z"
  }
}
```

---

## 🔄 VERSIONAMENTO E DEPRECIAÇÃO

### Header de Versão

```http
# Request
Accept-Version: v1

# Response
API-Version: v1
API-Deprecation: v1 (2027-07-28)  # Se deprecated
```

### Lifecycle

| Status | Headers | Comportamento |
|--------|---------|---------------|
| **Current** | `API-Version: v1` | Suporte total |
| **Deprecated** | `API-Version: v1`, `API-Deprecation: v1 (2027-07-28)` | Funciona, aviso no log |
| **Sunset** | `API-Version: v1`, `Sunset: Sat, 28 Jul 2027 00:00:00 GMT` | Funciona, retorna 410 em novas features |
| **Removed** | - | 410 Gone |

---

## 📋 CONTRATO DE COMPATIBILIDADE

### Garantias da Engine v1.x

1. **Endpoints existentes** - Nunca removidos na v1.x
2. **Campos de response** - Nunca removidos/renomeados (apenas adicionados)
3. **Event types** - Nunca removidos (apenas deprecated no doc)
4. **WebSocket protocol** - Compatível dentro da major version
5. **Sync Package v1** - Engine v1.x sempre lê/escreve v1
6. **Plugin API** - Estável dentro da major version

### Quebras Permitidas (Major Version)

- Remoção de endpoints deprecated
- Mudança na estrutura de evento (correlation_id → trace_id)
- Alteração no auth scheme (JWT → mTLS)
- Mudança no Sync Package format (v1 → v2)

---

**ESTE CONTRATO É LEI. QUALQUER IMPLEMENTAÇÃO QUE VIOLE ESTES CONTRATOS É BUG CRÍTICO.**