"""
Authentication Runtime Module

Provides JWT, OAuth2, API keys, sessions, RBAC, and token management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import asyncio
import hashlib
import logging
import secrets
import uuid
from urllib.parse import urlencode

import jwt
import aiohttp

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class AuthProvider(Enum):
    """Authentication provider types."""
    LOCAL = "local"
    OAUTH2 = "oauth2"
    OIDC = "oidc"
    LDAP = "ldap"
    SAML = "saml"
    API_KEY = "api_key"
    JWT = "jwt"


class TokenType(Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SESSION = "session"
    MAGIC_LINK = "magic_link"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"


class PermissionAction(Enum):
    """Permission actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    MANAGE = "manage"


@dataclass
class User:
    """User account."""
    user_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    username: str = ""
    email: str = ""
    email_verified: bool = False
    password_hash: Optional[str] = None
    display_name: str = ""
    avatar_url: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    is_superuser: bool = False
    last_login: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    password_changed_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    def has_permission(self, permission: str) -> bool:
        """Check if user has permission."""
        if self.is_superuser:
            return True
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """Check if user has role."""
        if self.is_superuser:
            return True
        return role in self.roles


@dataclass
class Role:
    """Role definition."""
    role_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    permissions: List[str] = field(default_factory=list)
    parent_roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Permission:
    """Permission definition."""
    permission_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""  # e.g., "users.create"
    resource: str = ""  # e.g., "users"
    action: PermissionAction = PermissionAction.READ
    description: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Session:
    """User session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    is_active: bool = True


@dataclass
class Token:
    """Authentication token."""
    token_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    token_type: TokenType = TokenType.ACCESS
    user_id: str = ""
    session_id: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    claims: Dict[str, Any] = field(default_factory=dict)
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if token is valid."""
        if self.revoked:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


@dataclass
class APIKey:
    """API key for programmatic access."""
    key_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    key_hash: str = ""
    key_prefix: str = ""  # First few chars for identification
    name: str = ""
    user_id: str = ""
    scopes: List[str] = field(default_factory=list)
    rate_limit: Optional[int] = None
    ip_whitelist: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def verify_key(self, key: str) -> bool:
        """Verify API key."""
        # First check prefix
        if not key.startswith(self.key_prefix):
            return False
        # Then verify hash
        return hashlib.sha256(key.encode()).hexdigest() == self.key_hash


class AuthBackend(ABC):
    """Abstract authentication backend."""

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate user with credentials."""
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    async def create_user(self, user: User, password: Optional[str] = None) -> User:
        """Create new user."""
        pass

    @abstractmethod
    async def update_user(self, user: User) -> User:
        """Update user."""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        pass

    @abstractmethod
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        pass

    @abstractmethod
    async def reset_password(self, user_id: str, new_password: str) -> bool:
        """Reset user password (admin)."""
        pass


class LocalAuthBackend(AuthBackend):
    """Local authentication backend."""

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._users_by_email: Dict[str, str] = {}
        self._users_by_username: Dict[str, str] = {}

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        identifier = credentials.get("username") or credentials.get("email")
        password = credentials.get("password", "")

        # Find user
        user_id = self._users_by_email.get(identifier) or self._users_by_username.get(identifier)
        if not user_id:
            return None

        user = self._users.get(user_id)
        if not user or not user.is_active:
            return None

        # Check if locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            return None

        # Verify password
        if not self._verify_password(password, user.password_hash or ""):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            await self.update_user(user)
            return None

        # Success
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        await self.update_user(user)
        return user

    def _hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password."""
        import bcrypt
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except:
            return False

    async def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    async def create_user(self, user: User, password: Optional[str] = None) -> User:
        if user.email in self._users_by_email:
            raise ValueError("Email already exists")
        if user.username in self._users_by_username:
            raise ValueError("Username already exists")

        if password:
            user.password_hash = self._hash_password(password)
        user.password_changed_at = datetime.utcnow()
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()

        self._users[user.user_id] = user
        self._users_by_email[user.email] = user.user_id
        self._users_by_username[user.username] = user.user_id
        return user

    async def update_user(self, user: User) -> User:
        user.updated_at = datetime.utcnow()
        self._users[user.user_id] = user
        self._users_by_email[user.email] = user.user_id
        self._users_by_username[user.username] = user.user_id
        return user

    async def delete_user(self, user_id: str) -> bool:
        user = self._users.pop(user_id, None)
        if user:
            self._users_by_email.pop(user.email, None)
            self._users_by_username.pop(user.username, None)
            return True
        return False

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        user = self._users.get(user_id)
        if not user or not self._verify_password(old_password, user.password_hash or ""):
            return False
        user.password_hash = self._hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        await self.update_user(user)
        return True

    async def reset_password(self, user_id: str, new_password: str) -> bool:
        user = self._users.get(user_id)
        if not user:
            return False
        user.password_hash = self._hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        await self.update_user(user)
        return True


