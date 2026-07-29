"""
Onboarding Contracts - Interfaces para aquisição de dados empresariais.

O Core implementa estes contratos. A Engine apenas consome.
Seguindo o princípio: Engine define Protocol, Core implementa Adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol
from datetime import datetime

from runtime.base.module import RuntimeModule, ModuleMetadata
from runtime.base.events import get_event_bus, RuntimeEventType, create_event


# =====================================================
# ONBOARDING SOURCE PROTOCOL (Engine define, Core implementa)
# =====================================================

class OnboardingSource(Protocol):
    """
    Protocolo para fontes de onboarding.

    O Core AIPENSA implementa adapters concretos:
    - InstagramOnboarding (Meta Graph API)
    - WhatsAppBusinessOnboarding
    - WebsiteScraperOnboarding
    - CRMOnboarding (Salesforce, HubSpot, Pipedrive)
    - GoogleBusinessOnboarding
    - LinkedInOnboarding
    - TikTokOnboarding
    - ManualOnboarding (formulário humano)
    """

    source_type: str
    source_name: str

    async def fetch_company_profile(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]: ...
    async def fetch_brand(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]: ...
    async def fetch_products(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]: ...
    async def fetch_channels(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]: ...
    async def fetch_goals(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]: ...
    async def fetch_knowledge(self, company_id: str, credentials: Dict[str, Any]) -> List[Dict[str, Any]]: ...

    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool: ...


# =====================================================
# BASE ADAPTER (Core herda e implementa)
# =====================================================

class BaseOnboardingAdapter(ABC):
    """Base class para adapters de onboarding."""

    def __init__(self, source_type: str, source_name: str):
        self.source_type = source_type
        self.source_name = source_name

    @abstractmethod
    async def fetch_company_profile(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def fetch_brand(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def fetch_products(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def fetch_channels(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def fetch_goals(self, company_id: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def fetch_knowledge(self, company_id: str, credentials: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        pass


# =====================================================
# ONBOARDING ORCHESTRATOR (Engine side)
# =====================================================

class OnboardingOrchestrator:
    """
    Orquestra onboarding multi-source.

    A Engine NÃO implementa adapters - apenas orquestra.
    O Core registra implementações via register_onboarding_source.
    """

    def __init__(self, company_context_engine):
        self.engine = company_context_engine
        self.adapters: Dict[str, OnboardingSource] = {}

    def register_adapter(self, adapter: OnboardingSource) -> None:
        """Core registra sua implementação."""
        self.adapters[adapter.source_type] = adapter

    async def run_onboarding(
        self,
        company_id: str,
        source_configs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Executa onboarding para múltiplas fontes.

        source_configs = {
            "instagram": {"credentials": {...}},
            "whatsapp": {"credentials": {...}},
            "website": {"credentials": {...}},
            "manual": {"data": {...}}
        }
        """
        results = {}

        for source_type, config in source_configs.items():
            adapter = self.adapters.get(source_type)
            if not adapter:
                results[source_type] = {"status": "error", "error": f"Source {source_type} not registered"}
                continue

            credentials = config.get("credentials", {})
            manual_data = config.get("data", {})

            try:
                # Validar credenciais
                if credentials and not await adapter.validate_credentials(credentials):
                    results[source_type] = {"status": "error", "error": "Invalid credentials"}
                    continue

                # Fetch all data
                profile = await adapter.fetch_company_profile(company_id, credentials) or manual_data.get("profile")
                brand = await adapter.fetch_brand(company_id, credentials) or manual_data.get("brand")
                products = await adapter.fetch_products(company_id, credentials) or manual_data.get("products")
                channels = await adapter.fetch_channels(company_id, credentials) or manual_data.get("channels")
                goals = await adapter.fetch_goals(company_id, credentials) or manual_data.get("goals")
                knowledge = await adapter.fetch_knowledge(company_id, credentials) or manual_data.get("knowledge", [])

                # Save via CompanyContextEngine
                save_results = {}
                if profile:
                    await self.engine.save_profile(company_id, profile)
                    save_results["profile"] = True
                if brand:
                    await self.engine.save_brand(company_id, brand)
                    save_results["brand"] = True
                if products:
                    await self.engine.save_products(company_id, products)
                    save_results["products"] = True
                if channels:
                    await self.engine.save_channels(company_id, channels)
                    save_results["channels"] = True
                if goals:
                    await self.engine.save_goals(company_id, goals)
                    save_results["goals"] = True
                if knowledge:
                    for k in knowledge:
                        await self.engine.add_knowledge(k)
                    save_results["knowledge_count"] = len(knowledge)

                results[source_type] = {
                    "status": "success",
                    "saved": save_results
                }

            except Exception as e:
                results[source_type] = {"status": "error", "error": str(e)}

        return results


# =====================================================
# ONBOARDING STEP DEFINITIONS (para UI)
# =====================================================

@dataclass
class OnboardingStep:
    """Define um step do fluxo de onboarding."""
    step_id: str
    name: str
    description: str
    source_types: List[str]  # Quais sources este step usa
    required: bool = True
    depends_on: List[str] = None  # step_ids que devem completar antes


