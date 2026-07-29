# 🔌 ENGINE_PLUGIN_GUIDE.md - Guia de Extensão da AIPENSA Engine

**Versão:** 1.0  
**Base:** ENGINE_SPEC.md + ENGINE_ARCHITECTURE.md + ENGINE_API_CONTRACT.md  
**Data:** 28 Julho 2026  
**Status:** Guia Oficial - Obrigatório para todos desenvolvedores de plugins  

---

## 🏛️ FILOSOFIA DO PLUGIN SYSTEM

> **"A Engine é o Kernel. Plugins são os Drivers."**

O **Plugin System** da AIPENSA Engine permite estender **TODA** capacidade da Engine **sem alterar o Core**. Qualquer nova funcionalidade técnica (LLM, Storage, Auth, Browser, Tool, etc) DEVE ser implementada como Plugin.

### Princípios

| Princípio | Regra |
|-----------|-------|
| **Zero Core Changes** | Adicionar LLM provider? Plugin. Novo storage backend? Plugin. Nova tool? Plugin. |
| **Auto-Discovery** | Plugins em `runtime/plugins/<type>/<name>/` são carregados automaticamente no startup |
| **Isolamento** | Plugins têm config/state próprios. Falha em um não derruba a Engine. |
| **Versionamento** | Cada plugin tem SemVer próprio. Engine valida compatibilidade na carga. |
| **Hot-Reload (Dev)** | `PluginManager.reload(plugin_id)` suportado em desenvolvimento |
| **Contrato Explícito** | `plugin.yaml` manifesto obrigatório com schema de config, capabilities, deps |
| **Observabilidade Nativa** | Plugins herdam logging, métricas, tracing, event emission da Engine |

---

## 📁 ESTRUTURA DE DIRETÓRIOS

```
runtime/plugins/
├── tool/                    # Tools chamáveis por Agents/LLM
│   ├── web_search/
│   │   ├── plugin.yaml
│   │   ├── web_search.py
│   │   ├── __init__.py
│   │   └── tests/
│   └── calculator/
│       ├── plugin.yaml
│       └── ...
├── llm/                     # LLM Providers
│   ├── nvidia_nim/
│   │   ├── plugin.yaml
│   │   ├── nvidia_backend.py
│   │   └── ...
│   ├── openai/
│   └── anthropic/
├── memory/                  # Memory Backends
│   ├── redis/
│   ├── pgvector/
│   ├── qdrant/
│   └── chroma/
├── storage/                 # Blob/KV Storage
│   ├── s3/
│   ├── gcs/
│   ├── minio/
│   └── filesystem/
├── auth/                    # Auth Providers
│   ├── oauth2/
│   ├── saml/
│   ├── oidc/
│   └── api_key/
├── browser/                 # Browser Engines
│   ├── playwright/
│   ├── selenium/
│   └── chrome_cdp/
├── sandbox/                 # Code Execution
│   ├── docker/
│   ├── gvisor/
│   ├── firecracker/
│   └── subprocess/
├── network/                 # HTTP Clients
│   ├── httpx/
│   ├── aiohttp/
│   └── curl/
├── mcp/                     # MCP Servers
│   ├── filesystem/
│   ├── github/
│   └── postgres/
├── runtime/                 # Runtime Modules (novos módulos core)
│   ├── custom_orchestrator/
│   └── ...
└── custom/                  # Extensibilidade livre
    ├── my_company_integration/
    └── ...
```

---

## 📄 MANIFESTO DO PLUGIN (`plugin.yaml`)

### Schema Obrigatório

