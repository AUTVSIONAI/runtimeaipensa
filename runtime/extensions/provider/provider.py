"""
Provider Registry - Camada de Integrações Externas.

Estende os módulos existentes (LLM, Tool, Network) para gerir conexões
com provedores externos: Meta, Twilio, OpenAI, AWS, Stripe, etc.

Este módulo NÃO substitui LLMModule, ToolModule, NetworkModule.
Ele COMPÕE eles via Provider Abstraction.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import json

from runtime.base.module import RuntimeModule, ModuleMetadata
from runtime.base.events import get_event_bus, RuntimeEventType, create_event
from runtime.llm.module import LLMModule
from runtime.tool.module import ToolModule
from runtime.network.local_network import LocalNetworkModule


class ProviderType(str, Enum):
    """Tipos de providers suportados."""
    LLM = "LLM"
    SOCIAL = "SOCIAL"           # Meta, TikTok, LinkedIn, Twitter/X
    COMMUNICATION = "COMMUNICATION"  # WhatsApp, Twilio, SendGrid, Email
    STORAGE = "STORAGE"         # S3, GCS, Azure Blob, MinIO
    PAYMENT = "PAYMENT"         # Stripe, MercadoPago, Asaas, PayPal
    AI_SERVICE = "AI_SERVICE"   # Replicate, ElevenLabs, Runway, Stability
    DATA = "DATA"               # NewsAPI, SerpAPI, Clearbit, Apollo
    CRM = "CRM"                 # Salesforce, HubSpot, Pipedrive
    CALENDAR = "CALENDAR"       # Google Calendar, Cal.com, Outlook
    ANALYTICS = "ANALYTICS"     # GA4, Mixpanel, Amplitude
    SEARCH = "SEARCH"           # Algolia, ElasticSearch, Meilisearch


class ProviderCapability:
    """Uma capability (operação) que o provider oferece."""

    def __init__(
        self,
        capability_id: str,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        rate_limit: Optional[Dict[str, int]] = None,
        requires_scopes: List[str] = None
    ):
        self.capability_id = capability_id
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.rate_limit = rate_limit or {}
        self.requires_scopes = requires_scopes or []


class OAuthConfig:
    """Configuração OAuth do provider."""
    def __init__(
        self,
        authorization_url: str,
        token_url: str,
        scopes: List[str],
        pkce: bool = False,
        extra_params: Dict[str, str] = None
    ):
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.scopes = scopes
        self.pkce = pkce
        self.extra_params = extra_params or {}


class Provider(ABC):
    """
    Base class para Providers.

    Cada provider implementa:
    - Suas capabilities (operações)
    - Config schema (credenciais necessárias)
    - OAuth config (se suportado)
    - Health check
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._capabilities: Dict[str, ProviderCapability] = {}
        self._register_capabilities()

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    @abstractmethod
    def config_schema(self) -> Dict[str, Any]: ...

    @property
    def oauth_config(self) -> Optional[OAuthConfig]:
        return None

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return list(self._capabilities.values())

    def _register_capabilities(self) -> None:
        """Override para registrar capabilities."""
        pass

    def add_capability(self, cap: ProviderCapability) -> None:
        self._capabilities[cap.capability_id] = cap

    def get_capability(self, capability_id: str) -> Optional[ProviderCapability]:
        return self._capabilities.get(capability_id)

    @abstractmethod
    async def execute_capability(
        self,
        connection: "ProviderConnection",
        capability_id: str,
        params: Dict[str, Any]
    ) -> Any:
        """Executa uma capability usando as credenciais da conexão."""
        pass

    async def health_check(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica se as credenciais funcionam."""
        return {"status": "unknown", "message": "Not implemented"}

    async def refresh_credentials(self, connection: "ProviderConnection") -> Dict[str, Any]:
        """Refresh OAuth tokens se aplicável."""
        return connection.credentials


class ProviderConnection:
    """Uma conexão credenciada a um provider para uma Company."""

    def __init__(
        self,
        connection_id: str,
        provider_id: str,
        company_id: str,
        credentials: Dict[str, Any],
        scopes: List[str] = None,
        status: str = "connected",
        connected_at: datetime = None,
        expires_at: datetime = None,
        last_used_at: datetime = None,
        error: Optional[str] = None
    ):
        self.connection_id = connection_id
        self.provider_id = provider_id
        self.company_id = company_id
        self.credentials = credentials
        self.scopes = scopes or []
        self.status = status
        self.connected_at = connected_at or datetime.utcnow()
        self.expires_at = expires_at
        self.last_used_at = last_used_at
        self.error = error

    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.utcnow() >= self.expires_at
        return False


class ConnectionManager:
    """Gerencia lifecycle de conexões: create, validate, refresh, revoke."""

    def __init__(self, provider_registry: "ProviderRegistry"):
        self.registry = provider_registry
        self.connections: Dict[str, ProviderConnection] = {}  # connection_id -> connection
        self.company_connections: Dict[str, List[str]] = {}  # company_id -> [connection_ids]

    async def create_connection(
        self,
        company_id: str,
        provider_id: str,
        credentials: Dict[str, Any],
        scopes: List[str] = None,
        connection_id: str = None
    ) -> ProviderConnection:
        provider = self.registry.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        # Validar credenciais
        provider.validate_credentials(credentials)

        # Test connection
        health = await provider.health_check(credentials)
        if health.get("status") != "healthy":
            raise ValueError(f"Connection test failed: {health.get('message')}")

        conn = ProviderConnection(
            connection_id=connection_id or f"conn_{provider_id}_{company_id}_{datetime.utcnow().timestamp()}",
            provider_id=provider_id,
            company_id=company_id,
            credentials=credentials,
            scopes=scopes or [],
            status="connected"
        )

        self.connections[conn.connection_id] = conn
        if company_id not in self.company_connections:
            self.company_connections[company_id] = []
        self.company_connections[company_id].append(conn.connection_id)

        # Emit event
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            RuntimeEventType.PROVIDER_CONNECTED,
            f"provider:{provider_id}",
            {
                "provider_id": provider_id,
                "connection_id": conn.connection_id,
                "company_id": company_id,
                "scopes": scopes
            }
        ))

        return conn

    async def create_oauth_connection(
        self,
        company_id: str,
        provider_id: str,
        redirect_uri: str,
        scopes: List[str] = None,
        state: str = None
    ) -> Dict[str, Any]:
        """Inicia fluxo OAuth."""
        provider = self.registry.get_provider(provider_id)
        if not provider or not provider.oauth_config:
            raise ValueError(f"Provider {provider_id} does not support OAuth")

        oauth = provider.oauth_config
        auth_url = (
            f"{oauth.authorization_url}?"
            f"client_id={self.registry.get_client_id(provider_id)}&"
            f"redirect_uri={redirect_uri}&"
            f"scope={' '.join(scopes or oauth.scopes)}&"
            f"response_type=code&"
            f"state={state or ''}&"
            f"{oauth.pkce and 'code_challenge_method=S256&' or ''}"
        )

        # Create pending connection
        conn = ProviderConnection(
            connection_id=f"conn_pending_{state}",
            provider_id=provider_id,
            company_id=company_id,
            credentials={"oauth_state": state, "redirect_uri": redirect_uri},
            scopes=scopes or oauth.scopes,
            status="pending_oauth"
        )
        self.connections[conn.connection_id] = conn

        return {
            "connection_id": conn.connection_id,
            "authorization_url": auth_url,
            "expires_at": datetime.utcnow().replace(hour=datetime.utcnow().hour + 1)
        }

    async def complete_oauth(
        self,
        connection_id: str,
        code: str,
        state: str = None
    ) -> ProviderConnection:
        """Completa fluxo OAuth trocando code por tokens."""
        conn = self.connections.get(connection_id)
        if not conn:
            raise ValueError(f"Connection {connection_id} not found")

        provider = self.registry.get_provider(conn.provider_id)
        oauth = provider.oauth_config

        # Exchange code for tokens
        # (Implementation would use network module)
        tokens = await self._exchange_code_for_tokens(
            oauth.token_url,
            code,
            conn.credentials.get("redirect_uri"),
            self.registry.get_client_id(conn.provider_id),
            self.registry.get_client_secret(conn.provider_id)
        )

        conn.credentials = tokens
        conn.scopes = tokens.get("scopes", conn.scopes)
        conn.status = "connected"
        conn.connected_at = datetime.utcnow()
        conn.expires_at = datetime.utcnow().replace(second=datetime.utcnow().second + tokens.get("expires_in", 3600)) if tokens.get("expires_in") else None

        await self.registry.event_bus.publish(create_event(
            RuntimeEventType.PROVIDER_CONNECTED,
            f"provider:{conn.provider_id}",
            {"provider_id": conn.provider_id, "connection_id": conn.connection_id, "company_id": conn.company_id}
        ))

        return conn

    async def _exchange_code_for_tokens(self, token_url, code, redirect_uri, client_id, client_secret):
        # Would use NetworkModule
        return {}

    async def refresh_connection(self, connection_id: str) -> ProviderConnection:
        """Refresh credentials (OAuth token refresh)."""
        conn = self.connections.get(connection_id)
        if not conn:
            raise ValueError(f"Connection {connection_id} not found")

        provider = self.registry.get_provider(conn.provider_id)
        new_creds = await provider.refresh_credentials(conn)
        conn.credentials = new_creds
        conn.last_used_at = datetime.utcnow()

        return conn

    async def revoke_connection(self, connection_id: str) -> bool:
        conn = self.connections.get(connection_id)
        if not conn:
            return False

        conn.status = "revoked"
        # Remove from company index
        if conn.company_id in self.company_connections:
            self.company_connections[conn.company_id] = [
                c for c in self.company_connections[conn.company_id] if c != connection_id
            ]

        await self.registry.event_bus.publish(create_event(
            RuntimeEventType.PROVIDER_DISCONNECTED,
            f"provider:{conn.provider_id}",
            {"provider_id": conn.provider_id, "connection_id": connection_id, "reason": "revoked"}
        ))

        return True

    def get_connection(self, connection_id: str) -> Optional[ProviderConnection]:
        return self.connections.get(connection_id)

    def get_company_connections(self, company_id: str) -> List[ProviderConnection]:
        conn_ids = self.company_connections.get(company_id, [])
        return [self.connections[cid] for cid in conn_ids if cid in self.connections]

    def find_connection_for_capability(
        self,
        company_id: str,
        capability_id: str
    ) -> Optional[ProviderConnection]:
        """Encontra conexão ativa que suporte uma capability."""
        conns = self.get_company_connections(company_id)
        for conn in conns:
            if conn.status != "connected":
                continue
            provider = self.registry.get_provider(conn.provider_id)
            if provider and provider.get_capability(capability_id):
                # Check scopes
                cap = provider.get_capability(capability_id)
                if not cap.requires_scopes or all(s in conn.scopes for s in cap.requires_scopes):
                    return conn
        return None


class ProviderRegistry:
    """
    Registry central de Providers.

    Responsabilidades:
    - Registrar providers (built-in + plugins)
    - Gerenciar conexões por company
    - Discovery de capabilities
    - Fallback chains
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.providers: Dict[str, Provider] = {}
        self.manager = ConnectionManager(self)
        self.event_bus = get_event_bus()
        self._fallback_chains: Dict[str, List[str]] = {}  # capability -> [provider_ids]

    def register(self, provider: Provider) -> None:
        if provider.provider_id in self.providers:
            raise ValueError(f"Provider {provider.provider_id} already registered")
        self.providers[provider.provider_id] = provider

        # Index capabilities
        for cap in provider.capabilities:
            self._fallback_chains.setdefault(cap.capability_id, []).append(provider.provider_id)

        # Emit event
        import asyncio
        asyncio.create_task(self._emit_registered(provider))

    async def _emit_registered(self, provider: Provider):
        await self.event_bus.publish(create_event(
            RuntimeEventType.PROVIDER_REGISTERED,
            f"provider:{provider.provider_id}",
            {
                "provider_id": provider.provider_id,
                "name": provider.name,
                "type": provider.provider_type.value,
                "version": provider.version,
                "capabilities": [c.capability_id for c in provider.capabilities]
            }
        ))

    def get_provider(self, provider_id: str) -> Optional[Provider]:
        return self.providers.get(provider_id)

    def list_providers(self, provider_type: ProviderType = None) -> List[Provider]:
        if provider_type:
            return [p for p in self.providers.values() if p.provider_type == provider_type]
        return list(self.providers.values())

    def get_provider_for_capability(self, capability_id: str, company_id: str) -> Optional[ProviderConnection]:
        """Retorna melhor conexão para capability (com fallback)."""
        provider_ids = self._fallback_chains.get(capability_id, [])
        for pid in provider_ids:
            conn = self.manager.find_connection_for_capability(company_id, capability_id)
            if conn and conn.provider_id == pid:
                return conn
        return None

    def set_fallback_chain(self, capability_id: str, provider_ids: List[str]) -> None:
        """Define ordem de fallback para uma capability."""
        self._fallback_chains[capability_id] = provider_ids

    def get_client_id(self, provider_id: str) -> str:
        return self.runtime.config.get(f"providers.{provider_id}.client_id", "")

    def get_client_secret(self, provider_id: str) -> str:
        return self.runtime.config.get(f"providers.{provider_id}.client_secret", "")


# =====================================================
# BUILT-IN PROVIDERS EXAMPLES
# =====================================================

class MetaProvider(Provider):
    """Meta (Facebook/Instagram/WhatsApp) Graph API."""

    provider_id = "meta"
    name = "Meta (Instagram, Facebook, WhatsApp)"
    provider_type = ProviderType.SOCIAL
    version = "2.1.0"

    config_schema = {
        "type": "object",
        "properties": {
            "app_id": {"type": "string"},
            "app_secret": {"type": "string", "format": "password"},
            "default_page_id": {"type": "string"}
        },
        "required": ["app_id", "app_secret"]
    }

    oauth_config = OAuthConfig(
        authorization_url="https://www.facebook.com/v18.0/dialog/oauth",
        token_url="https://graph.facebook.com/v18.0/oauth/access_token",
        scopes=[
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
            "pages_read_engagement",
            "whatsapp_business_management",
            "whatsapp_business_messaging"
        ]
    )

    def _register_capabilities(self):
        self.add_capability(ProviderCapability(
            capability_id="instagram_post",
            name="Instagram Feed Post",
            description="Publica post no Instagram Feed",
            input_schema={
                "type": "object",
                "properties": {
                    "image_url": {"type": "string", "format": "uri"},
                    "caption": {"type": "string"},
                    "location_id": {"type": "string"}
                },
                "required": ["image_url", "caption"]
            },
            output_schema={"type": "object", "properties": {"post_id": {"type": "string"}}},
            requires_scopes=["instagram_content_publish"]
        ))

        self.add_capability(ProviderCapability(
            capability_id="instagram_story",
            name="Instagram Story",
            description="Publica Story no Instagram",
            input_schema={
                "type": "object",
                "properties": {
                    "media_url": {"type": "string", "format": "uri"},
                    "is_video": {"type": "boolean", "default": False}
                },
                "required": ["media_url"]
            },
            output_schema={"type": "object", "properties": {"story_id": {"type": "string"}}},
            requires_scopes=["instagram_content_publish"]
        ))

        self.add_capability(ProviderCapability(
            capability_id="facebook_post",
            name="Facebook Page Post",
            description="Publica post na Facebook Page",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "link": {"type": "string", "format": "uri"},
                    "published": {"type": "boolean", "default": True}
                },
                "required": ["message"]
            },
            output_schema={"type": "object", "properties": {"post_id": {"type": "string"}}},
            requires_scopes=["pages_show_list", "pages_read_engagement"]
        ))

        self.add_capability(ProviderCapability(
            capability_id="whatsapp_message",
            name="WhatsApp Business Message",
            description="Envia mensagem via WhatsApp Business API",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Phone number with country code"},
                    "type": {"type": "string", "enum": ["text", "template", "image", "document"]},
                    "text": {"type": "object", "properties": {"body": {"type": "string"}}},
                    "template": {"type": "object", "properties": {
                        "name": {"type": "string"},
                        "language": {"type": "object", "properties": {"code": {"type": "string"}}},
                        "components": {"type": "array"}
                    }}
                },
                "required": ["to", "type"]
            },
            output_schema={"type": "object", "properties": {"message_id": {"type": "string"}}},
            requires_scopes=["whatsapp_business_messaging"]
        ))

    async def execute_capability(
        self,
        connection: ProviderConnection,
        capability_id: str,
        params: Dict[str, Any]
    ) -> Any:
        # Usar NetworkModule para chamar Graph API
        network = self.runtime.get_module("network")
        access_token = connection.credentials.get("access_token")

        if capability_id == "instagram_post":
            # 1. Create media container
            # 2. Publish
            pass
        elif capability_id == "instagram_story":
            pass
        elif capability_id == "facebook_post":
            resp = await network.post(
                f"https://graph.facebook.com/v18.0/{connection.credentials.get('page_id')}/feed",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"message": params["message"], "link": params.get("link")}
            )
            return resp
        elif capability_id == "whatsapp_message":
            phone_id = connection.credentials.get("phone_number_id")
            resp = await network.post(
                f"https://graph.facebook.com/v18.0/{phone_id}/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": params["to"],
                    "type": params["type"],
                    **({params["type"]: params[params["type"]]} if params["type"] != "text" else {"text": params["text"]})
                }
            )
            return resp

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        required = ["access_token"]  # For direct credentials
        for r in required:
            if r not in credentials:
                raise ValueError(f"Missing required credential: {r}")


