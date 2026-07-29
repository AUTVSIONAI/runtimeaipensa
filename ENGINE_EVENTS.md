# 📋 ENGINE_EVENTS.md - Catálogo Completo de Eventos da AIPENSA Engine

**Versão:** 1.0  
**Base:** `runtime/events/__init__.py` + Extensões Enterprise  
**Data:** 28 Julho 2026  
**Total de Event Types:** 155+ (Core) + 35+ (Enterprise Extensions) = ~190  

---

## 📊 VISÃO GERAL

### Estrutura de Evento Base

```python
@dataclass
class Event:
    event_type: str              # Tipo único (ex: "AgentCreated")
    source: str                  # Origem (ex: "agent:employee:john.doe")  
    timestamp: datetime          # UTC ISO 8601
    correlation_id: str          # UUID - Rastreia fluxo completo (causation chain)
    causation_id: Optional[str]  # UUID - Evento pai direto que causou este
    payload: Dict[str, Any]      # Dados do evento
    metadata: Dict[str, Any]     # Metadados extras (tags, tenant_id, etc)
    priority: EventPriority      # LOW/NORMAL/HIGH/CRITICAL
```

### Convenções de Nomenclatura

| Padrão | Exemplo | Significado |
|--------|---------|-------------|
| `{Domain}{Action}` | `AgentCreated` | Ação completada |
| `{Domain}{Action}Failed` | `AgentCreationFailed` | Falha |
| `{Domain}{Action}Started` | `WorkflowStarted` | Início async |
| `{Domain}{Entity}{Action}` | `MessageSent` | Entidade + ação |

---

## 🏗️ CAMADA 1: CORE RUNTIME (37 events)

### Runtime Lifecycle
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `RuntimeStarted` | `runtime:core` | `{version, config, modules:[]}` | HIGH | Engine iniciado |
| `RuntimeShutdown` | `runtime:core` | `{graceful:bool, reason}` | HIGH | Engine parando |
| `RuntimeError` | `runtime:core` | `{error, traceback, recoverable}` | CRITICAL | Erro fatal no runtime |

### Module Lifecycle
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `ModuleStarted` | `runtime:module:{name}` | `{module, version, config}` | HIGH | Módulo iniciado |
| `ModuleStopped` | `runtime:module:{name}` | `{module, reason}` | HIGH | Módulo parado |
| `ModuleError` | `runtime:module:{name}` | `{module, error, recoverable}` | HIGH | Erro no módulo |
| `ModuleHealthCheck` | `runtime:module:{name}` | `{module, status, details}` | NORMAL | Health check periódico |

### System Events
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `SystemError` | `runtime:system` | `{component, error, severity}` | CRITICAL | Erro de sistema |
| `SystemWarning` | `runtime:system` | `{component, message}` | HIGH | Aviso de sistema |
| `SystemInfo` | `runtime:system` | `{component, message}` | LOW | Info de sistema |
| `ConfigChanged` | `runtime:config` | `{keys_changed:[]}` | HIGH | Config alterada |
| `MetricsSnapshot` | `runtime:metrics` | `{cpu, memory, requests, latency_p99}` | LOW | Snapshot métricas (a cada 30s) |

---

## 🤖 CAMADA 2: AGENT / EMPLOYEE (35 events)

### Employee Lifecycle
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `EmployeeCreated` | `agent:employee:{id}` | `{employee_id, profile, team_id, capabilities:[]}` | HIGH | Funcionário criado |
| `EmployeeActivated` | `agent:employee:{id}` | `{employee_id, status}` | NORMAL | Ativado |
| `EmployeeDeactivated` | `agent:employee:{id}` | `{employee_id, reason}` | HIGH | Desativado |
| `EmployeeDeleted` | `agent:employee:{id}` | `{employee_id}` | CRITICAL | Deletado |
| `EmployeeProfileUpdated` | `agent:employee:{id}` | `{employee_id, changes:{}}` | NORMAL | Perfil atualizado |
| `EmployeeStatusChanged` | `agent:employee:{id}` | `{employee_id, from, to}` | NORMAL | Status mudou |

### Employee Assignment
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `EmployeeAssignedToTeam` | `agent:employee:{id}` | `{employee_id, team_id, role}` | NORMAL | Atribuído a time |
| `EmployeeRemovedFromTeam` | `agent:employee:{id}` | `{employee_id, team_id}` | NORMAL | Removido de time |
| `EmployeeSkillGranted` | `agent:employee:{id}` | `{employee_id, skill_id, level}` | NORMAL | Habilidade concedida |
| `EmployeeSkillRevoked` | `agent:employee:{id}` | `{employee_id, skill_id}` | NORMAL | Habilidade revogada |
| `EmployeeCredentialIssued` | `agent:employee:{id}` | `{employee_id, credential_id, expires_at}` | NORMAL | Credencial emitida |
| `EmployeeCredentialRevoked` | `agent:employee:{id}` | `{employee_id, credential_id}` | HIGH | Credencial revogada |