```yaml
# plugin.yaml - Manifesto obrigatório para TODOS plugins
name: "web_search"                    # Único, snake_case, max 64 chars
version: "1.2.0"                      # SemVer obrigatório
type: "tool"                          # Um dos 11 PluginType (obrigatório)
class_name: "WebSearchPlugin"         # Classe principal (obrigatório)
entry_point: "web_search.py"          # Arquivo com a classe (relativo à raiz do plugin)
description: "Busca web via SerpAPI, Bing, Google Custom Search"
author: "aipensa"
license: "MIT"
homepage: "https://github.com/aipensa/plugins/web_search"
repository: "https://github.com/aipensa/plugins"
tags: ["search", "web", "serpapi", "bing"]

# Dependências de outros plugins/modules
dependencies:
  - "network:httpx"           # plugin_type:plugin_name
  - "runtime:conversation"    # módulo runtime builtin
  - "skill:llm_generation"    # skill requerida

# Capabilities que este plugin provê
capabilities:
  - "web_search"
  - "news_search"
  - "academic_search"

# Schema de configuração (JSON Schema Draft 2020-12)
config_schema:
  type: "object"
  properties:
    default_engine:
      type: "string"
      enum: ["serpapi", "bing", "google"]
      default: "serpapi"
    engines:
      type: "object"
      properties:
        serpapi:
          type: "object"
          properties:
            api_key:
              type: "string"
              format: "password"
              description: "SerpAPI Key"
          required: ["api_key"]
        bing:
          type: "object"
          properties:
            api_key:
              type: "string"
              format: "password"
            endpoint:
              type: "string"
              format: "uri"
          required: ["api_key", "endpoint"]
        google:
          type: "object"
          properties:
            api_key:
              type: "string"
              format: "password"
            cx:
              type: "string"
              description: "Custom Search Engine ID"
          required: ["api_key", "cx"]
    timeout_seconds:
      type: "integer"
      minimum: 5
      maximum: 60
      default: 30
    max_results:
      type: "integer"
      minimum: 1
      maximum: 100
      default: 10
  required: ["default_engine", "engines"]

# Permissões necessárias para usar este plugin
permissions_required:
  - "plugin.use:web_search"
  - "provider.use:serpapi"

# Rate limits globais do plugin
rate_limits:
  requests_per_minute: 60
  tokens_per_minute: 10000

# Health check endpoint
health_check:
  enabled: true
  interval_seconds: 60
  timeout_seconds: 10

# Metadados de marketplace (opcional)
marketplace:
  category: "search"
  pricing: "free"
  verified: true
  downloads: 15420
  rating: 4.8
```

---

## 🔧 TIPOS DE PLUGIN E IMPLEMENTAÇÃO

### 1. TOOL PLUGINS (Functions para Agents/LLM)

```python
# runtime/plugins/tool/web_search/web_search.py
from runtime.plugins.base import ToolPlugin, ToolResult, ToolContext
from runtime.plugins.decorators import tool

class WebSearchPlugin(ToolPlugin):
    """Plugin de busca web multi-engine."""
    
    name = "web_search"
    version = "1.2.0"
    
    def __init__(self, config: Dict, runtime: "Runtime"):
        super().__init__(config, runtime)
        self.engines = self._initialize_engines(config["engines"])
        self.default_engine = config["default_engine"]
        self.timeout = config.get("timeout_seconds", 30)
        self.max_results = config.get("max_results", 10)
        
    def _initialize_engines(self, engines_config: Dict) -> Dict[str, SearchEngine]:
        engines = {}
        for name, cfg in engines_config.items():
            if name == "serpapi":
                engines[name] = SerpAPIEngine(cfg["api_key"])
            elif name == "bing":
                engines[name] = BingEngine(cfg["api_key"], cfg["endpoint"])
            elif name == "google":
                engines[name] = GoogleCustomSearchEngine(cfg["api_key"], cfg["cx"])
        return engines
    
    @tool(
        name="web_search",
        description="Busca na web usando múltiplos engines",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query de busca"},
                "engine": {"type": "string", "enum": ["serpapi", "bing", "google"], "description": "Engine específico (opcional)"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "recency_days": {"type": "integer", "description": "Filtrar por dias recentes"}
            },
            "required": ["query"]
        }
    )
    async def web_search(self, ctx: ToolContext, query: str, 
                        engine: str = None, max_results: int = None,
                        recency_days: int = None) -> ToolResult:
        """Executa busca web."""
        engine = engine or self.default_engine
        search_engine = self.engines.get(engine)
        
        if not search_engine:
            return ToolResult.error(f"Engine '{engine}' não configurado")
            
        try:
            results = await search_engine.search(
                query=query,
                max_results=max_results or self.max_results,
                recency_days=recency_days
            )
            
            # Emit event para observabilidade
            await self.emit_event(ToolExecuted(
                tool_name="web_search",
                engine=engine,
                query=query,
                results_count=len(results),
                correlation_id=ctx.correlation_id
            ))
            
            return ToolResult.success(
                data={"results": results, "engine": engine, "query": query},
                metadata={"tokens_used": sum(len(r.get("snippet", "")) for r in results)}
            )
        except Exception as e:
            await self.emit_event(ToolFailed(
                tool_name="web_search",
                engine=engine,
                error=str(e),
                correlation_id=ctx.correlation_id
            ))
            return ToolResult.error(f"Search failed: {e}")
    
    @tool(
        name="news_search",
        description="Busca notícias recentes",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "days_back": {"type": "integer", "default": 7}
            },
            "required": ["query"]
        }
    )
    async def news_search(self, ctx: ToolContext, query: str, days_back: int = 7) -> ToolResult:
        return await self.web_search(ctx, query, recency_days=days_back)
```