class TwilioProvider(Provider):
    """Twilio - SMS, WhatsApp, Voice, Video."""

    provider_id = "twilio"
    name = "Twilio Communications"
    provider_type = ProviderType.COMMUNICATION
    version = "1.0.0"

    config_schema = {
        "type": "object",
        "properties": {
            "account_sid": {"type": "string"},
            "auth_token": {"type": "string", "format": "password"},
            "from_number": {"type": "string"}
        },
        "required": ["account_sid", "auth_token"]
    }

    def _register_capabilities(self):
        self.add_capability(ProviderCapability(
            capability_id="send_sms",
            name="Send SMS",
            description="Envia SMS via Twilio",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "body"]
            },
            output_schema={"type": "object", "properties": {"sid": {"type": "string"}}}
        ))

        self.add_capability(ProviderCapability(
            capability_id="send_whatsapp",
            name="Send WhatsApp",
            description="Envia WhatsApp via Twilio",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "body"]
            },
            output_schema={"type": "object", "properties": {"sid": {"type": "string"}}}
        ))

        self.add_capability(ProviderCapability(
            capability_id="make_call",
            name="Make Voice Call",
            description="Inicia chamada de voz",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "url": {"type": "string", "format": "uri", "description": "TwiML URL"}
                },
                "required": ["to", "url"]
            },
            output_schema={"type": "object", "properties": {"sid": {"type": "string"}}}
        ))

    async def execute_capability(
        self,
        connection: ProviderConnection,
        capability_id: str,
        params: Dict[str, Any]
    ) -> Any:
        network = self.runtime.get_module("network")
        account_sid = connection.credentials["account_sid"]
        auth_token = connection.credentials["auth_token"]
        from_number = connection.credentials.get("from_number")

        import base64
        auth_header = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()

        if capability_id == "send_sms":
            resp = await network.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                headers={"Authorization": f"Basic {auth_header}"},
                data={"To": params["to"], "From": from_number, "Body": params["body"]}
            )
            return resp

        elif capability_id == "send_whatsapp":
            resp = await network.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                headers={"Authorization": f"Basic {auth_header}"},
                data={"To": f"whatsapp:{params['to']}", "From": f"whatsapp:{from_number}", "Body": params["body"]}
            )
            return resp

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        for r in ["account_sid", "auth_token"]:
            if r not in credentials:
                raise ValueError(f"Missing required credential: {r}")