### Employee Execution
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `EmployeeTaskStarted` | `agent:employee:{id}` | `{employee_id, task_id, task_type, input:{} }` | NORMAL | Task iniciada |
| `EmployeeTaskCompleted` | `agent:employee:{id}` | `{employee_id, task_id, output:{} , duration_ms}` | NORMAL | Task completada |
| `EmployeeTaskFailed` | `agent:employee:{id}` | `{employee_id, task_id, error, duration_ms}` | HIGH | Task falhou |
| `EmployeeThinking` | `agent:employee:{id}` | `{employee_id, step, reasoning}` | LOW | Pensando (streaming) |
| `EmployeeToolCall` | `agent:employee:{id}` | `{employee_id, tool_name, args:{}, call_id}` | NORMAL | Tool chamada |
| `EmployeeToolResult` | `agent:employee:{id}` | `{employee_id, tool_name, result:{}, call_id}` | NORMAL | Tool resultou |
| `EmployeeMessageSent` | `agent:employee:{id}` | `{employee_id, to, message_type, content}` | NORMAL | Mensagem enviada |
| `EmployeeMessageReceived` | `agent:employee:{id}` | `{employee_id, from, message_type, content}` | NORMAL | Mensagem recebida |

---

## 👥 CAMADA 3: TEAM / WORKSPACE (28 events)

### Team Lifecycle
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `TeamCreated` | `workspace:team:{id}` | `{team_id, name, type, parent_team_id, config:{}}` | HIGH | Time criado |
| `TeamUpdated` | `workspace:team:{id}` | `{team_id, changes:{}}` | NORMAL | Time atualizado |
| `TeamDeleted` | `workspace:team:{id}` | `{team_id, force:bool}` | CRITICAL | Time deletado |
| `TeamArchived` | `workspace:team:{id}` | `{team_id, reason}` | HIGH | Time arquivado |
| `TeamRestored` | `workspace:team:{id}` | `{team_id}` | HIGH | Time restaurado |

### Team Membership
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `TeamMemberAdded` | `workspace:team:{id}` | `{team_id, employee_id, role, permissions:[]}` | NORMAL | Membro adicionado |
| `TeamMemberRemoved` | `workspace:team:{id}` | `{team_id, employee_id, reason}` | HIGH | Membro removido |
| `TeamMemberRoleChanged` | `workspace:team:{id}` | `{team_id, employee_id, from_role, to_role}` | NORMAL | Role alterado |
| `TeamInvitationSent` | `workspace:team:{id}` | `{team_id, email, role, invited_by}` | NORMAL | Convite enviado |
| `TeamInvitationAccepted` | `workspace:team:{id}` | `{team_id, employee_id, invitation_id}` | NORMAL | Convite aceito |

### Team Execution
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `TeamWorkflowStarted` | `workspace:team:{id}` | `{team_id, workflow_id, execution_id, trigger}` | NORMAL | Workflow do time iniciado |
| `TeamWorkflowCompleted` | `workspace:team:{id}` | `{team_id, execution_id, result:{}, duration_ms}` | NORMAL | Workflow completado |
| `TeamWorkflowFailed` | `workspace:team:{id}` | `{team_id, execution_id, error}` | HIGH | Workflow falhou |
| `TeamTaskDelegated` | `workspace:team:{id}` | `{team_id, from_employee, to_employee, task_id}` | NORMAL | Task delegada |
| `TeamHandoffOccurred` | `workspace:team:{id}` | `{team_id, from_employee, to_employee, context:{}}` | NORMAL | Handoff entre employees |

### Company/Workspace (Multi-tenant)
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `CompanyCreated` | `workspace:company:{id}` | `{company_id, name, domain, settings:{}}` | HIGH | Empresa criada |
| `CompanyUpdated` | `workspace:company:{id}` | `{company_id, changes:{}}` | NORMAL | Empresa atualizada |
| `CompanyDeleted` | `workspace:company:{id}` | `{company_id}` | CRITICAL | Empresa deletada |
| `CompanySettingsChanged` | `workspace:company:{id}` | `{company_id, settings:{}}` | HIGH | Configs da empresa |
| `CompanyQuotaExceeded` | `workspace:company:{id}` | `{company_id, resource, limit, current}` | HIGH | Quota excedida |
| `CompanyBillingEvent` | `workspace:company:{id}` | `{company_id, event_type, amount, currency}` | NORMAL | Evento billing |

---

## 🧠 CAMADA 4: SKILL REGISTRY (22 events)

### Skill Lifecycle
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `SkillRegistered` | `skill:registry` | `{skill_id, name, version, type, capabilities:[]}` | HIGH | Skill registrada |
| `SkillUpdated` | `skill:registry` | `{skill_id, version, changes:{}}` | NORMAL | Skill atualizada |
| `SkillDeprecated` | `skill:registry` | `{skill_id, version, replacement_skill_id}` | NORMAL | Depreciada |
| `SkillRemoved` | `skill:registry` | `{skill_id, version}` | HIGH | Removida |
| `SkillInstalled` | `skill:registry` | `{skill_id, version, source, tenant_id?}` | NORMAL | Instalada (marketplace) |
| `SkillUninstalled` | `skill:registry` | `{skill_id, version, tenant_id?}` | NORMAL | Desinstalada |