### 2. LLM PLUGINS (Providers de Modelos)

```python
# runtime/plugins/llm/openai/openai_backend.py
from runtime.plugins.base import LLMPlugin, LLMRequest, LLMResponse, LLMStreamChunk
from runtime.llm.base import ModelConfig, ModelBackend

class OpenAIPlugin(LLMPlugin):
    """OpenAI/GPT Provider Plugin."""
    
    name = "openai"
    version = "2.1.0"
    provider_id = "openai"
    
    SUPPORTED_MODELS = [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
        "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
    ]
    
    def __init__(self, config: Dict, runtime: "Runtime"):
        super().__init__(config, runtime)
        self.api_key = config.get("api_key") or self.get_secret("openai_api_key")
        self.organization = config.get("organization")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            organization=self.organization,
            base_url=self.base_url
        )
        
    def get_supported_models(self) -> List[ModelConfig]:
        return [
            ModelConfig(
                model_id=model,
                provider="openai",
                capabilities=["chat", "completion", "function_calling", "vision"],
                context_window=128000 if "4o" in model else 16384,
                max_output_tokens=4096,
                cost_per_1k_input=self._get_cost(model, "input"),
                cost_per_1k_output=self._get_cost(model, "output")
            )
            for model in self.SUPPORTED_MODELS
        ]
    
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Chat completion com function calling."""
        messages = self._convert_messages(request.messages)
        tools = self._convert_tools(request.tools) if request.tools else None
        
        response = await self.client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=tools,
            tool_choice=request.tool_choice,
            stream=False
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            tool_calls=self._convert_tool_calls(response.choices[0].message.tool_calls),
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            model=response.model,
            finish_reason=response.choices[0].finish_reason
        )
    
    async def chat_completion_stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        """Streaming chat completion."""
        stream = await self.client.chat.completions.create(
            model=request.model,
            messages=self._convert_messages(request.messages),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=self._convert_tools(request.tools) if request.tools else None,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield LLMStreamChunk(
                    content=chunk.choices[0].delta.content,
                    finish_reason=None
                )
            if chunk.choices[0].delta.tool_calls:
                yield LLMStreamChunk(
                    tool_calls=self._convert_streaming_tool_calls(chunk.choices[0].delta.tool_calls)
                )
            if chunk.choices[0].finish_reason:
                yield LLMStreamChunk(
                    content="",
                    finish_reason=chunk.choices[0].finish_reason
                )
    
    async def health_check(self) -> PluginHealth:
        """Verifica conectividade com OpenAI."""
        try:
            await self.client.models.list()
            return PluginHealth(status="healthy", latency_ms=50)
        except Exception as e:
            return PluginHealth(status="unhealthy", error=str(e))
```

