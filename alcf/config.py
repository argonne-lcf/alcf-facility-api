import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/facilityapi")