### Skill Composition (Composite Skills)
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `SkillComposed` | `skill:composer` | `{composite_skill_id, component_skills:[], composition_type}` | NORMAL | Skill composta criada |
| `SkillCompositionFailed` | `skill:composer` | `{composite_skill_id, component_skills, error}` | HIGH | Falha na composição |

### Skill Execution
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `SkillExecutionStarted` | `skill:executor:{id}` | `{skill_id, execution_id, input:{}, employee_id}` | NORMAL | Execução iniciada |
| `SkillExecutionCompleted` | `skill:executor:{id}` | `{skill_id, execution_id, output:{}, duration_ms}` | NORMAL | Completada |
| `SkillExecutionFailed` | `skill:executor:{id}` | `{skill_id, execution_id, error, duration_ms}` | HIGH | Falhou |
| `SkillExecutionPartial` | `skill:executor:{id}` | `{skill_id, execution_id, step, output:{}}` | LOW | Parcial (streaming) |
| `SkillValidationPassed` | `skill:validator` | `{skill_id, version, validators:[]}` | NORMAL | Validação passou |
| `SkillValidationFailed` | `skill:validator` | `{skill_id, version, errors:[]}` | HIGH | Validação falhou |

### Skill Marketplace
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `SkillPublished` | `skill:marketplace` | `{skill_id, version, publisher, price}` | NORMAL | Publicada no marketplace |
| `SkillPurchased` | `skill:marketplace` | `{skill_id, version, buyer_tenant_id, price}` | NORMAL | Comprada |
| `SkillReviewSubmitted` | `skill:marketplace` | `{skill_id, reviewer_id, rating, comment}` | LOW | Review submetido |
| `SkillVulnerabilityFound` | `skill:security` | `{skill_id, version, severity, cve}` | CRITICAL | Vulnerabilidade encontrada |

---

## 🔌 CAMADA 5: PROVIDER REGISTRY (30 events)

### Provider Lifecycle
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `ProviderRegistered` | `provider:registry` | `{provider_id, name, type, version, capabilities:[]}` | HIGH | Provider registrado |
| `ProviderUpdated` | `provider:registry` | `{provider_id, version, changes:{}}` | NORMAL | Provider atualizado |
| `ProviderDeprecated` | `provider:registry` | `{provider_id, version, replacement_provider_id}` | NORMAL | Depreciado |
| `ProviderRemoved` | `provider:registry` | `{provider_id}` | HIGH | Removido |
| `ProviderHealthChanged` | `provider:registry` | `{provider_id, status, details:{}}` | NORMAL | Health status mudou |

### Provider Connection
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `ProviderConnected` | `provider:{id}` | `{provider_id, connection_id, config:{}}` | NORMAL | Conexão estabelecida |
| `ProviderDisconnected` | `provider:{id}` | `{provider_id, connection_id, reason}` | HIGH | Desconectado |
| `ProviderConnectionFailed` | `provider:{id}` | `{provider_id, error, retry_count}` | HIGH | Falha conexão |
| `ProviderReconnected` | `provider:{id}` | `{provider_id, connection_id, downtime_ms}` | NORMAL | Reconectado |
| `ProviderAuthRefreshed` | `provider:{id}` | `{provider_id, connection_id, token_expires_at}` | NORMAL | Auth renovado |
| `ProviderAuthFailed` | `provider:{id}` | `{provider_id, error}` | CRITICAL | Auth falhou |

### Provider Operations
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `ProviderRequestStarted` | `provider:{id}` | `{provider_id, operation, request_id, correlation_id}` | NORMAL | Request iniciado |
| `ProviderRequestCompleted` | `provider:{id}` | `{provider_id, operation, request_id, response:{}, duration_ms}` | NORMAL | Request completado |
| `ProviderRequestFailed` | `provider:{id}` | `{provider_id, operation, request_id, error, duration_ms}` | HIGH | Request falhou |
| `ProviderRequestRetried` | `provider:{id}` | `{provider_id, operation, request_id, attempt, max_attempts}` | LOW | Tentativa retry |
| `ProviderRateLimitHit` | `provider:{id}` | `{provider_id, operation, limit, reset_at}` | HIGH | Rate limit atingido |
| `ProviderQuotaExceeded` | `provider:{id}` | `{provider_id, resource, quota, current}` | CRITICAL | Quota excedida |
| `ProviderWebhookReceived` | `provider:{id}` | `{provider_id, webhook_type, payload:{}, signature_valid}` | NORMAL | Webhook recebido |
| `ProviderWebhookProcessed` | `provider:{id}` | `{provider_id, webhook_type, event_id, processed_ok}` | NORMAL | Webhook processado |
| `ProviderWebhookFailed` | `provider:{id}` | `{provider_id, webhook_type, event_id, error}` | HIGH | Webhook falhou |

