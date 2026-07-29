"""
Company Context Engine - Camada ACIMA dos Agents/Employees.

A Engine NÃO conhece schemas de negócio. O Core define, a Engine armazena e resolve.
Esta é a implementação da separação Engine ↔ Core definida na ENGINE_SPEC.md.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from enum import Enum

from runtime.base.module import RuntimeModule, ModuleMetadata
from runtime.base.events import get_event_bus, RuntimeEventType, RuntimeEvent, create_event
from runtime.modules import MemoryModule


class OnboardingSource(Protocol):
    """Protocolo para fontes de onboarding (Core implementa, Engine consome)."""

    async def fetch_company_profile(self, company_id: str) -> Dict[str, Any]: ...
    async def fetch_brand(self, company_id: str) -> Dict[str, Any]: ...
    async def fetch_products(self, company_id: str) -> Dict[str, Any]: ...
    async def fetch_channels(self, company_id: str) -> Dict[str, Any]: ...
    async def fetch_goals(self, company_id: str) -> Dict[str, Any]: ...
    async def fetch_knowledge(self, company_id: str) -> List[Dict[str, Any]]: ...


@dataclass
class CompanyProfile:
    """Perfil da empresa - schema definido pelo Core, Engine apenas armazena."""
    company_id: str
    name: str
    legal_name: str
    tax_id: str
    segment: str
    size: str
    founded_date: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompanyBrand:
    """Brand/Voice da empresa."""
    company_id: str
    name: str
    tagline: str
    colors: Dict[str, str]
    logo_url: str
    voice_tone: str
    guidelines: str
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompanyProducts:
    """Produtos e serviços da empresa."""
    company_id: str
    products: List[Dict[str, Any]] = field(default_factory=list)
    services: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompanyChannels:
    """Canais de comunicação/presença digital."""
    company_id: str
    instagram: Optional[Dict[str, Any]] = None
    facebook: Optional[Dict[str, Any]] = None
    tiktok: Optional[Dict[str, Any]] = None
    whatsapp: Optional[Dict[str, Any]] = None
    website: Optional[Dict[str, Any]] = None
    google_business: Optional[Dict[str, Any]] = None
    linkedin: Optional[Dict[str, Any]] = None
    youtube: Optional[Dict[str, Any]] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompanyGoals:
    """Objetivos e KPIs da empresa."""
    company_id: str
    okrs: List[Dict[str, Any]] = field(default_factory=list)
    kpis: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KnowledgeEntry:
    """Entrada no Knowledge Base da empresa."""
    document_id: str
    company_id: str
    title: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompanyContext:
    """Contexto completo resolvido para um Employee."""
    company_id: str
    profile: CompanyProfile
    brand: CompanyBrand
    products: CompanyProducts
    channels: CompanyChannels
    goals: CompanyGoals
    knowledge: List[KnowledgeEntry] = field(default_factory=list)
    resolved_at: datetime = field(default_factory=datetime.utcnow)
    employee_role: Optional[str] = None
    task_context: Optional[str] = None


class CompanyContextResolver:
    """
    Resolve contexto da empresa para um Employee específico.
    Engine-agnostic: apenas compõe dados armazenados.
    """

    def __init__(self, memory_module: MemoryModule, event_bus):
        self.memory = memory_module
        self.event_bus = event_bus
        self._cache: Dict[str, CompanyContext] = {}
        self._cache_ttl = 300  # 5 minutos

    async def resolve_for_employee(
        self,
        employee_id: str,
        company_id: str,
        role: Optional[str] = None,
        task: Optional[str] = None
    ) -> CompanyContext:
        """Monta contexto completo para um Employee."""
        cache_key = f"ctx:{company_id}:{role or 'default'}"

        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if (datetime.utcnow() - cached.resolved_at).total_seconds() < self._cache_ttl:
                return cached

        # Buscar todos os componentes
        profile = await self._get_profile(company_id)
        brand = await self._get_brand(company_id)
        products = await self._get_products(company_id)
        channels = await self._get_channels(company_id)
        goals = await self._get_goals(company_id)

        # Buscar knowledge relevante (semantic search se embedding disponível)
        knowledge = await self._search_relevant_knowledge(
            company_id=company_id,
            role=role,
            task=task
        )

        context = CompanyContext(
            company_id=company_id,
            profile=profile,
            brand=brand,
            products=products,
            channels=channels,
            goals=goals,
            knowledge=knowledge,
            employee_role=role,
            task_context=task
        )

        self._cache[cache_key] = context
        return context

    async def _get_profile(self, company_id: str) -> CompanyProfile:
        data = await self.memory.read(store=f"company_{company_id}", key="profile")
        if not data:
            return CompanyProfile(company_id=company_id, name="", legal_name="", tax_id="", segment="", size="", founded_date="")
        return CompanyProfile(**data)

    async def _get_brand(self, company_id: str) -> CompanyBrand:
        data = await self.memory.read(store=f"company_{company_id}", key="brand")
        if not data:
            return CompanyBrand(company_id=company_id, name="", tagline="", colors={}, logo_url="", voice_tone="", guidelines="")
        return CompanyBrand(**data)

    async def _get_products(self, company_id: str) -> CompanyProducts:
        data = await self.memory.read(store=f"company_{company_id}", key="products")
        if not data:
            return CompanyProducts(company_id=company_id)
        return CompanyProducts(**data)

    async def _get_channels(self, company_id: str) -> CompanyChannels:
        data = await self.memory.read(store=f"company_{company_id}", key="channels")
        if not data:
            return CompanyChannels(company_id=company_id)
        return CompanyChannels(**data)

    async def _get_goals(self, company_id: str) -> CompanyGoals:
        data = await self.memory.read(store=f"company_{company_id}", key="goals")
        if not data:
            return CompanyGoals(company_id=company_id)
        return CompanyGoals(**data)

    async def _search_relevant_knowledge(
        self,
        company_id: str,
        role: Optional[str],
        task: Optional[str]
    ) -> List[KnowledgeEntry]:
        """Busca semântica no knowledge base."""
        query_parts = []
        if role:
            query_parts.append(role)
        if task:
            query_parts.append(task)
        query = " ".join(query_parts) if query_parts else ""

        if not query:
            # Retornar os mais recentes
            data = await self.memory.read(store=f"company_{company_id}_knowledge", key="index")
            if not data:
                return []
            return [KnowledgeEntry(**k) for k in data.get("entries", [])[:10]]

        # Tentar busca vetorial
        try:
            embedding_module = self.memory.runtime.get_module("embedding")
            if embedding_module:
                embedding = await embedding_module.embed(query)
                results = await self.memory.vector_search(
                    store=f"company_{company_id}_knowledge",
                    vector=embedding,
                    top_k=10
                )
                return [KnowledgeEntry(**r.value) for r in results]
        except Exception:
            pass

        # Fallback: busca textual simples
        data = await self.memory.read(store=f"company_{company_id}_knowledge", key="index")
        if not data:
            return []
        entries = [KnowledgeEntry(**k) for k in data.get("entries", [])]
        # Filtro simples por tags/categoria
        query_lower = query.lower()
        filtered = [
            e for e in entries
            if query_lower in e.content.lower()
            or query_lower in e.title.lower()
            or any(query_lower in tag.lower() for tag in e.tags)
        ]
        return filtered[:10]


class CompanyContextEngine:
    """
    Engine de Contexto de Empresa.

    Responsabilidades:
    - Armazenar dados de empresa (via MemoryModule)
    - Resolver contexto para Employees
    - Emitir eventos de mudança
    - Integrar com Onboarding Sources (Core)

    NÃO responsabilidades (pertencem ao Core):
    - Definir schemas de negócio
    - Implementar Onboarding Adapters (Instagram, CRM, WhatsApp, Website)
    - Lógica de validação de domínio
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.memory: Optional[MemoryModule] = None
        self.event_bus = get_event_bus()
        self.resolver: Optional[CompanyContextResolver] = None
        self.onboarding_sources: Dict[str, OnboardingSource] = {}

    async def initialize(self) -> None:
        self.memory = self.runtime.get_module("memory")
        self.resolver = CompanyContextResolver(self.memory, self.event_bus)

        # Registrar evento handlers
        from runtime.base.events import EventHandler

        class ProfileUpdatedHandler(EventHandler):
            def __init__(self, engine):
                self.engine = engine

            @property
            def handles_event_types(self):
                return [RuntimeEventType.COMPANY_PROFILE_UPDATED]

            async def handle(self, event: RuntimeEvent) -> None:
                await self.engine._on_profile_updated(event)

        class KnowledgeStoredHandler(EventHandler):
            def __init__(self, engine):
                self.engine = engine

            @property
            def handles_event_types(self):
                return [RuntimeEventType.COMPANY_KNOWLEDGE_STORED]

            async def handle(self, event: RuntimeEvent) -> None:
                await self.engine._on_knowledge_updated(event)

        self.event_bus.subscribe(RuntimeEventType.COMPANY_PROFILE_UPDATED, ProfileUpdatedHandler(self))
        self.event_bus.subscribe(RuntimeEventType.COMPANY_KNOWLEDGE_STORED, KnowledgeStoredHandler(self))

    async def save_profile(self, company_id: str, profile: CompanyProfile) -> None:
        await self.memory.write(
            store=f"company_{company_id}",
            key="profile",
            value=profile.__dict__,
            ttl=None
        )
        await self.event_bus.publish(create_event(
            RuntimeEventType.COMPANY_PROFILE_UPDATED,
            f"company_context:{company_id}",
            {"company_id": company_id, "profile": profile.__dict__}
        ))

    async def save_brand(self, company_id: str, brand: CompanyBrand) -> None:
        await self.memory.write(
            store=f"company_{company_id}",
            key="brand",
            value=brand.__dict__,
            ttl=None
        )
        await self.event_bus.publish(create_event(
            RuntimeEventType.COMPANY_BRAND_UPDATED,
            f"company_context:{company_id}",
            {"company_id": company_id, "brand": brand.__dict__}
        ))

    async def save_products(self, company_id: str, products: CompanyProducts) -> None:
        await self.memory.write(
            store=f"company_{company_id}",
            key="products",
            value=products.__dict__,
            ttl=None
        )

    async def save_channels(self, company_id: str, channels: CompanyChannels) -> None:
        await self.memory.write(
            store=f"company_{company_id}",
            key="channels",
            value=channels.__dict__,
            ttl=None
        )

    async def save_goals(self, company_id: str, goals: CompanyGoals) -> None:
        await self.memory.write(
            store=f"company_{company_id}",
            key="goals",
            value=goals.__dict__,
            ttl=None
        )

    async def add_knowledge(self, entry: KnowledgeEntry) -> None:
        # Store individual entry
        await self.memory.write(
            store=f"company_{entry.company_id}_knowledge",
            key=f"entry_{entry.document_id}",
            value=entry.__dict__,
            ttl=None
        )

        # Update index
        index = await self.memory.read(store=f"company_{entry.company_id}_knowledge", key="index")
        if not index:
            index = {"entries": []}

        # Remove old if exists
        index["entries"] = [e for e in index["entries"] if e.get("document_id") != entry.document_id]
        index["entries"].insert(0, entry.__dict__)
        index["entries"] = index["entries"][:1000]  # Limit

        await self.memory.write(
            store=f"company_{entry.company_id}_knowledge",
            key="index",
            value=index,
            ttl=None
        )

        # Generate embedding if possible
        try:
            embedding_module = self.runtime.get_module("embedding")
            if embedding_module:
                embedding = await embedding_module.embed(entry.content)
                entry.embedding = embedding
                await self.memory.write(
                    store=f"company_{entry.company_id}_knowledge_vec",
                    key=f"vec_{entry.document_id}",
                    value={"embedding": embedding, "metadata": entry.__dict__},
                    ttl=None
                )
        except Exception:
            pass  # Embedding optional

        await self.event_bus.publish(create_event(
            RuntimeEventType.COMPANY_KNOWLEDGE_STORED,
            f"company_context:{entry.company_id}",
            {"company_id": entry.company_id, "document_id": entry.document_id}
        ))

    async def search_knowledge(
        self,
        company_id: str,
        query: str,
        role: Optional[str] = None,
        limit: int = 10
    ) -> List[KnowledgeEntry]:
        if self.resolver:
            return await self.resolver._search_relevant_knowledge(company_id, role, query)
        return []

    async def get_context_for_employee(
        self,
        employee_id: str,
        company_id: str,
        role: Optional[str] = None,
        task: Optional[str] = None
    ) -> CompanyContext:
        if not self.resolver:
            raise RuntimeError("CompanyContextEngine not initialized")
        return await self.resolver.resolve_for_employee(employee_id, company_id, role, task)

    async def run_onboarding(self, company_id: str, source_types: List[str]) -> Dict[str, Any]:
        """Executa onboarding usando sources registradas pelo Core."""
        results = {}
        for source_type in source_types:
            source = self.onboarding_sources.get(source_type)
            if not source:
                results[source_type] = {"error": f"Source {source_type} not registered"}
                continue

            try:
                # Fetch data from source
                profile = await source.fetch_company_profile(company_id)
                brand = await source.fetch_brand(company_id)
                products = await source.fetch_products(company_id)
                channels = await source.fetch_channels(company_id)
                goals = await source.fetch_goals(company_id)
                knowledge = await source.fetch_knowledge(company_id)

                # Save all
                if profile:
                    await self.save_profile(company_id, CompanyProfile(**profile))
                if brand:
                    await self.save_brand(company_id, CompanyBrand(**brand))
                if products:
                    await self.save_products(company_id, CompanyProducts(**products))
                if channels:
                    await self.save_channels(company_id, CompanyChannels(**channels))
                if goals:
                    await self.save_goals(company_id, CompanyGoals(**goals))
                if knowledge:
                    for k in knowledge:
                        await self.add_knowledge(KnowledgeEntry(**k))

                results[source_type] = {"status": "success", "knowledge_count": len(knowledge)}
            except Exception as e:
                results[source_type] = {"error": str(e)}

        return results

    def register_onboarding_source(self, source_type: str, source: OnboardingSource) -> None:
        """Core registra implementações de OnboardingSource."""
        self.onboarding_sources[source_type] = source

    async def _on_profile_updated(self, event) -> None:
        # Invalidate cache
        company_id = event.payload.get("company_id")
        if company_id and self.resolver:
            for key in list(self.resolver._cache.keys()):
                if company_id in key:
                    del self.resolver._cache[key]

    async def _on_knowledge_updated(self, event) -> None:
        company_id = event.payload.get("company_id")
        if company_id and self.resolver:
            for key in list(self.resolver._cache.keys()):
                if company_id in key:
                    del self.resolver._cache[key]