class StripeProvider(Provider):
    """Stripe - Pagamentos, Subscriptions, Billing."""

    provider_id = "stripe"
    name = "Stripe Payments"
    provider_type = ProviderType.PAYMENT
    version = "1.0.0"

    config_schema = {
        "type": "object",
        "properties": {
            "secret_key": {"type": "string", "format": "password"},
            "publishable_key": {"type": "string"},
            "webhook_secret": {"type": "string", "format": "password"}
        },
        "required": ["secret_key"]
    }

    def _register_capabilities(self):
        self.add_capability(ProviderCapability(
            capability_id="create_payment_intent",
            name="Create Payment Intent",
            description="Cria intenção de pagamento",
            input_schema={
                "type": "object",
                "properties": {
                    "amount": {"type": "integer", "description": "Amount in cents"},
                    "currency": {"type": "string", "default": "brl"},
                    "customer_id": {"type": "string"},
                    "metadata": {"type": "object"}
                },
                "required": ["amount"]
            },
            output_schema={"type": "object", "properties": {"client_secret": {"type": "string"}, "id": {"type": "string"}}}
        ))

        self.add_capability(ProviderCapability(
            capability_id="create_customer",
            name="Create Customer",
            description="Cria cliente no Stripe",
            input_schema={
                "type": "object",
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string"},
                    "metadata": {"type": "object"}
                },
                "required": ["email"]
            },
            output_schema={"type": "object", "properties": {"id": {"type": "string"}}}
        ))

        self.add_capability(ProviderCapability(
            capability_id="create_subscription",
            name="Create Subscription",
            description="Cria assinatura recorrente",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "price_id": {"type": "string"},
                    "metadata": {"type": "object"}
                },
                "required": ["customer_id", "price_id"]
            },
            output_schema={"type": "object", "properties": {"id": {"type": "string"}, "status": {"type": "string"}}}
        ))

    async def execute_capability(
        self,
        connection: ProviderConnection,
        capability_id: str,
        params: Dict[str, Any]
    ) -> Any:
        network = self.runtime.get_module("network")
        secret_key = connection.credentials["secret_key"]

        if capability_id == "create_payment_intent":
            resp = await network.post(
                "https://api.stripe.com/v1/payment_intents",
                headers={"Authorization": f"Bearer {secret_key}"},
                data=params
            )
            return resp

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        if "secret_key" not in credentials:
            raise ValueError("Missing secret_key")


