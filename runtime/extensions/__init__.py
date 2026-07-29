"""
AIPENSA Engine Extensions Layer.

Este pacote contém as extensões da Engine que adicionam inteligência de negócio
sem modificar o Kernel congelado.

Arquitetura:
- runtime/extensions/company/ - Company Context Engine
- runtime/extensions/employee/ - Employee System (Agent + Business Context)
- runtime/extensions/team/ - Team Manager (Hierarchical Workspaces)
- runtime/extensions/provider/ - Provider Registry (External Connections)
- runtime/extensions/onboarding/ - Onboarding Contracts (Core implements, Engine consumes)
- runtime/extensions/explorer/ - Runtime & Company Explorers
- runtime/extensions/sync/ - Sync Package (Engine ↔ Core YAML)
"""

from runtime.extensions.company.engine import (
    CompanyContextEngine,
    CompanyContextResolver,
    CompanyContextModule,
)

from runtime.extensions.employee.employee import (
    EmployeeProfile,
    EmployeeRole,
    MemoryScope,
    EmployeeFactory,
    EmployeeRegistry,
    EmployeeModule,
    ROLE_CONFIGS,
)

from runtime.extensions.team.team import (
    TeamRole,
    TeamType,
    TeamMember,
    Team,
    TeamManager,
    TeamModule,
)

from runtime.extensions.provider.provider import (
    ProviderType,
    ProviderCapability as Capability,
    ProviderConnection as Connection,
    OAuthConfig,
    Provider,
    ConnectionManager,
    ProviderRegistry,
    ProviderModule,
    MetaProvider,
    TwilioProvider,
    StripeProvider,
    S3StorageProvider,
)

from runtime.extensions.onboarding.onboarding import (
    OnboardingSource,
    BaseOnboardingAdapter,
    OnboardingOrchestrator,
    OnboardingStep,
    ONBOARDING_FLOW,
    SOURCE_CREDENTIAL_SCHEMAS,
    OnboardingModule,
)

from runtime.extensions.explorer.explorer import (
    RuntimeExplorer,
    CompanyExplorer,
    ExplorerModule,
)

from runtime.extensions.sync.sync import (
    SyncPackage,
    SyncExporter,
    SyncImporter,
    SyncModule,
)

__version__ = "1.0.0"

__all__ = [
    # Company
    "CompanyContextEngine",
    "CompanyContextResolver",
    "CompanyContextModule",
    # Employee
    "EmployeeProfile",
    "EmployeeRole",
    "MemoryScope",
    "EmployeeFactory",
    "EmployeeRegistry",
    "EmployeeModule",
    "ROLE_CONFIGS",
    # Team
    "TeamRole",
    "TeamType",
    "TeamMember",
    "Team",
    "TeamManager",
    "TeamModule",
    # Provider
    "ProviderType",
    "Capability",
    "OAuthConfig",
    "Provider",
    "Connection",
    "ConnectionManager",
    "ProviderRegistry",
    "ProviderModule",
    "MetaProvider",
    "TwilioProvider",
    "StripeProvider",
    "S3StorageProvider",
    # Onboarding
    "OnboardingSource",
    "BaseOnboardingAdapter",
    "OnboardingOrchestrator",
    "OnboardingStep",
    "ONBOARDING_FLOW",
    "SOURCE_CREDENTIAL_SCHEMAS",
    "OnboardingModule",
    # Explorer
    "RuntimeExplorer",
    "CompanyExplorer",
    "ExplorerModule",
    # Sync
    "SyncPackage",
    "SyncExporter",
    "SyncImporter",
    "SyncModule",
]