### Provider Types Específicos (examples)
| Tipo | Exemplos de Operações |
|------|----------------------|
| `llm` | `chat_completion`, `embedding`, `moderation`, `function_call` |
| `messaging` | `send_message`, `send_template`, `get_templates`, `register_webhook` |
| `voice` | `text_to_speech`, `speech_to_text`, `stream_audio`, `voice_clone` |
| `vision` | `analyze_image`, `ocr`, `face_detect`, `object_detect` |
| `video` | `generate_video`, `edit_video`, `transcribe_video` |
| `storage` | `upload`, `download`, `delete`, `list`, `presigned_url` |
| `search` | `web_search`, `news_search`, `academic_search` |
| `payment` | `create_payment`, `refund`, `subscription_create`, `webhook` |
| `crm` | `create_contact`, `update_deal`, `get_pipeline`, `sync` |
| `calendar` | `create_event`, `get_events`, `find_slots`, `send_invite` |

---

## 🔌 CAMADA 6: PLUGIN SYSTEM (18 events)

| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `PluginLoaded` | `plugin:manager` | `{plugin_id, type, version, path}` | HIGH | Plugin carregado |
| `PluginUnloaded` | `plugin:manager` | `{plugin_id, type}` | HIGH | Plugin descarregado |
| `PluginReloaded` | `plugin:manager` | `{plugin_id, old_version, new_version}` | NORMAL | Plugin recarregado |
| `PluginLoadFailed` | `plugin:manager` | `{plugin_id, error, traceback}` | CRITICAL | Falha ao carregar |
| `PluginConfigChanged` | `plugin:manager` | `{plugin_id, config:{}}` | NORMAL | Config alterada |
| `PluginHealthCheckFailed` | `plugin:manager` | `{plugin_id, error}` | HIGH | Health check falhou |
| `ToolRegistered` | `tool:registry` | `{tool_id, plugin_id, name, schema:{}}` | NORMAL | Tool registrada |
| `ToolUnregistered` | `tool:registry` | `{tool_id, plugin_id}` | NORMAL | Tool removida |
| `ToolExecutionStarted` | `tool:executor` | `{tool_id, call_id, args:{}, employee_id}` | LOW | Execução iniciada |
| `ToolExecutionCompleted` | `tool:executor` | `{tool_id, call_id, result:{}, duration_ms}` | LOW | Completada |
| `ToolExecutionFailed` | `tool:executor` | `{tool_id, call_id, error, duration_ms}` | NORMAL | Falhou |
| `LLMProviderRegistered` | `llm:registry` | `{provider_id, name, models:[], capabilities:[]}` | NORMAL | LLM provider registrado |
| `LLMProviderRemoved` | `llm:registry` | `{provider_id}` | NORMAL | Removido |
| `MemoryBackendRegistered` | `memory:registry` | `{backend_id, type, capabilities:[]}` | NORMAL | Memory backend |
| `StorageBackendRegistered` | `storage:registry` | `{backend_id, type, capabilities:[]}` | NORMAL | Storage backend |
| `AuthProviderRegistered` | `auth:registry` | `{provider_id, type, config:{}}` | NORMAL | Auth provider |
| `SandboxBackendRegistered` | `sandbox:registry` | `{backend_id, type, capabilities:[]}` | NORMAL | Sandbox backend |

---

## 🔄 CAMADA 7: WORKFLOW / SCHEDULER / QUEUE (35 events)

### Workflow
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `WorkflowCreated` | `workflow:registry` | `{workflow_id, name, version, nodes:[], edges:[]}` | NORMAL | Workflow criado |
| `WorkflowUpdated` | `workflow:registry` | `{workflow_id, version, changes:{}}` | NORMAL | Atualizado |
| `WorkflowDeleted` | `workflow:registry` | `{workflow_id}` | HIGH | Deletado |
| `WorkflowExecutionStarted` | `workflow:executor` | `{execution_id, workflow_id, trigger, input:{}, correlation_id}` | NORMAL | Execução iniciada |
| `WorkflowExecutionCompleted` | `workflow:executor` | `{execution_id, workflow_id, output:{}, duration_ms}` | NORMAL | Completada |
| `WorkflowExecutionFailed` | `workflow:executor` | `{execution_id, workflow_id, error, failed_node, duration_ms}` | HIGH | Falhou |
| `WorkflowExecutionPaused` | `workflow:executor` | `{execution_id, workflow_id, reason}` | NORMAL | Pausada |
| `WorkflowExecutionResumed` | `workflow:executor` | `{execution_id, workflow_id}` | NORMAL | Retomada |
| `WorkflowExecutionCancelled` | `workflow:executor` | `{execution_id, workflow_id, reason}` | HIGH | Cancelada |
| `WorkflowNodeStarted` | `workflow:executor` | `{execution_id, node_id, node_type, input:{}}` | LOW | Nó iniciado |
| `WorkflowNodeCompleted` | `workflow:executor` | `{execution_id, node_id, output:{}, duration_ms}` | LOW | Nó completado |
| `WorkflowNodeFailed` | `workflow:executor` | `{execution_id, node_id, error, duration_ms}` | HIGH | Nó falhou |
| `WorkflowNodeSkipped` | `workflow:executor` | `{execution_id, node_id, reason}` | LOW | Nó pulado |
| `WorkflowEdgeTraversed` | `workflow:executor` | `{execution_id, from_node, to_node, condition_result}` | LOW | Edge percorrida |