class S3StorageProvider(Provider):
    """AWS S3 / MinIO / S3-compatible storage."""

    provider_id = "s3"
    name = "S3 Compatible Storage"
    provider_type = ProviderType.STORAGE
    version = "1.0.0"

    config_schema = {
        "type": "object",
        "properties": {
            "access_key": {"type": "string"},
            "secret_key": {"type": "string", "format": "password"},
            "region": {"type": "string", "default": "us-east-1"},
            "endpoint_url": {"type": "string", "format": "uri", "description": "For MinIO/custom S3"}
        },
        "required": ["access_key", "secret_key"]
    }

    def _register_capabilities(self):
        self.add_capability(ProviderCapability(
            capability_id="upload_file",
            name="Upload File",
            description="Faz upload de arquivo",
            input_schema={
                "type": "object",
                "properties": {
                    "bucket": {"type": "string"},
                    "key": {"type": "string"},
                    "content_base64": {"type": "string"},
                    "content_type": {"type": "string"}
                },
                "required": ["bucket", "key", "content_base64"]
            },
            output_schema={"type": "object", "properties": {"etag": {"type": "string"}, "url": {"type": "string"}}}
        ))

        self.add_capability(ProviderCapability(
            capability_id="download_file",
            name="Download File",
            description="Baixa arquivo",
            input_schema={
                "type": "object",
                "properties": {
                    "bucket": {"type": "string"},
                    "key": {"type": "string"}
                },
                "required": ["bucket", "key"]
            },
            output_schema={"type": "object", "properties": {"content_base64": {"type": "string"}, "content_type": {"type": "string"}}}
        ))

        self.add_capability(ProviderCapability(
            capability_id="generate_presigned_url",
            name="Generate Presigned URL",
            description="Gera URL assinada para acesso direto",
            input_schema={
                "type": "object",
                "properties": {
                    "bucket": {"type": "string"},
                    "key": {"type": "string"},
                    "expiration": {"type": "integer", "default": 3600},
                    "method": {"type": "string", "enum": ["GET", "PUT"], "default": "GET"}
                },
                "required": ["bucket", "key"]
            },
            output_schema={"type": "object", "properties": {"url": {"type": "string"}, "expires_at": {"type": "string"}}}
        ))

    async def execute_capability(
        self,
        connection: ProviderConnection,
        capability_id: str,
        params: Dict[str, Any]
    ) -> Any:
        # Usar boto3 ou similar via subprocess/execution module
        pass

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        for r in ["access_key", "secret_key"]:
            if r not in credentials:
                raise ValueError(f"Missing required credential: {r}")


