import os
import json
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Load ALCF endpoints data
_BASE_DIR = Path(__file__).parent.parent
_ENDPOINTS_FILE = _BASE_DIR / "alcf_endpoints.json"
if not _ENDPOINTS_FILE.exists():
    raise FileNotFoundError(f"Endpoints JSON file not found: {_ENDPOINTS_FILE}")
ALCF_ENDPOINTS = json.loads(_ENDPOINTS_FILE.read_text())

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://facilityapi_user@localhost/facilityapi_db")

# Dev only
# TODO: Remove this once Auth is integrated
SECRET_DEV_KEY = os.getenv("SECRET_DEV_KEY", None)

# PBS GraphQL
GRAPHQL_HTTPX_TRUST_ENV = os.getenv("GRAPHQL_HTTPX_TRUST_ENV", "True").lower() in ("true", "1", "t")

# Keycloak integration
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", None)
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", None)
KEYCLOAK_REALM_NAME = os.getenv("KEYCLOAK_REALM_NAME", None)
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", None)
KEYCLOAK_ENABLED = KEYCLOAK_CLIENT_ID is not None
KEYCLOAK_AUTHORIZED_USERNAMES = json.loads(os.getenv("KEYCLOAK_AUTHORIZED_USERNAMES", "[]"))

# Globus authorization
GLOBUS_SERVICE_API_CLIENT_ID = os.getenv("GLOBUS_SERVICE_API_CLIENT_ID", None)
GLOBUS_SERVICE_API_CLIENT_SECRET = os.getenv("GLOBUS_SERVICE_API_CLIENT_SECRET", None)
GLOBUS_HA_POLICY = os.getenv("GLOBUS_HA_POLICY", None)
GLOBUS_GROUP = os.getenv("GLOBUS_GROUP", None)
AUTHORIZED_IDP_DOMAIN = os.getenv("AUTHORIZED_IDP_DOMAIN", None)
GLOBUS_AUTHORIZED_USERNAMES = json.loads(os.getenv("GLOBUS_AUTHORIZED_USERNAMES", "[]"))

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# [TEMPORARY] - AmSC Demo
GLOBUS_AMSC_CLIENT_ID = os.getenv("GLOBUS_AMSC_CLIENT_ID", None)
GLOBUS_AMSC_CLIENT_SECRET = os.getenv("GLOBUS_AMSC_CLIENT_SECRET", None)
GLOBUS_AMSC_AUTHORIZED_USERNAMES = json.loads(os.getenv("GLOBUS_AMSC_AUTHORIZED_USERNAMES", "[]"))