### 3. MEMORY PLUGINS (Backends de Armazenamento)

```python
# runtime/plugins/memory/pgvector/pgvector_store.py
from runtime.plugins.base import MemoryPlugin, VectorStore, MemoryStore
from runtime.memory.base import VectorSearchResult, MemoryStats

class PgVectorPlugin(MemoryPlugin):
    """PostgreSQL + pgvector backend para memory."""
    
    name = "pgvector"
    version = "1.0.0"
    store_type = "vector"  # ou "kv", "document", "timeseries", "graph"
    
    def __init__(self, config: Dict, runtime: "Runtime"):
        super().__init__(config, runtime)
        self.dsn = config.get("dsn") or self.get_secret("pgvector_dsn")
        self.pool: Optional[asyncpg.Pool] = None
        self.vector_dimensions = config.get("dimensions", 1536)
        
    async def initialize(self) -> None:
        self.pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
        # Criar tabelas se não existem
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
                CREATE TABLE IF NOT EXISTS memory_vectors (
                    store_name TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value JSONB NOT NULL,
                    embedding VECTOR($1) NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    expires_at TIMESTAMPTZ,
                    PRIMARY KEY (store_name, key)
                );
                CREATE INDEX IF NOT EXISTS idx_memory_vectors_embedding 
                ON memory_vectors USING ivfflat (embedding vector_cosine_ops);
            """, self.vector_dimensions)
    
    async def write(self, store: str, key: str, value: Any, 
                   ttl: int = None, metadata: Dict = None,
                   embedding: List[float] = None) -> WriteResult:
        if embedding is None and isinstance(value, str):
            # Auto-embed se string
            embedding = await self.runtime.get_module("embedding").embed(value)
            
        expires_at = None
        if ttl:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO memory_vectors (store_name, key, value, embedding, metadata, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (store_name, key) DO UPDATE SET
                    value = EXCLUDED.value,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    expires_at = EXCLUDED.expires_at
            """, store, key, json.dumps(value), embedding, json.dumps(metadata or {}), expires_at)
            
        return WriteResult(success=True, key=key, store=store)
    
    async def vector_search(self, store: str, vector: List[float], 
                          top_k: int = 10, filter: Dict = None) -> List[VectorSearchResult]:
        where_clause = "store_name = $1"
        params = [store, vector, top_k]
        
        if filter:
            for k, v in filter.items():
                where_clause += f" AND metadata->>'{k}' = ${len(params)+1}"
                params.append(str(v))
                
        query = f"""
            SELECT key, value, metadata, 
                   1 - (embedding <=> $2) as similarity
            FROM memory_vectors
            WHERE {where_clause}
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY embedding <=> $2
            LIMIT $3
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
        return [
            VectorSearchResult(
                key=row["key"],
                value=json.loads(row["value"]),
                metadata=json.loads(row["metadata"]),
                score=row["similarity"]
            )
            for row in rows
        ]
```

### 4. STORAGE PLUGINS (Blob/KV)