ONBOARDING_FLOW = [
    OnboardingStep(
        step_id="identity",
        name="Identidade da Empresa",
        description="Nome, CNPJ, segmento, tamanho, data de fundação",
        source_types=["manual", "crm", "government_api"],
        required=True
    ),
    OnboardingStep(
        step_id="brand",
        name="Brand & Voice",
        description="Nome da marca, tagline, cores, logo, tom de voz, guidelines",
        source_types=["manual", "website", "social_media"],
        required=True
    ),
    OnboardingStep(
        step_id="products",
        name="Produtos & Serviços",
        description="Catálogo de produtos, preços, categorias, serviços recorrentes",
        source_types=["manual", "crm", "ecommerce", "erp"],
        required=False
    ),
    OnboardingStep(
        step_id="channels",
        name="Canais de Presença",
        description="Instagram, WhatsApp, Website, LinkedIn, TikTok, Google Business",
        source_types=["instagram", "whatsapp", "website", "linkedin", "tiktok", "google_business"],
        required=True
    ),
    OnboardingStep(
        step_id="goals",
        name="Objetivos & KPIs",
        description="OKRs, KPIs, metas de crescimento, targets financeiros",
        source_types=["manual", "analytics", "finance"],
        required=False
    ),
    OnboardingStep(
        step_id="knowledge",
        name="Base de Conhecimento",
        description="FAQs, políticas, documentos, processos, playbooks",
        source_types=["manual", "drive", "notion", "confluence", "website"],
        required=False
    ),
]


# =====================================================
# CREDENTIAL SCHEMAS POR SOURCE (para validação)
# =====================================================

SOURCE_CREDENTIAL_SCHEMAS = {
    "instagram": {
        "type": "object",
        "properties": {
            "access_token": {"type": "string", "format": "password"},
            "instagram_business_id": {"type": "string"},
            "page_id": {"type": "string"}
        },
        "required": ["access_token", "instagram_business_id"]
    },
    "whatsapp": {
        "type": "object",
        "properties": {
            "access_token": {"type": "string", "format": "password"},
            "phone_number_id": {"type": "string"},
            "business_account_id": {"type": "string"}
        },
        "required": ["access_token", "phone_number_id"]
    },
    "website": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri"},
            "api_key": {"type": "string", "format": "password"},
            "selectors": {"type": "object"}
        },
        "required": ["url"]
    },
    "crm": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["salesforce", "hubspot", "pipedrive"]},
            "api_key": {"type": "string", "format": "password"},
            "domain": {"type": "string"}
        },
        "required": ["type", "api_key"]
    },
    "google_business": {
        "type": "object",
        "properties": {
            "access_token": {"type": "string", "format": "password"},
            "location_id": {"type": "string"}
        },
        "required": ["access_token", "location_id"]
    },
    "linkedin": {
        "type": "object",
        "properties": {
            "access_token": {"type": "string", "format": "password"},
            "organization_id": {"type": "string"}
        },
        "required": ["access_token", "organization_id"]
    },
    "tiktok": {
        "type": "object",
        "properties": {
            "access_token": {"type": "string", "format": "password"},
            "advertiser_id": {"type": "string"}
        },
        "required": ["access_token", "advertiser_id"]
    },
    "manual": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


# =====================================================
# ONBOARDING MODULE
# =====================================================

class OnboardingModule(RuntimeModule):
    """Module wrapper para Onboarding system."""

    metadata = ModuleMetadata(
        name="onboarding",
        version="1.0.0",
        description="Onboarding Orchestrator - Multi-source company data acquisition"
    )

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.orchestrator: Optional[OnboardingOrchestrator] = None

    async def initialize(self, runtime, config: Dict[str, Any]) -> None:
        await super().initialize(runtime, config)
        company_context = self.runtime.get_module("company_context")
        if company_context and company_context.engine:
            self.orchestrator = OnboardingOrchestrator(company_context.engine)
        else:
            # Company context not yet initialized, will be set up later
            pass

    async def start(self) -> None:
        await super().start()
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            RuntimeEventType.MODULE_STARTED,
            "onboarding",
            {"module": self.name, "version": self.metadata.version}
        ))

    async def stop(self) -> None:
        await super().stop()

    async def cleanup(self) -> None:
        self.orchestrator = None
        await super().cleanup()

    async def health_check(self):
        from runtime.base.module import ModuleHealth, ModuleState
        return ModuleHealth(
            module=self.name,
            state=ModuleState.RUNNING,
            checks={"adapters_registered": str(len(self.orchestrator.adapters) if self.orchestrator else 0)},
            timestamp=datetime.utcnow()
        )

    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "run_onboarding": self.orchestrator.run_onboarding,
            "register_adapter": self.orchestrator.register_adapter,
            "get_flow": lambda: ONBOARDING_FLOW,
            "get_credential_schema": lambda source_type: SOURCE_CREDENTIAL_SCHEMAS.get(source_type, {}),
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: {operation}")
        return await ops[operation](**params)