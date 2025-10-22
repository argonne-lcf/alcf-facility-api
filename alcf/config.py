import os

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