```python
# runtime/plugins/storage/s3/s3_storage.py
from runtime.plugins.base import StoragePlugin, BlobStore, KVStore
from runtime.storage.base import BlobMetadata, PutResult, GetResult

class S3Plugin(StoragePlugin):
    """AWS S3 / MinIO / S3-compatible Storage."""
    
    name = "s3"
    version = "1.3.0"
    store_types = ["blob", "kv"]
    
    def __init__(self, config: Dict, runtime: "Runtime"):
        super().__init__(config, runtime)
        self.client = boto3.client(
            "s3",
            endpoint_url=config.get("endpoint_url"),  # Para MinIO
            aws_access_key_id=config.get("access_key") or self.get_secret("s3_access_key"),
            aws_secret_access_key=config.get("secret_key") or self.get_secret("s3_secret_key"),
            region_name=config.get("region", "us-east-1")
        )
        self.default_bucket = config.get("default_bucket", "aipensa-engine")
        
    async def put_blob(self, bucket: str, key: str, data: bytes,
                      metadata: BlobMetadata = None) -> PutResult:
        bucket = bucket or self.default_bucket
        extra_args = {}
        if metadata:
            extra_args["Metadata"] = metadata.custom_metadata
            if metadata.content_type:
                extra_args["ContentType"] = metadata.content_type
                
        self.client.put_object(Bucket=bucket, Key=key, Body=data, **extra_args)
        
        return PutResult(
            bucket=bucket,
            key=key,
            size=len(data),
            etag=response["ETag"].strip('"')
        )
    
    async def get_blob(self, bucket: str, key: str) -> GetResult:
        bucket = bucket or self.default_bucket
        response = self.client.get_object(Bucket=bucket, Key=key)
        return GetResult(
            data=response["Body"].read(),
            metadata=BlobMetadata(
                content_type=response.get("ContentType"),
                size=response["ContentLength"],
                etag=response["ETag"].strip('"'),
                last_modified=response["LastModified"],
                custom_metadata=response.get("Metadata", {})
            )
        )
    
    async def list_blobs(self, bucket: str, prefix: str = "", 
                        max_keys: int = 1000) -> List[BlobMetadata]:
        bucket = bucket or self.default_bucket
        paginator = self.client.get_paginator("list_objects_v2")
        results = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, MaxKeys=max_keys):
            for obj in page.get("Contents", []):
                results.append(BlobMetadata(
                    key=obj["Key"],
                    size=obj["Size"],
                    etag=obj["ETag"].strip('"'),
                    last_modified=obj["LastModified"]
                ))
        return results
```

### 5. PROVIDER PLUGINS (Integrações Externas)

```python
# runtime/plugins/provider/meta/meta_provider.py
from runtime.plugins.base import ProviderPlugin, ProviderConnection, ProviderCapability
from runtime.provider.base import ProviderAction, ProviderResult

class MetaProviderPlugin(ProviderPlugin):
    """Meta (Facebook/Instagram/WhatsApp) Graph API Provider."""
    
    name = "meta"
    version = "2.1.0"
    provider_id = "meta"
    provider_type = ProviderType.SOCIAL
    
    CAPABILITIES = [
        ProviderCapability(
            id="instagram_post",
            name="Instagram Post",
            description="Publica post no Instagram Feed",
            params_schema={...}
        ),
        ProviderCapability(
            id="instagram_story",
            name="Instagram Story",
            description="Publica Story no Instagram",
            params_schema={...}
        ),
        ProviderCapability(
            id="instagram_reel",
            name="Instagram Reel",
            description="Publica Reel no Instagram",
            params_schema={...}
        ),
        ProviderCapability(
            id="facebook_post",
            name="Facebook Post",
            description="Publica post no Facebook Page",
            params_schema={...}
        ),
        ProviderCapability(
            id="whatsapp_message",
            name="WhatsApp Message",
            description="Envia mensagem WhatsApp Business",
            params_schema={...}
        ),
        ProviderCapability(
            id="whatsapp_template",
            name="WhatsApp Template",
            description="Envia template WhatsApp aprovado",
            params_schema={...}
        ),
    ]
    
    OAUTH_CONFIG = {
        "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scopes": [
            "instagram_basic", "instagram_content_publish",
            "pages_show_list", "pages_read_engagement",
            "whatsapp_business_management", "whatsapp_business_messaging"
        ]
    }
    
    def __init__(self, config: Dict, runtime: "Runtime"):
        super().__init__(config, runtime)
        self.api_version = config.get("api_version", "v18.0")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
    async def execute(self, connection: ProviderConnection, 
                     capability: str, params: Dict) -> ProviderResult:
        """Executa ação no provider."""
        access_token = decrypt(connection.credentials["access_token"])
        
        client = MetaGraphAPIClient(access_token, self.base_url)
        
        if capability == "instagram_post":
            return await client.post_to_instagram(
                instagram_id=connection.credentials["instagram_business_id"],
                image_url=params["image_url"],
                caption=params["caption"]
            )
        elif capability == "whatsapp_message":
            return await client.send_whatsapp_message(
                phone_number=params["phone_number"],
                message=params["message"],
                messaging_product="whatsapp"
            )
        # ... outras capabilities
        
    async def refresh_token(self, connection: ProviderConnection) -> ProviderConnection:
        """Refresh OAuth token usando refresh_token."""
        refresh_token = decrypt(connection.credentials["refresh_token"])
        app_id = self.config["app_id"]
        app_secret = self.config["app_secret"]
        
        new_tokens = await self._oauth_refresh(refresh_token, app_id, app_secret)
        
        connection.credentials = encrypt({
            **connection.credentials,
            "access_token": new_tokens["access_token"],
            "refresh_token": new_tokens.get("refresh_token", refresh_token),
            "expires_at": (datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"])).isoformat()
        })
        
        return connection
    
    def validate_credentials(self, credentials: Dict) -> bool:
        """Valida credenciais antes de conectar."""
        required = ["access_token"]
        if credentials.get("oauth"):
            required = []  # OAuth flow handles it
        return all(k in credentials for k in required)
```

