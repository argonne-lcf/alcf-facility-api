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

# Keycloak integration
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", None)
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", None)
KEYCLOAK_REALM_NAME = os.getenv("KEYCLOAK_REALM_NAME", None)

# Globus Compute
GLOBUS_COMPUTE_FUNCTIONS = json.loads(os.getenv("GLOBUS_COMPUTE_FUNCTIONS", "{}"))
GLOBUS_COMPUTE_ENDPOINTS = json.loads(os.getenv("GLOBUS_COMPUTE_ENDPOINTS", "{}"))