class OAuth2Backend(AuthBackend):
    """OAuth2 authentication backend."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.authorize_url = config.get("authorize_url")
        self.token_url = config.get("token_url")
        self.userinfo_url = config.get("userinfo_url")
        self.scopes = config.get("scopes", ["openid", "profile", "email"])
        self._users: Dict[str, User] = {}

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        code = credentials.get("code")
        if not code:
            return None

        # Exchange code for token
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": credentials.get("redirect_uri")
            }) as resp:
                token_data = await resp.json()

        access_token = token_data.get("access_token")
        if not access_token:
            return None

        # Get user info
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(self.userinfo_url, headers=headers) as resp:
                user_info = await resp.json()

        # Map to local user
        return await self._get_or_create_user(user_info, access_token)

    async def _get_or_create_user(self, user_info: Dict[str, Any], access_token: str) -> User:
        # Extract identity
        sub = user_info.get("sub") or user_info.get("id")
        email = user_info.get("email")
        username = user_info.get("preferred_username") or email

        # Check existing
        for user in self._users.values():
            if user.metadata.get("oauth_sub") == sub:
                return user

        # Create new
        user = User(
            email=email,
            username=username,
            display_name=user_info.get("name", ""),
            avatar_url=user_info.get("picture"),
            email_verified=user_info.get("email_verified", False),
            metadata={
                "oauth_sub": sub,
                "oauth_provider": self.config.get("provider", "oauth2"),
                "access_token": access_token
            }
        )
        return await self.create_user(user)

    async def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    async def create_user(self, user: User, password: Optional[str] = None) -> User:
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        self._users[user.user_id] = user
        return user

    async def update_user(self, user: User) -> User:
        user.updated_at = datetime.utcnow()
        self._users[user.user_id] = user
        return user

    async def delete_user(self, user_id: str) -> bool:
        return self._users.pop(user_id, None) is not None

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        return False  # Not applicable for OAuth

    async def reset_password(self, user_id: str, new_password: str) -> bool:
        return False


class JWTManager:
    """JWT token manager."""

    def __init__(self, secret: str, algorithm: str = "HS256", issuer: str = "aipensa"):
        self.secret = secret
        self.algorithm = algorithm
        self.issuer = issuer

    def create_token(
        self,
        user_id: str,
        token_type: TokenType = TokenType.ACCESS,
        scopes: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
        claims: Optional[Dict[str, Any]] = None
    ) -> Token:
        """Create JWT token."""
        now = datetime.utcnow()
        expires_at = now + (expires_delta or timedelta(hours=1))

        token = Token(
            token_type=token_type,
            user_id=user_id,
            scopes=scopes or [],
            claims=claims or {},
            issued_at=now,
            expires_at=expires_at
        )

        # Create JWT payload
        payload = {
            "iss": self.issuer,
            "sub": user_id,
            "type": token_type.value,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "scopes": scopes or [],
            "jti": token.token_id,
            **claims
        }

        token_str = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        token.metadata["token_string"] = token_str
        return token

    def decode_token(self, token_str: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(
                token_str,
                self.secret,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                options={"verify_exp": True}
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def validate_token(self, token_str: str) -> Optional[Token]:
        """Validate token and return Token object."""
        payload = self.decode_token(token_str)
        if not payload:
            return None

        return Token(
            token_id=payload.get("jti", ""),
            token_type=TokenType(payload.get("type", "access")),
            user_id=payload.get("sub", ""),
            scopes=payload.get("scopes", []),
            claims={k: v for k, v in payload.items() if k not in
                    ("iss", "sub", "type", "iat", "exp", "scopes", "jti")},
            issued_at=datetime.fromtimestamp(payload.get("iat", 0)),
            expires_at=datetime.fromtimestamp(payload.get("exp", 0))
        )


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._permissions: Dict[str, Permission] = {}
        self._user_roles: Dict[str, Set[str]] = {}
        self._user_permissions: Dict[str, Set[str]] = {}

    def create_role(self, role: Role) -> Role:
        self._roles[role.role_id] = role
        return role

    def get_role(self, role_id: str) -> Optional[Role]:
        return self._roles.get(role_id)

    def get_role_by_name(self, name: str) -> Optional[Role]:
        for role in self._roles.values():
            if role.name == name:
                return role
        return None

    def create_permission(self, permission: Permission) -> Permission:
        self._permissions[permission.permission_id] = permission
        return permission

    def assign_role(self, user_id: str, role_name: str) -> bool:
        role = self.get_role_by_name(role_name)
        if not role:
            return False
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        self._user_roles[user_id].add(role_name)
        return True

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        if user_id in self._user_roles:
            self._user_roles[user_id].discard(role_name)
            return True
        return False

    def get_user_roles(self, user_id: str) -> List[Role]:
        role_names = self._user_roles.get(user_id, set())
        return [self.get_role_by_name(name) for name in role_names if self.get_role_by_name(name)]

    def get_user_permissions(self, user_id: str) -> List[str]:
        permissions = set(self._user_permissions.get(user_id, set()))

        # Add role permissions
        for role_name in self._user_roles.get(user_id, set()):
            role = self.get_role_by_name(role_name)
            if role:
                permissions.update(role.permissions)

        return list(permissions)

    def check_permission(self, user_id: str, permission: str) -> bool:
        return permission in self.get_user_permissions(user_id)

    def check_any_permission(self, user_id: str, permissions: List[str]) -> bool:
        user_perms = set(self.get_user_permissions(user_id))
        return len(user_perms.intersection(permissions)) > 0

    def check_all_permissions(self, user_id: str, permissions: List[str]) -> bool:
        user_perms = set(self.get_user_permissions(user_id))
        return set(permissions).issubset(user_perms)


class AuthenticationModule(RuntimeModule):
    """
    Authentication and authorization module.

    Supports:
    - Local authentication (username/password)
    - OAuth2/OIDC providers
    - JWT tokens
    - API keys
    - Sessions
    - RBAC (roles, permissions)
    - Magic links
    - Password reset
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="authentication",
            version="1.0.0",
            description="Authentication and authorization with JWT, OAuth2, API keys, RBAC",
            author="AIPENSA",
            dependencies=["memory"],
            provides=["auth", "oauth2", "jwt", "api_keys", "sessions", "rbac"],
            tags={"auth", "authentication", "authorization", "jwt", "oauth2", "rbac"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._backends: Dict[AuthProvider, AuthBackend] = {}
        self._users: Dict[str, User] = {}
        self._sessions: Dict[str, Session] = {}
        self._tokens: Dict[str, Token] = {}
        self._api_keys: Dict[str, APIKey] = {}
        self._jwt_manager: Optional[JWTManager] = None
        self._rbac: RBACManager = RBACManager()
        self._password_reset_tokens: Dict[str, Tuple[str, datetime]] = {}  # token -> (user_id, expires)
        self._magic_link_tokens: Dict[str, Tuple[str, datetime]] = {}
        self._config: Dict[str, Any] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._max_sessions_per_user = config.get("max_sessions_per_user", 5) if config else 5
        self._session_timeout = config.get("session_timeout", 86400) if config else 86400
        self._token_refresh_threshold = config.get("token_refresh_threshold", 300) if config else 300  # 5 min

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize authentication module."""
        self._runtime = runtime
        self._config = {**self._config, **config}

        # Initialize JWT manager
        jwt_secret = self._config.get("jwt_secret", secrets.token_urlsafe(32))
        jwt_algorithm = self._config.get("jwt_algorithm", "HS256")
        jwt_issuer = self._config.get("jwt_issuer", "aipensa")
        self._jwt_manager = JWTManager(jwt_secret, jwt_algorithm, jwt_issuer)

        # Initialize backends
        for provider_name, backend_config in self._config.get("backends", {}).items():
            provider = AuthProvider(provider_name)
            await self._create_backend(provider, backend_config)

        # Load roles and permissions
        for role_data in self._config.get("roles", []):
            role = Role(**role_data)
            self._rbac.create_role(role)

        for perm_data in self._config.get("permissions", []):
            perm = Permission(**perm_data)
            self._rbac.create_permission(perm)

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        self.state = ModuleState.INITIALIZED
        logger.info(f"Authentication module initialized with {len(self._backends)} backends")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("Authentication module started")

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self.state = ModuleState.STOPPED
        logger.info("Authentication module stopped")

    async def cleanup(self) -> None:
        await self.stop()
        self._backends.clear()
        self._users.clear()
        self._sessions.clear()
        self._tokens.clear()
        self._api_keys.clear()
        self._password_reset_tokens.clear()
        self._magic_link_tokens.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("Authentication module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "authentication",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "users": len(self._users),
            "active_sessions": len([s for s in self._sessions.values() if s.is_active]),
            "active_tokens": len([t for t in self._tokens.values() if t.is_valid()]),
            "api_keys": len(self._api_keys),
            "backends": len(self._backends)
        }

    async def _create_backend(self, provider: AuthProvider, config: Dict[str, Any]) -> None:
        if not config.get("enabled", True):
            return

        if provider == AuthProvider.LOCAL:
            self._backends[provider] = LocalAuthBackend()
        elif provider in (AuthProvider.OAUTH2, AuthProvider.OIDC):
            self._backends[provider] = OAuth2Backend(config)
        else:
            logger.warning(f"Backend {provider.value} not implemented")
            return

        await self._backends[provider].initialize(self._runtime, config)

    # User Management
    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        provider: AuthProvider = AuthProvider.LOCAL,
        **kwargs
    ) -> User:
        """Register new user."""
        backend = self._backends.get(provider)
        if not backend:
            raise ValueError(f"Provider {provider.value} not available")

        user = User(
            username=username,
            email=email,
            **kwargs
        )

        user = await backend.create_user(user, password)
        self._users[user.user_id] = user
        return user

    async def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    async def update_user(self, user: User) -> User:
        backend = self._backends.get(AuthProvider.LOCAL)
        if backend:
            user = await backend.update_user(user)
        self._users[user.user_id] = user
        return user

    async def delete_user(self, user_id: str) -> bool:
        # Revoke all sessions and tokens
        await self.revoke_all_sessions(user_id)
        await self.revoke_all_tokens(user_id)

        # Delete from backends
        for backend in self._backends.values():
            await backend.delete_user(user_id)

        self._users.pop(user_id, None)
        return True

    # Authentication
    async def authenticate(
        self,
        credentials: Dict[str, Any],
        provider: AuthProvider = AuthProvider.LOCAL
    ) -> Optional[User]:
        """Authenticate user."""
        backend = self._backends.get(provider)
        if not backend:
            raise ValueError(f"Provider {provider.value} not available")

        user = await backend.authenticate(credentials)
        if user:
            self._users[user.user_id] = user
        return user

    async def authenticate_with_token(self, token_str: str) -> Optional[User]:
        """Authenticate using JWT token."""
        token = self._jwt_manager.validate_token(token_str)
        if not token or not token.is_valid():
            return None

        # Check if token is revoked
        stored_token = self._tokens.get(token.token_id)
        if stored_token and stored_token.revoked:
            return None

        return self._users.get(token.user_id)

    async def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate using API key."""
        for key in self._api_keys.values():
            if key.verify_key(api_key):
                key.last_used_at = datetime.utcnow()
                key.usage_count += 1
                return self._users.get(key.user_id)
        return None

    # Session Management
    async def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
        expires_in: Optional[int] = None
    ) -> Session:
        """Create new session."""
        # Check session limit
        user_sessions = [s for s in self._sessions.values() if s.user_id == user_id and s.is_active]
        if len(user_sessions) >= self._max_sessions_per_user:
            # Remove oldest session
            oldest = min(user_sessions, key=lambda s: s.last_activity)
            oldest.is_active = False

        session = Session(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info or {},
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in or self._session_timeout)
        )

        self._sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.is_active and session.expires_at > datetime.utcnow():
            session.last_activity = datetime.utcnow()
            return session
        if session:
            session.is_active = False
        return None

    async def delete_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.is_active = False
            return True
        return False

    async def revoke_all_sessions(self, user_id: str) -> int:
        count = 0
        for session in self._sessions.values():
            if session.user_id == user_id and session.is_active:
                session.is_active = False
                count += 1
        return count

    # Token Management
    async def create_token(
        self,
        user_id: str,
        token_type: TokenType = TokenType.ACCESS,
        scopes: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
        claims: Optional[Dict[str, Any]] = None
    ) -> Token:
        """Create new token."""
        token = self._jwt_manager.create_token(
            user_id, token_type, scopes, expires_delta, claims
        )
        self._tokens[token.token_id] = token
        return token

    async def create_access_token(
        self,
        user_id: str,
        scopes: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
        session_id: Optional[str] = None
    ) -> Token:
        """Create access token."""
        claims = {"session_id": session_id} if session_id else {}
        return await self.create_token(user_id, TokenType.ACCESS, scopes, expires_delta, claims)

    async def create_refresh_token(
        self,
        user_id: str,
        expires_delta: Optional[timedelta] = None,
        session_id: Optional[str] = None
    ) -> Token:
        """Create refresh token."""
        claims = {"session_id": session_id} if session_id else {}
        return await self.create_token(user_id, TokenType.REFRESH, [], expires_delta, claims)

    async def revoke_token(self, token_id: str) -> bool:
        token = self._tokens.get(token_id)
        if token:
            token.revoked = True
            token.revoked_at = datetime.utcnow()
            return True
        return False

    async def revoke_all_tokens(self, user_id: str) -> int:
        count = 0
        for token in self._tokens.values():
            if token.user_id == user_id and not token.revoked:
                token.revoked = True
                token.revoked_at = datetime.utcnow()
                count += 1
        return count

    async def refresh_tokens(self, refresh_token_str: str) -> Optional[Tuple[Token, Token]]:
        """Refresh access token using refresh token."""
        refresh_token = self._jwt_manager.validate_token(refresh_token_str)
        if not refresh_token or refresh_token.token_type != TokenType.REFRESH:
            return None

        stored = self._tokens.get(refresh_token.token_id)
        if not stored or stored.revoked:
            return None

        # Create new access token
        access_token = await self.create_access_token(
            refresh_token.user_id,
            refresh_token.scopes,
            claims={"session_id": refresh_token.claims.get("session_id")}
        )

        # Optionally create new refresh token
        new_refresh = await self.create_refresh_token(refresh_token.user_id)

        # Revoke old refresh token
        await self.revoke_token(refresh_token.token_id)

        return access_token, new_refresh

    # API Key Management
    async def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: Optional[List[str]] = None,
        rate_limit: Optional[int] = None,
        ip_whitelist: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None
    ) -> Tuple[APIKey, str]:
        """Create API key. Returns (key_object, plain_key)."""
        # Generate key
        plain_key = f"ak_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        key_prefix = plain_key[:8]

        api_key = APIKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            user_id=user_id,
            scopes=scopes or [],
            rate_limit=rate_limit,
            ip_whitelist=ip_whitelist or [],
            expires_at=expires_at
        )

        self._api_keys[api_key.key_id] = api_key
        return api_key, plain_key

    async def get_api_key(self, key_id: str) -> Optional[APIKey]:
        return self._api_keys.get(key_id)

    async def list_api_keys(self, user_id: str) -> List[APIKey]:
        return [k for k in self._api_keys.values() if k.user_id == user_id]

    async def revoke_api_key(self, key_id: str) -> bool:
        key = self._api_keys.get(key_id)
        if key:
            key.is_active = False
            return True
        return False

    # Password Reset
    async def generate_password_reset_token(self, user_id: str, expires_in: int = 3600) -> str:
        """Generate password reset token."""
        token = secrets.token_urlsafe(32)
        self._password_reset_tokens[token] = (user_id, datetime.utcnow() + timedelta(seconds=expires_in))
        return token

    async def validate_password_reset_token(self, token: str) -> Optional[str]:
        """Validate password reset token. Returns user_id if valid."""
        entry = self._password_reset_tokens.get(token)
        if not entry:
            return None
        user_id, expires = entry
        if datetime.utcnow() > expires:
            del self._password_reset_tokens[token]
            return None
        return user_id

    async def consume_password_reset_token(self, token: str) -> Optional[str]:
        """Consume password reset token."""
        user_id = await self.validate_password_reset_token(token)
        if user_id:
            del self._password_reset_tokens[token]
        return user_id

    # Magic Links
    async def generate_magic_link(self, email: str, expires_in: int = 900) -> str:
        """Generate magic link token."""
        token = secrets.token_urlsafe(32)
        self._magic_link_tokens[token] = (email, datetime.utcnow() + timedelta(seconds=expires_in))
        return token

    async def validate_magic_link(self, token: str) -> Optional[str]:
        """Validate magic link token. Returns email if valid."""
        entry = self._magic_link_tokens.get(token)
        if not entry:
            return None
        email, expires = entry
        if datetime.utcnow() > expires:
            del self._magic_link_tokens[token]
            return None
        return email

    async def consume_magic_link(self, token: str) -> Optional[str]:
        email = await self.validate_magic_link(token)
        if email:
            del self._magic_link_tokens[token]
        return email

    # OAuth2 Flow
    def get_oauth2_authorize_url(
        self,
        provider: AuthProvider,
        redirect_uri: str,
        state: Optional[str] = None,
        scopes: Optional[List[str]] = None
    ) -> str:
        """Get OAuth2 authorization URL."""
        backend = self._backends.get(provider)
        if not backend or not isinstance(backend, OAuth2Backend):
            raise ValueError(f"OAuth2 backend not available for {provider.value}")

        params = {
            "client_id": backend.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or backend.scopes)
        }
        if state:
            params["state"] = state

        return f"{backend.authorize_url}?{urlencode(params)}"

    async def handle_oauth2_callback(
        self,
        provider: AuthProvider,
        code: str,
        redirect_uri: str,
        state: Optional[str] = None
    ) -> Optional[User]:
        """Handle OAuth2 callback."""
        backend = self._backends.get(provider)
        if not backend or not isinstance(backend, OAuth2Backend):
            raise ValueError(f"OAuth2 backend not available for {provider.value}")

        return await backend.authenticate({
            "code": code,
            "redirect_uri": redirect_uri
        })

    # RBAC
    def get_rbac(self) -> RBACManager:
        return self._rbac

    def check_permission(self, user_id: str, permission: str) -> bool:
        return self._rbac.check_permission(user_id, permission)

    def check_any_permission(self, user_id: str, permissions: List[str]) -> bool:
        return self._rbac.check_any_permission(user_id, permissions)

    def check_all_permissions(self, user_id: str, permissions: List[str]) -> bool:
        return self._rbac.check_all_permissions(user_id, permissions)

    # Cleanup
    async def _cleanup_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _cleanup_expired(self) -> None:
        """Clean up expired sessions, tokens, etc."""
        now = datetime.utcnow()

        # Clean sessions
        expired_sessions = [sid for sid, s in self._sessions.items() if s.expires_at < now]
        for sid in expired_sessions:
            del self._sessions[sid]

        # Clean tokens
        expired_tokens = [tid for tid, t in self._tokens.items() if t.expires_at and t.expires_at < now]
        for tid in expired_tokens:
            del self._tokens[tid]

        # Clean password reset tokens
        expired_resets = [t for t, (_, exp) in self._password_reset_tokens.items() if exp < now]
        for t in expired_resets:
            del self._password_reset_tokens[t]

        # Clean magic links
        expired_magic = [t for t, (_, exp) in self._magic_link_tokens.items() if exp < now]
        for t in expired_magic:
            del self._magic_link_tokens[t]

        logger.debug(f"Cleaned up {len(expired_sessions)} sessions, {len(expired_tokens)} tokens")

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        mapping = {
            "register": self.register_user,
            "get_user": self.get_user,
            "get_user_by_email": self.get_user_by_email,
            "get_user_by_username": self.get_user_by_username,
            "update_user": self.update_user,
            "delete_user": self.delete_user,
            "authenticate": self.authenticate,
            "authenticate_token": self.authenticate_with_token,
            "authenticate_api_key": self.authenticate_api_key,
            "create_session": self.create_session,
            "get_session": self.get_session,
            "delete_session": self.delete_session,
            "revoke_sessions": self.revoke_all_sessions,
            "create_access_token": self.create_access_token,
            "create_refresh_token": self.create_refresh_token,
            "refresh_tokens": self.refresh_tokens,
            "revoke_token": self.revoke_token,
            "revoke_all_tokens": self.revoke_all_tokens,
            "create_api_key": self.create_api_key,
            "get_api_key": self.get_api_key,
            "list_api_keys": self.list_api_keys,
            "revoke_api_key": self.revoke_api_key,
            "generate_reset_token": self.generate_password_reset_token,
            "validate_reset_token": self.validate_password_reset_token,
            "consume_reset_token": self.consume_password_reset_token,
            "generate_magic_link": self.generate_magic_link,
            "validate_magic_link": self.validate_magic_link,
            "consume_magic_link": self.consume_magic_link,
            "get_oauth2_url": self.get_oauth2_authorize_url,
            "handle_oauth2_callback": self.handle_oauth2_callback,
            "check_permission": self.check_permission,
            "check_any_permission": self.check_any_permission,
            "check_all_permissions": self.check_all_permissions,
        }
        if operation in mapping:
            return await mapping[operation](**kwargs)
        raise NotImplementedError(f"Operation '{operation}' not supported")


__all__ = [
    "AuthenticationModule",
    "AuthBackend",
    "LocalAuthBackend",
    "OAuth2Backend",
    "JWTManager",
    "RBACManager",
    "User",
    "Role",
    "Permission",
    "Session",
    "Token",
    "APIKey",
    "AuthProvider",
    "TokenType",
    "PermissionAction",
]