### 6. WORKFLOW NODE PLUGINS (Custom Step Types)

```python
# runtime/plugins/runtime/custom_nodes/sentiment_analysis.py
from runtime.workflow.base import WorkflowNodePlugin, WorkflowNode, NodeExecutionContext, NodeResult

class SentimentAnalysisNode(WorkflowNodePlugin):
    """Custom Workflow Node para análise de sentimento."""
    
    name = "sentiment_analysis"
    version = "1.0.0"
    node_type = "sentiment_analysis"  # Novo StepType
    
    # Schema de configuração do node no workflow
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "text_input": {"type": "string", "description": "Texto ou variável {{context.text}}"},
            "model": {"type": "string", "default": "meta/llama-3.1-8b-instruct"},
            "output_variable": {"type": "string", "default": "sentiment"},
            "threshold": {"type": "number", "default": 0.5}
        },
        "required": ["text_input"]
    }
    
    async def execute(self, node: WorkflowNode, context: NodeExecutionContext) -> NodeResult:
        config = node.config
        
        # Resolve input (pode ser template)
        text = self._resolve_template(config["text_input"], context.variables)
        
        # Chama LLM Module
        llm = self.runtime.get_module("llm")
        response = await llm.chat_completion(LLMRequest(
            model=config["model"],
            messages=[{
                "role": "system",
                "content": "Analise o sentimento do texto. Retorne JSON: {\"sentiment\": \"positive|negative|neutral\", \"score\": 0.0-1.0, \"reasoning\": \"...\"}"
            }, {
                "role": "user",
                "content": text
            }],
            temperature=0.1,
            response_format={"type": "json_object"}
        ))
        
        result = json.loads(response.content)
        
        # Armazena no context
        context.variables[config["output_variable"]] = result
        
        # Emite evento
        await self.emit_event(WorkflowNodeExecuted(
            node_id=node.node_id,
            node_type=self.node_type,
            output=result,
            correlation_id=context.correlation_id
        ))
        
        return NodeResult(
            success=True,
            output=result,
            next_nodes=node.get_next_nodes(result["sentiment"])  # Conditional routing
        )
```

### 7. AUTH PLUGINS (Provedores de Autenticação)