### Scheduler
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `JobScheduled` | `scheduler` | `{job_id, name, schedule, next_run_at}` | NORMAL | Job agendado |
| `JobTriggered` | `scheduler` | `{job_id, execution_id, trigger_type}` | NORMAL | Job disparado |
| `JobCompleted` | `scheduler` | `{job_id, execution_id, result:{}, duration_ms}` | NORMAL | Completado |
| `JobFailed` | `scheduler` | `{job_id, execution_id, error, duration_ms}` | HIGH | Falhou |
| `JobMissed` | `scheduler` | `{job_id, scheduled_at, reason}` | HIGH | Perdido (atrasado) |
| `JobPaused` | `scheduler` | `{job_id, reason}` | NORMAL | Pausado |
| `JobResumed` | `scheduler` | `{job_id}` | NORMAL | Retomado |

### Queue
| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `QueueCreated` | `queue:manager` | `{queue_id, name, type, config:{}}` | NORMAL | Fila criada |
| `QueueDeleted` | `queue:manager` | `{queue_id}` | HIGH | Fila deletada |
| `MessageEnqueued` | `queue:{id}` | `{queue_id, message_id, priority, size}` | LOW | Mensagem enfileirada |
| `MessageDequeued` | `queue:{id}` | `{queue_id, message_id, consumer_id}` | LOW | Desenfileirada |
| `MessageProcessed` | `queue:{id}` | `{queue_id, message_id, consumer_id, duration_ms}` | LOW | Processada |
| `MessageFailed` | `queue:{id}` | `{queue_id, message_id, consumer_id, error}` | HIGH | Falhou processamento |
| `MessageDeadLettered` | `queue:{id}` | `{queue_id, message_id, reason, retry_count}` | HIGH | DLQ |
| `QueueBackpressure` | `queue:{id}` | `{queue_id, current_size, max_size, action}` | HIGH | Backpressure |
| `QueuePaused` | `queue:{id}` | `{queue_id, reason}` | NORMAL | Pausada |
| `QueueResumed` | `queue:{id}` | `{queue_id}` | NORMAL | Retomada |

---

## 🧠 CAMADA 8: MEMORY / RAG / EMBEDDING (15 events)

| Event Type | Source | Payload | Priority | Descrição |
|------------|--------|---------|----------|-----------|
| `MemoryStored` | `memory:{type}` | `{memory_id, type, content_hash, tags:[]}` | LOW | Armazenado |
| `MemoryRetrieved` | `memory:{type}` | `{memory_id, type, query, score}` | LOW | Recuperado |
| `MemoryDeleted` | `memory:{type}` | `{memory_id, type}` | NORMAL | Deletado |
| `MemoryCleared` | `memory:{type}` | `{type, filter:{}, count}` | HIGH | Limpado |
| `MemoryConsolidated` | `memory:{type}` | `{type, count, duration_ms}` | NORMAL | Consolidado |
| `EmbeddingGenerated` | `embedding:provider` | `{provider_id, model, input_tokens, output_dim, duration_ms}` | LOW | Embedding gerado |
| `EmbeddingBatchGenerated` | `embedding:provider` | `{provider_id, model, batch_size, duration_ms}` | NORMAL | Batch embedding |
| `RAGIndexed` | `rag:engine` | `{index_id, documents:count, duration_ms}` | NORMAL | Indexado RAG |
| `RAGQueryExecuted` | `rag:engine` | `{index_id, query, results:count, duration_ms}` | LOW | Query RAG |
| `RAGIndexUpdated` | `rag:engine` | `{index_id, upserts, deletes, duration_ms}` | NORMAL | Index atualizado |

---

## 🎙️ CAMADA 9: VOICE / VISION / VIDEO / IMAGE (22 events)

