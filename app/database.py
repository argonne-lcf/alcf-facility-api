from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_ENABLED, DATABASE_URL

# First assume database support is disabled
async_engine = None
AsyncSessionLocal = None

# If database support is enabled, create the engine and session factory
if DATABASE_ENABLED:

    # Define async database engine
    async_engine = create_async_engine(
        DATABASE_URL, 
        echo=True,
        future=True  # Ensures SQLAlchemy 2.0+ behavior
    )

    # Define async database session factory
    AsyncSessionLocal = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

# Function to get a database session for each FastAPI request
async def get_db_session():
    if DATABASE_ENABLED:
        async with AsyncSessionLocal() as session:
            yield session
    else:
        yield None
        return