```python
# runtime/plugins/auth/oauth2/oauth2_provider.py
from runtime.plugins.base import AuthPlugin, AuthProvider, TokenData, UserInfo

class OAuth2Plugin(AuthPlugin):
    """Generic OAuth 2.0 / OIDC Provider."""
    
    name = "oauth2"
    version = "1.1.0"
    provider_type = AuthProviderType.OAUTH2
    
    def __init__(self, config: Dict, runtime: "Runtime"):
        super().__init__(config, runtime)
        self.providers = config.get("providers", {})
        # Ex: {"google": {...}, "github": {...}, "microsoft": {...}}
        
    async def authenticate(self, provider_name: str, code: str, 
                          redirect_uri: str) -> TokenData:
        """Exchange code for tokens."""
        provider = self.providers[provider_name]
        return await self._oauth_exchange(provider, code, redirect_uri)
        
    async def get_user_info(self, provider_name: str, 
                           access_token: str) -> UserInfo:
        """Get user profile from provider."""
        provider = self.providers[provider_name]
        return await self._fetch_userinfo(provider, access_token)
        
    async def validate_token(self, provider_name: str, 
                            access_token: str) -> bool:
        """Validate token with provider."""
        provider = self.providers[provider_name]
        return await self._introspect_token(provider, access_token)
        
    async def refresh_token(self, provider_name: str, 
                           refresh_token: str) -> TokenData:
        """Refresh expired access token."""
        provider = self.providers[provider_name]
        return await self._oauth_refresh(provider, refresh_token)
```

---

## 🏭 COMO CRIAR UM NOVO PLUGIN (Passo a Passo)

### 1. Escolha o Tipo

| O que você precisa | Tipo de Plugin |
|-------------------|----------------|
| Função chamável por Agent/LLM | `tool` |
| Novo modelo LLM | `llm` |
| Backend de memória/vetor | `memory` |
| Blob storage (S3, GCS) | `storage` |
| Auth (OAuth, SAML, API Key) | `auth` |
| Browser engine | `browser` |
| Code sandbox | `sandbox` |
| HTTP client custom | `network` |
| MCP Server | `mcp` |
| Novo módulo runtime | `runtime` |
| Qualquer outra coisa | `custom` |

### 2. Crie a Estrutura

```bash
# Exemplo: tool plugin
mkdir -p runtime/plugins/tool/meu_plugin
cd runtime/plugins/tool/meu_plugin
```

### 3. Crie o `plugin.yaml`

```yaml
name: "meu_plugin"
version: "1.0.0"
type: "tool"
class_name: "MeuPlugin"
entry_point: "meu_plugin.py"
description: "Descrição do que faz"
author: "seu_nome"
license: "MIT"
dependencies: []
capabilities: ["minha_capability"]
config_schema: {...}
```

### 4. Implemente a Classe

```python
# meu_plugin.py
from runtime.plugins.base import ToolPlugin, ToolResult, ToolContext
from runtime.plugins.decorators import tool

class MeuPlugin(ToolPlugin):
    name = "meu_plugin"
    version = "1.0.0"
    
    def __init__(self, config: Dict, runtime: "Runtime"):
        super().__init__(config, runtime)
        # init code
    
    @tool(name="minha_funcao", description="...", parameters={...})
    async def minha_funcao(self, ctx: ToolContext, param1: str) -> ToolResult:
        # logic
        return ToolResult.success({"result": "ok"})
```

### 5. Registre as Tools (Auto-magic via decorator)

O decorator `@tool` registra automaticamente no `ToolRegistry` da Engine.

### 6. Testes

```python
# tests/test_meu_plugin.py
import pytest
from runtime.plugins.tool.meu_plugin.meu_plugin import MeuPlugin

@pytest.mark.asyncio
async def test_minha_funcao():
    plugin = MeuPlugin(config={}, runtime=mock_runtime)
    result = await plugin.minha_funcao(mock_context, "test")
    assert result.success
    assert result.data["result"] == "ok"
```

### 7. Documentação

Crie `README.md` no diretório do plugin com:
- Descrição
- Configuração (exemplo `plugin.yaml`)
- Tools:
- Exemplos de uso
- Capabilities
- Rate limits
- Troubleshooting

---

## 📦 PUBLICAÇÃO NO MARKETPLACE

### Requisitos para Marketplace Oficial