### Voice
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `VoiceSessionStarted` | `voice:{provider}` | `{session_id, voice_id, language, format}` | NORMAL |
| `VoiceSegmentGenerated` | `voice:{provider}` | `{session_id, segment_id, audio_base64, duration_ms}` | LOW |
| `VoiceSessionCompleted` | `voice:{provider}` | `{session_id, total_duration_ms, segments}` | NORMAL |
| `VoiceTranscriptionStarted` | `voice:{provider}` | `{session_id, audio_format, language}` | NORMAL |
| `VoiceTranscriptionCompleted` | `voice:{provider}` | `{session_id, text, confidence, duration_ms}` | NORMAL |
| `VoiceCloneStarted | `vision:{provider}` | `{request_id, operation, image_hash}` | LOW |
| `VisionAnalysisCompleted` | `vision:{provider}` | `{request_id, operation, result:{}, duration_ms}` | NORMAL |
| `VisionAnalysisFailed` | `vision:{provider}` | `{request_id, operation, error}` | HIGH |

### Video
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `VideoGenerationStarted` | `video:{provider}` | `{request_id, prompt, duration_seconds, style}` | NORMAL |
| `VideoGenerationProgress` | `video:{provider}` | `{request_id, progress_pct, frame_preview}` | LOW |
| `VideoGenerationCompleted` | `video:{provider}` | `{request_id, video_url, duration_ms}` | NORMAL |
| `VideoGenerationFailed` | `video:{provider}` | `{request_id, error}` | HIGH |

### Image
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `ImageGenerationStarted` | `image:{provider}` | `{request_id, prompt, size, model}` | NORMAL |
| `ImageGenerationCompleted` | `image:{provider}` | `{request_id, images:[{url, revised_prompt}], duration_ms}` | NORMAL |
| `ImageEditStarted` | `image:{provider}` | `{request_id, operation, image_url, mask_url}` | NORMAL |
| `ImageEditCompleted` | `image:{provider}` | `{request_id, image_url, duration_ms}` | NORMAL |
| `ImageVariationStarted` | `image:{provider}` | `{request_id, image_url, n_variations}` | NORMAL |
| `ImageVariationCompleted` | `image:{provider}` | `{request_id, images:[], duration_ms}` | NORMAL |

---

## 🛠️ CAMADA 10: CAPABILITIES - BROWSER / EXECUTION / FS / NETWORK / DOCKER / MCP (25 events)

### Browser
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `BrowserSessionCreated` | `browser` | `{session_id, url, config:{}}` | NORMAL |
| `BrowserNavigated` | `browser:{session_id}` | `{session_id, url, load_time_ms}` | LOW |
| `BrowserActionExecuted` | `browser:{session_id}` | `{session_id, action, params:{}, result:{}}` | LOW |
| `BrowserScreenshotTaken` | `browser:{session_id}` | `{session_id, full_page, size_bytes}` | LOW |
| `BrowserElementInspected` | `browser:{session_id}` | `{session_id, selector, element_data:{}}` | LOW |
| `BrowserConsoleLog` | `browser:{session_id}` | `{session_id, level, message, timestamp}` | LOW |
| `BrowserSessionClosed` | `browser` | `{session_id, duration_ms, reason}` | NORMAL |

### Execution (Python/Sandbox)
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `PythonExecutionStarted` | `execution:sandbox` | `{execution_id, sandbox_id, packages:[]}` | NORMAL |
| `PythonExecutionCompleted` | `execution:sandbox` | `{execution_id, output, duration_ms, artifacts:[]}` | NORMAL |
| `PythonExecutionFailed` | `execution:sandbox` | `{execution_id, error, traceback, duration_ms}` | HIGH |
| `SandboxCreated` | `execution:sandbox` | `{sandbox_id, type, config:{}}` | NORMAL |
| `SandboxDestroyed` | `execution:sandbox` | `{sandbox_id, reason}` | NORMAL |

### FileSystem
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `FileRead` | `filesystem` | `{path, size_bytes, encoding}` | LOW |
| `FileWritten` | `filesystem` | `{path, size_bytes, encoding, created_dirs}` | LOW |
| `FileDeleted` | `filesystem` | `{path}` | NORMAL |
| `DirectoryListed` | `filesystem` | `{path, recursive, count, duration_ms}` | LOW |

### Network
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `HttpRequest` | `network:http` | `{request_id, method, url, status_code, duration_ms}` | LOW |
| `HttpRequestFailed` | `network:http` | `{request_id, method, url, error, duration_ms}` | NORMAL |
| `FileDownloaded` | `network:http` | `{request_id, url, path, size_bytes}` | NORMAL |

### Docker
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `ContainerCreated` | `docker` | `{container_id, image, config:{}}` | NORMAL |
| `ContainerStarted` | `docker:{container_id}` | `{container_id, duration_ms}` | NORMAL |
| `ContainerStopped` | `docker:{container_id}` | `{container_id, exit_code, duration_ms}` | NORMAL |
| `ContainerLogs` | `docker:{container_id}` | `{container_id, stream, content}` | LOW |
| `ContainerRemoved` | `docker` | `{container_id, force}` | NORMAL |

### MCP
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `MCPServerConnected` | `mcp:{server_id}` | `{server_id, transport, tools_count}` | NORMAL |
| `MCPServerDisconnected` | `mcp:{server_id}` | `{server_id, reason}` | HIGH |
| `MCPToolCalled` | `mcp:{server_id}` | `{server_id, tool_name, args:{}, result:{}, duration_ms}` | LOW |

---

## 💬 CAMADA 11: CONVERSATION / NOTIFICATION (18 events)

### Conversation
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `ConversationCreated` | `conversation` | `{conversation_id, title, participants:[]}` | NORMAL |
| `ConversationUpdated` | `conversation` | `{conversation_id, changes:{}}` | NORMAL |
| `ConversationDeleted` | `conversation` | `{conversation_id}` | HIGH |
| `ConversationArchived` | `conversation` | `{conversation_id}` | NORMAL |
| `MessageAdded` | `conversation:{id}` | `{conversation_id, message_id, role, content, type}` | LOW |
| `MessageUpdated` | `conversation:{id}` | `{conversation_id, message_id, changes:{}}` | LOW |
| `MessageDeleted` | `conversation:{id}` | `{conversation_id, message_id}` | NORMAL |
| `ConversationStreamingStarted` | `conversation:{id}` | `{conversation_id, message_id, model}` | NORMAL |
| `ConversationStreamingChunk` | `conversation:{id}` | `{conversation_id, message_id, delta, done}` | LOW |
| `ConversationStreamingCompleted` | `conversation:{id}` | `{conversation_id, message_id, usage:{}}` | NORMAL |

### Notification
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `NotificationSent` | `notification` | `{notification_id, channel, recipients:[], template_id}` | LOW |
| `NotificationDelivered` | `notification` | `{notification_id, channel, recipient, delivered_at}` | LOW |
| `NotificationFailed` | `notification` | `{notification_id, channel, recipient, error}` | HIGH |
| `NotificationOpened` | `notification` | `{notification_id, channel, recipient, opened_at}` | LOW |
| `NotificationClicked` | `notification` | `{notification_id, channel, recipient, url, clicked_at}` | LOW |

---

## 📦 CAMADA 12: STORAGE / AUTH / WORKSPACE INFRA (12 events)

### Storage
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `BlobUploaded` | `storage:{backend}` | `{blob_id, bucket, path, size_bytes, content_type}` | LOW |
| `BlobDownloaded` | `storage:{backend}` | `{blob_id, bucket, path, size_bytes}` | LOW |
| `BlobDeleted` | `storage:{backend}` | `{blob_id, bucket, path}` | NORMAL |
| `BlobListed` | `storage:{backend}` | `{bucket, prefix, count, duration_ms}` | LOW |

### Auth
| Event Type | Source | Payload | Priority |
|------------|--------|---------|----------|
| `UserAuthenticated` | `auth:{provider}` | `{user_id, provider, method, session_id}` | NORMAL |
| `UserLoginFailed` | `auth:{provider}` | `{user_id, provider, error, ip}` | HIGH |
| `UserLoggedOut` | `auth:{provider}` | `{user_id, provider, session_id}` | NORMAL |
| `TokenRefreshed` | `auth:{provider}` | `{user_id, provider, new_expires_at}` | LOW |
| `PermissionGranted` | `auth:core` | `{user_id, permission, resource, granted_by}` | NORMAL |
| `PermissionRevoked` | `auth:core` | `{user_id, permission, resource, revoked_by}` | HIGH |

---

## 📊 RESUMO ESTATÍSTICO

| Camada | Event Types | Prioridade Média |
|--------|-------------|------------------|
| Core Runtime | 37 | HIGH |
| Agent/Employee | 35 | NORMAL |
| Team/Workspace | 28 | NORMAL |
| Skill Registry | 22 | NORMAL |
| Provider Registry | 30 | HIGH |
| Plugin System | 18 | HIGH |
| Workflow/Scheduler/Queue | 35 | NORMAL |
| Memory/RAG/Embedding | 15 | LOW |
| Voice/Vision/Video/Image | 22 | NORMAL |
| Capabilities (Browser/Exec/FS/Net/Docker/MCP) | 25 | LOW |
| Conversation/Notification | 18 | LOW |
| Storage/Auth/Workspace Infra | 12 | NORMAL |
| **TOTAL CORE** | **~155** | - |
| **Enterprise Extensions** | **~35** | - |
| **GRAND TOTAL** | **~190** | - |

---

## 🔗 CORRELAÇÃO E CAUSAÇÃO (Correlation/Causation)

### Padrão Obrigatório

```python
# TODO evento DEVE ter:
event = Event(
    event_type="EmployeeTaskCompleted",
    source="agent:employee:john.doe",
    correlation_id="abc-123-def-456",  # UUID - mesmo para toda a chain
    causation_id="xyz-789",             # UUID - event_id do "EmployeeTaskStarted"
    payload={...}
)
```

### Cadeia Típica (Employee executa workflow)

```
1. WorkflowExecutionStarted      (correlation_id=A, causation_id=null)
2.   WorkflowNodeStarted         (correlation_id=A, causation_id=1)
3.     EmployeeTaskStarted       (correlation_id=A, causation_id=2) ← Employee pega task
4.       EmployeeToolCall        (correlation_id=A, causation_id=3)   ← Tool chamada
5.         ToolExecutionCompleted (correlation_id=A, causation_id=4)  ← Tool retorna
6.       EmployeeToolResult      (correlation_id=A, causation_id=5)
7.     EmployeeTaskCompleted     (correlation_id=A, causation_id=6)
8.   WorkflowNodeCompleted       (correlation_id=A, causation_id=7)
9. WorkflowExecutionCompleted    (correlation_id=A, causation_id=8)
```

### Query no Frontend (Timeline)

```typescript
// Buscar toda a cadeia de um correlation_id
const chain = await api.events.getCorrelationChain(correlationId);
// Retorna array ordenado por timestamp

