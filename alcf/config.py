import os
import json

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://facilityapi_user@localhost/facilityapi_db")

# Dev only
# TODO: Remove this once Auth is integrated
SECRET_DEV_KEY = os.getenv("SECRET_DEV_KEY", None)

# PBS GraphQL API URL
GRAPHQL_URL = os.getenv("GRAPHQL_URL", "")
GRAPHQL_HTTPX_TRUST_ENV = os.getenv("GRAPHQL_URL", "True").lower() in ("true", "1", "t")

# Keycloak integration
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", None)
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", None)
KEYCLOAK_REALM_NAME = os.getenv("KEYCLOAK_REALM_NAME", None)

# Globus authorization
GLOBUS_SERVICE_API_CLIENT_ID = os.getenv("GLOBUS_SERVICE_API_CLIENT_ID", None)
GLOBUS_SERVICE_API_CLIENT_SECRET = os.getenv("GLOBUS_SERVICE_API_CLIENT_SECRET", None)
GLOBUS_HA_POLICY = os.getenv("GLOBUS_HA_POLICY", None)
GLOBUS_GROUP = os.getenv("GLOBUS_GROUP", None)
AUTHORIZED_IDP_DOMAIN = os.getenv("AUTHORIZED_IDP_DOMAIN", None)

# Globus Compute
GLOBUS_COMPUTE_FUNCTIONS = json.loads(os.getenv("GLOBUS_COMPUTE_FUNCTIONS", "{}"))
GLOBUS_COMPUTE_ENDPOINTS = json.loads(os.getenv("GLOBUS_COMPUTE_ENDPOINTS", "{}"))

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))