# =====================================================
# PROVIDER MODULE
# =====================================================

class ProviderModule(RuntimeModule):
    """Module wrapper para Provider Registry."""

    metadata = ModuleMetadata(
        name="provider",
        version="1.0.0",
        description="Provider Registry - External system integrations with OAuth, capabilities, fallback chains"
    )

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.registry: Optional[ProviderRegistry] = None

    async def initialize(self, runtime, config: Dict[str, Any]) -> None:
        await super().initialize(runtime, config)
        self.registry = ProviderRegistry(runtime)

        # Register built-in providers
        self.registry.register(MetaProvider())
        self.registry.register(TwilioProvider())
        self.registry.register(StripeProvider())
        self.registry.register(S3StorageProvider())

        # Set default fallback chains
        self.registry.set_fallback_chain("chat_completion", ["nvidia_nim", "openai", "anthropic"])
        self.registry.set_fallback_chain("embedding", ["nvidia_nim", "openai", "cohere"])

    async def start(self) -> None:
        await super().start()
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            RuntimeEventType.MODULE_STARTED,
            "provider",
            {"module": self.name, "version": self.metadata.version, "providers": list(self.registry.providers.keys())}
        ))

    async def stop(self) -> None:
        await super().stop()

    async def cleanup(self) -> None:
        self.registry = None
        await super().cleanup()

    async def health_check(self):
        from runtime.base.module import ModuleHealth, ModuleState
        return ModuleHealth(
            module=self.name,
            state=ModuleState.RUNNING,
            checks={"providers_loaded": str(len(self.registry.providers) if self.registry else 0)},
            timestamp=datetime.utcnow()
        )

    async def execute(self, operation: str, **params) -> Any:
        ops = {
            "register_provider": self.registry.register,
            "get_provider": self.registry.get_provider,
            "list_providers": self.registry.list_providers,
            "create_connection": self.registry.manager.create_connection,
            "create_oauth_connection": self.registry.manager.create_oauth_connection,
            "complete_oauth": self.registry.manager.complete_oauth,
            "refresh_connection": self.registry.manager.refresh_connection,
            "revoke_connection": self.registry.manager.revoke_connection,
            "get_connection": self.registry.manager.get_connection,
            "get_company_connections": self.registry.manager.get_company_connections,
            "execute_capability": self._execute_capability,
            "find_connection_for_capability": self.registry.manager.find_connection_for_capability,
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: {operation}")
        return await ops[operation](**params)

    async def _execute_capability(self, company_id: str, capability_id: str, params: Dict[str, Any]) -> Any:
        """Execute capability with fallback chain."""
        connection = self.registry.manager.find_connection_for_capability(company_id, capability_id)
        if not connection:
            raise ValueError(f"No connection found for capability {capability_id}")
        provider = self.registry.get_provider(connection.provider_id)
        if not provider:
            raise ValueError(f"Provider {connection.provider_id} not found")
        return await provider.execute_capability(connection, capability_id, params)

    async def _execute_capability(
        self,
        connection_id: str,
        capability_id: str,
        params: Dict[str, Any]
    ) -> Any:
        conn = self.registry.manager.get_connection(connection_id)
        if not conn:
            raise ValueError(f"Connection {connection_id} not found")

        provider = self.registry.get_provider(conn.provider_id)
        if not provider:
            raise ValueError(f"Provider {conn.provider_id} not found")

        conn.last_used_at = datetime.utcnow()
        return await provider.execute_capability(conn, capability_id, params)