| Requisito | Obrigatório |
|-----------|-------------|
| `plugin.yaml` completo e válido | ✅ |
| Testes passando (unit + integration) | ✅ |
| Documentação `README.md` | ✅ |
| Licença compatível (MIT, Apache-2.0) | ✅ |
| Sem dependências não-declaradas | ✅ |
| Health check implementado | ✅ |
| Observabilidade (logs, métricas, eventos) | ✅ |
| Assinatura digital (futuro) | ⚠️ |

### Processo de Submissão

```bash
# 1. Validar plugin
aipensa-engine plugin validate ./runtime/plugins/tool/meu_plugin

# 2. Empacotar
aipensa-engine plugin package ./runtime/plugins/tool/meu_plugin -o meu_plugin-1.0.0.apip

# 3. Publicar (requer conta no marketplace)
aipensa-engine plugin publish meu_plugin-1.0.0.apip
```

---

## 🔄 HOT RELOAD (Desenvolvimento)

```python
# Em desenvolvimento, recarregar plugin sem reiniciar Engine
from runtime.plugins.manager import PluginManager

plugin_manager = runtime.plugin_manager

# Recarregar plugin específico
await plugin_manager.reload("web_search")

# Recarregar todos plugins de um tipo
await plugin_manager.reload_type(PluginType.TOOL)

# Ver status
status = plugin_manager.get_plugin_status("web_search")
print(status.version, status.status, status.last_reload)
```

---

## ⚠️ BOAS PRÁTICAS E ANTI-PATTERNS

### ✅ FAÇA

```python
# 1. Use config schema para validação
@tool(...)
async def minha_tool(self, ctx: ToolContext, 
                     param: Annotated[str, Field(min_length=1, max_length=100)]) -> ToolResult:

# 2. Emita eventos para observabilidade
await self.emit_event(ToolExecuted(tool_name="minha_tool", ...))

# 3. Trate erros graciosamente
try:
    result = await external_api.call()
except ExternalAPIError as e:
    return ToolResult.error(f"API unavailable: {e}")

# 4. Use secrets manager para credenciais
api_key = self.get_secret("minha_api_key")

# 5. Implemente health_check
async def health_check(self) -> PluginHealth:
    try:
        await self.client.ping()
        return PluginHealth(status="healthy")
    except:
        return PluginHealth(status="unhealthy", error="connection failed")
```

### ❌ NÃO FAÇA

```python
# 1. Hardcode config
api_key = "sk-12345"  # NUNCA!

# 2. Bloqueie event loop
time.sleep(10)  # Use asyncio.sleep ou thread pool

# 3. Importe módulos internos da Engine diretamente
from runtime.agent.module import AgentModule  # Use self.runtime.get_module()

# 4. Mantenha estado global mutável
GLOBAL_CACHE = {}  # Use self.runtime.get_module("memory")

# 5. Assuma estrutura de outros plugins
other_plugin.internal_method()  # Use EventBus ou Module.execute()

# 6. Log sem correlation_id
logger.info("Done")  # Use logger.info("Done", correlation_id=ctx.correlation_id)
```

---

## 📋 CHECKLIST DE VALIDAÇÃO (Para PR de Plugin)

- [ ] `plugin.yaml` válido contra schema
- [ ] Classe herda de `ToolPlugin`/`LLMPlugin`/etc correto
- [ ] `@tool` decorators para tools públicas
- [ ] `config_schema` JSON Schema válido (Draft 2020-12)
- [ ] `health_check()` implementado
- [ ] Eventos emitidos: `ToolExecuted`, `ToolFailed`, etc
- [ ] Logs estruturados com `correlation_id`
- [ ] Métricas Prometheus exportadas
- [ ] Tratamento de erros sem crash
- [ ] Secrets via `self.get_secret()` ou config
- [ ] Testes: unit + integration + health
- [ ] Documentação `README.md`
- [ ] Sem imports de `aipensa_core`
- [ ] Type hints 100% (mypy strict passa)

---

**TODO PLUGIN DEVE SEGUIR ESTE GUIA. PLUGINS QUE VIOLEM ESTAS REGRAS SERÃO REJEITADOS NO LOAD TIME.**