class CompanyContextModule(RuntimeModule):
    """Module wrapper para integração com Runtime."""

    metadata = ModuleMetadata(
        name="company_context",
        version="1.0.0",
        description="Company Context Engine - Business context storage and resolution"
    )

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.engine: Optional[CompanyContextEngine] = None

    async def initialize(self, runtime, config: Dict[str, Any]) -> None:
        await super().initialize(runtime, config)
        self.engine = CompanyContextEngine(runtime)
        await self.engine.initialize()

    async def start(self) -> None:
        await super().start()
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            RuntimeEventType.MODULE_STARTED,
            "company_context",
            {"module": self.name, "version": self.metadata.version}
        ))

    async def stop(self) -> None:
        await super().stop()

    async def cleanup(self) -> None:
        self.engine = None
        await super().cleanup()

    async def health_check(self):
        from runtime.base.module import ModuleHealth, ModuleState
        return ModuleHealth(
            module=self.name,
            state=ModuleState.RUNNING,
            checks={"memory": "ok", "resolver": "ok"},
            timestamp=datetime.utcnow()
        )

    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "save_profile": self.engine.save_profile,
            "get_profile": self.engine.get_profile,
            "save_brand": self.engine.save_brand,
            "get_brand": self.engine.get_brand,
            "save_products": self.engine.save_products,
            "get_products": self.engine.get_products,
            "save_channels": self.engine.save_channels,
            "get_channels": self.engine.get_channels,
            "save_goals": self.engine.save_goals,
            "get_goals": self.engine.get_goals,
            "add_knowledge": self.engine.add_knowledge,
            "search_knowledge": self.engine.search_knowledge,
            "get_context_for_employee": self.engine.get_context_for_employee,
            "run_onboarding": self.engine.run_onboarding,
            "register_onboarding_source": self.engine.register_onboarding_source,
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: {operation}")
        return await ops[operation](**params)

    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "save_profile": self.engine.save_profile,
            "save_brand": self.engine.save_brand,
            "save_products": self.engine.save_products,
            "save_channels": self.engine.save_channels,
            "save_goals": self.engine.save_goals,
            "add_knowledge": self.engine.add_knowledge,
            "search_knowledge": self.engine.search_knowledge,
            "get_context_for_employee": self.engine.get_context_for_employee,
            "run_onboarding": self.engine.run_onboarding,
            "register_onboarding_source": self.engine.register_onboarding_source,
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: {operation}")
        return await ops[operation](**params)