import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///alcf/facilityapi.db")

# Dev only
# TODO: Remove this once Auth is integrated
SECRET_DEV_KEY = os.getenv("SECRET_DEV_KEY", None)

# PBS GraphQL API URL
GRAPHQL_URL = os.getenv("GRAPHQL_URL", "")

# Keycloak integration
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", None)
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", None)
KEYCLOAK_REALM_NAME = os.getenv("KEYCLOAK_REALM_NAME", None)
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", None)
KEYCLOAK_AUTHORIZATION_ENDPOINT = os.getenv("KEYCLOAK_AUTHORIZATION_ENDPOINT", None)
KEYCLOAK_REDIRECT_URI = os.getenv("KEYCLOAK_REDIRECT_URI", None)
SESSION_MIDDLEWARE_SECRET_KEY = os.getenv("SESSION_MIDDLEWARE_SECRET_KEY", None)