// Filtrar por causation (filhos diretos de um evento)
const children = await api.events.getChildren(causationId);
```

---

## 📡 WEBSOCKET EVENT STREAM

### Conexão
```
ws://localhost:8000/ws/events?token=<jwt>&filters=event_types:sources:tags
```

### Filtros Disponíveis (Query Params)

| Parâmetro | Exemplo | Descrição |
|-----------|---------|-----------|
| `event_types` | `AgentCreated,AgentDeleted` | CSV de event_types |
| `sources` | `agent:employee:,workflow:` | Prefix match (wildcard *) |
| `tags` | `critical,production` | Tags no metadata |
| `priority` | `HIGH,CRITICAL` | Mínima prioridade |
| `tenant_id` | `company:acme` | Multi-tenant filter |
| `correlation_id` | `abc-123` | Single correlation chain |

### Formato da Mensagem

```json
{
  "type": "event",
  "data": {
    "event_type": "EmployeeTaskCompleted",
    "source": "agent:employee:john.doe",
    "timestamp": "2026-07-28T15:30:45.123Z",
    "correlation_id": "abc-123-def-456",
    "causation_id": "xyz-789",
    "payload": { "employee_id": "john.doe", "task_id": "task-1", "output": {...} },
    "metadata": { "tenant_id": "company:acme", "tags": ["production"] },
    "priority": "NORMAL"
  }
}
```

### Heartbeat
```json
{"type": "ping", "timestamp": "2026-07-28T15:30:45.000Z"}
{"type": "pong", "timestamp": "2026-07-28T15:30:45.001Z"}
```

---

## 🛡️ GOVERNANÇA DE EVENTOS

### Regras Obrigatórias

| Regra | Descrição |
|-------|-----------|
| **Unique Event Types** | `event_type` deve ser único globalmente. Prefix com domínio: `EmployeeCreated`, não `Created` |
| **Correlation Required** | Todo evento DEVE ter `correlation_id` (auto-gerado se não fornecido) |
| **Causation Chain** | Eventos causados por outros DEVEM ter `causation_id` = event_id do pai |
| **Payload Schema** | Payload deve ser JSON-serializable. Evite objetos complexos. Use IDs. |
| **PII Protection** | Nunca log PII no payload. Use `user_id`, não email/nome. |
| **Priority Accuracy** | Use `CRITICAL` apenas para falhas que exigem alerta imediato (pager duty) |
| **Source Format** | `{domain}:{module}:{instance_id}` ex: `agent:employee:john.doe` |
| **Versioning** | Novos campos em payload = backward compatible. Remover campos = breaking (novo event_type v2) |

### Event Type Versioning

```
EmployeeCreated          → v1 (original)
EmployeeCreated_v2       → breaking change (campo removido/renomeado)
EmployeeProfileUpdated   → novo evento para mudanças parciais
```

---

## 📝 COMO ADICIONAR NOVO EVENT TYPE

### 1. Defina no `runtime/events/__init__.py`

```python
class EventType(Enum):
    # ... existentes ...
    
    # NOVO - Minha Feature
    MYFEATURE_ACTION = "MyFeatureAction"
    MYFEATURE_ACTION_FAILED = "MyFeatureActionFailed"
