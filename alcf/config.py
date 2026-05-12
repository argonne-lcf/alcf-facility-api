import json
from pathlib import Path
from typing import Optional, List, Dict
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from alcf.enums import APIComponent

load_dotenv()


# Database
class DatabaseSettings(BaseSettings):
    """Database configuration."""

    # Optional
    url: Optional[str] = Field(default="sqlite+aiosqlite:///alcf/facilityapi.db")
    sql_echo: Optional[bool] = Field(default=False)

    # Prefix of environment variables
    class Config(SettingsConfigDict):
        env_prefix = "DATABASE_"


# Keycloak
class KeycloakSettings(BaseSettings):
    """Keycloak integration configuration."""

    # Mandatory
    realm_name: str
    server_url: str
    impersonation_service_client_id: str
    impersonation_service_client_secret: str
    pbs_graphql_audience: str

    # Optional
    enabled: Optional[bool] = Field(default=True)
    authorized_usernames: Optional[List[str]] = Field(default_factory=list)
    
    @field_validator("server_url", mode="before")
    @classmethod
    def normalize_server_url(cls, v: str) -> str:
        """Remove trailing slash from server URL to avoid double slashes."""
        if isinstance(v, str):
            return v.rstrip("/")
        return v
    
    # Prefix of environment variables
    class Config(SettingsConfigDict):
        env_prefix = "KEYCLOAK_"


# Globus
class GlobusSettings(BaseSettings):
    """Globus authorization configuration."""

    # Mandatory
    service_api_client_id: str
    service_api_client_secret: str
    ha_policy: str

    # Optional
    group: Optional[str] = Field(default=None)
    authorized_usernames: Optional[List[str]] = Field(default_factory=list)

    # Prefix of environment variables
    class Config(SettingsConfigDict):
        env_prefix = "GLOBUS_"


# Redis
class RedisSettings(BaseSettings):
    """Redis cache configuration."""

    # Optional
    host: Optional[str] = Field(default="localhost")
    port: Optional[int] = Field(default=6379, ge=1, le=9999)

    # Prefix of environment variables
    class Config(SettingsConfigDict):
        env_prefix = "REDIS_"


class AlcfSettings(BaseSettings):
    """Main ALCF application settings."""

    # Grouped variables with a prefix
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    keycloak: KeycloakSettings = Field(default_factory=KeycloakSettings)
    globus: GlobusSettings = Field(default_factory=GlobusSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)

    # Other variables without a prefix
    graphql_httpx_trust_env: bool = Field(default=True)
    authorized_idp_domain: str
    component_maintenance_notices: Optional[Dict[APIComponent, str]] = None
    task_timeout_sec: Optional[int] = 600
    env: Optional[str] = Field(default="development")

    # Load from .env file
    class Config(SettingsConfigDict):
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# ALCF endpoints Json configuration
def _load_endpoints() -> dict:
    """Load ALCF endpoints from JSON file."""
    base_dir = Path(__file__).parent.parent
    endpoints_file = base_dir / "alcf_endpoints.json"
    if not endpoints_file.exists():
        raise FileNotFoundError(f"Endpoints JSON file not found: {endpoints_file}")
    return json.loads(endpoints_file.read_text())
ALCF_ENDPOINTS = _load_endpoints()

# Load and validate environment variables
settings = AlcfSettings()

# Assign variables
COMPONENT_MAINTENANCE_NOTICES = settings.component_maintenance_notices
DATABASE_URL = settings.database.url
DATABASE_SQL_ECHO = settings.database.sql_echo
KEYCLOAK_REALM_NAME = settings.keycloak.realm_name
KEYCLOAK_SERVER_URL = settings.keycloak.server_url
KEYCLOAK_ENABLED = settings.keycloak.enabled
KEYCLOAK_AUTHORIZED_USERNAMES = settings.keycloak.authorized_usernames
KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_ID = settings.keycloak.impersonation_service_client_id
KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_SECRET = settings.keycloak.impersonation_service_client_secret
KEYCLOAK_PBS_GRAPHQL_AUDIENCE = settings.keycloak.pbs_graphql_audience
GLOBUS_SERVICE_API_CLIENT_ID = settings.globus.service_api_client_id
GLOBUS_SERVICE_API_CLIENT_SECRET = settings.globus.service_api_client_secret
GLOBUS_HA_POLICY = settings.globus.ha_policy
GLOBUS_GROUP = settings.globus.group
GLOBUS_AUTHORIZED_USERNAMES = settings.globus.authorized_usernames
REDIS_HOST = settings.redis.host
REDIS_PORT = settings.redis.port
GRAPHQL_HTTPX_TRUST_ENV = settings.graphql_httpx_trust_env
AUTHORIZED_IDP_DOMAIN = settings.authorized_idp_domain
TASK_TIMEOUT_SEC = settings.task_timeout_sec
ENV = settings.env

# Log base path
if ENV == "development":
    LOG_BASE_PATH = Path("logs/")
else:
    LOG_BASE_PATH = Path("/var/log/alcf-facility-api/")
