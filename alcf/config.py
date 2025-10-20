import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///alcf/facilityapi.db")

# Dev only
# TODO: Remove this once Auth is integrated
SECRET_DEV_KEY = os.getenv("SECRET_DEV_KEY", None)