```

### 2. Crie Helper Function (opcional)

```python
def create_myfeature_event(source: str, action: str, payload: Dict, **kwargs) -> Event:
    return create_event(
        EventType.MYFEATURE_ACTION,
        source,
        payload={"action": action, **payload},
        **kwargs
    )
```

### 3. Documente NESTE ARQUIVO (ENGINE_EVENTS.md)

Adicione na tabela apropriada com: Event Type, Source, Payload, Priority, Descrição.

### 4. Adicione Testes

```python
# tests/events/test_myfeature_events.py
async def test_myfeature_event_emitted():
    event_bus = get_event_bus()
    events = []
    event_bus.subscribe_all(event_handler(lambda e: events.append(e)))
    
    await my_feature.do_action()
    
    assert any(e.event_type == "MyFeatureAction" for e in events)
```

---

## 🔍 DEBUGGING E OBSERVABILIDADE

### CLI Commands

```bash
# Ver eventos recentes
aipensa-engine events list --limit 50 --type EmployeeTaskCompleted

# Seguir stream em tempo real
aipensa-engine events tail --filter source:agent:employee:*

# Buscar correlation chain
aipensa-engine events chain abc-123-def-456

# Dead letter queue
aipensa-engine events dead-letter --limit 20
```

### Structured Logging (JSON)

```json
{
  "timestamp": "2026-07-28T15:30:45.123Z",
  "level": "INFO",
  "logger": "eventbus",
  "event_type": "EmployeeTaskCompleted",
  "correlation_id": "abc-123-def-456",
  "causation_id": "xyz-789",
  "source": "agent:employee:john.doe",
  "duration_ms": 1250,
  "message": "Event published"
}
```

### Prometheus Metrics

| Metric | Type | Labels | Descrição |
|--------|------|--------|-----------|
| `engine_events_published_total` | Counter | `event_type, source, priority` | Total publicado |
| `engine_events_processed_total` | Counter | `event_type, handler, status` | Processados (success/error) |
| `engine_event_processing_duration_seconds` | Histogram | `event_type, handler` | Latência handler |
| `engine_event_queue_size` | Gauge | - | Tamanho fila background |
| `engine_dead_letter_size` | Gauge | - | Tamanho DLQ |

---

**ESTE DOCUMENTO É A REFERÊNCIA CANÔNICA DE TODOS OS EVENTOS. QUALQUER NOVO EVENTO DEVE SER ADICIONADO AQUI ANTES DE SER IMPLEMENTADO.**