from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, or_
from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
import datetime
from typing import List
from contextlib import asynccontextmanager
from . import models as db_models
from alcf.config import DATABASE_URL


engine = create_async_engine(
    DATABASE_URL, 
    echo=True,
    future=True,  # Ensures SQLAlchemy 2.0+ behavior
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,  # Connection pool size (adjust based on your needs)
    max_overflow=10  # Maximum overflow connections
)

AsyncSessionLocal = sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

@asynccontextmanager
async def get_db_session_context():
    """Context manager for independent database operations."""
    async with AsyncSessionLocal() as db_session:
        yield db_session 


# Function to check if an entry exists in the database
async def exists_in_db(id, db_model_class):
    async with get_db_session_context() as session:
        stmt = select(db_model_class).where(db_model_class.id == id).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

# Function to reject null bytes in strings
def _reject_null_bytes(*strings: str | None):
    """Raise 404 if any string contains a null byte (rejected by PostgreSQL UTF-8)."""
    for s in strings:
        if s and '\x00' in s:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"'{s}' not found."
            )


# ==================================================
# ===== Add and update single database objects =====
# ==================================================

# Function to add an entry to the database
async def add_to_db(data: dict, db_model_class):
    async with get_db_session_context() as session:
        try:
            object_db = db_model_class(**data)
            session.add(object_db)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating database object: {e}"
            )

# Function to update an existing entry to the database
async def update_db(data: dict, db_model_class):
    async with get_db_session_context() as session:
        try:
            # Find the existing object
            stmt = select(db_model_class).where(db_model_class.id == data['id'])
            result = await session.execute(stmt)
            existing_obj = result.scalar_one_or_none()
            
            if existing_obj is None:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=f"Object with id '{data['id']}' not found"
                )
            
            # Update the object with new data
            for key, value in data.items():
                if hasattr(existing_obj, key):
                    setattr(existing_obj, key, value)
            
            await session.commit()
        except HTTPException:
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating database object: {e}"
            )

# Function to add a single task entry
async def add_task_to_db(data: dict):
    await add_to_db(data, db_models.Task)

# Function to update a single task entry
async def update_task_in_db(data: dict):
    await update_db(data, db_models.Task)

# Function to add a single user entry
async def add_user_to_db(data: dict):
    await add_to_db(data, db_models.User)


# =======================================
# ===== Get single database objects =====
# =======================================

# Function to extract a single database entry from its id
async def get_db_object_from_id(id, db_model_class):
    _reject_null_bytes(id)
    async with get_db_session_context() as session:
        entry = await session.get(db_model_class, id)
        if entry is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"'{id}' not found.")
        await session.commit()
        return entry

# Function to extract a single facility entry from its id
async def get_db_facility_from_id(id) -> db_models.Facility:
    return await get_db_object_from_id(id, db_models.Facility)

# Function to extract a single resource entry from its id
async def get_db_resource_from_id(id) -> db_models.Resource:
    return await get_db_object_from_id(id, db_models.Resource)

# Function to extract a single site entry from its id
async def get_db_site_from_id(id) -> db_models.Site:
    return await get_db_object_from_id(id, db_models.Site)

# Function to extract a single incident entry from its id
async def get_db_incident_from_id(id) -> db_models.Incident:
    return await get_db_object_from_id(id, db_models.Incident)

# Function to extract a single event entry from its id
async def get_db_event_from_id(id) -> db_models.Event:
    return await get_db_object_from_id(id, db_models.Event)

# Function to extract a single user entry from its id
async def get_db_user_from_id(id) -> db_models.User:
    return await get_db_object_from_id(id, db_models.User)

# Function to extract a single task entry from its id
async def get_db_task_from_id(id) -> db_models.Task:
    return await get_db_object_from_id(id, db_models.Task)

# ========================================
# ===== Get list of database objects =====
# ========================================

# Function to extract multiple database entries by list of IDs (or all if no IDs provided)
async def get_db_objects(
    db_model_class, 
    ids: List[str] = None, 
    name: str = None, 
    short_name: str = None,
    description: str = None,
    group: str = None,
    modified_since: datetime.datetime | None = None,
    offset: int = None,
    limit: int = None,
    resource_type: str = None,
    status: str = None,
    type: str = None,
    current_status: str = None,
    site_id: str = None,
    resolution: str = None,
    from_: datetime.datetime | None = None,
    to: datetime.datetime | None = None,
    time_: datetime.datetime | None = None,
    ):
    _reject_null_bytes(
        *(ids or []),
        name,
        short_name,
        description,
        group,
        resource_type,
        status,
        type,
        current_status,
        site_id,
        resolution
    )
    if offset:
        offset = min(offset, 9000000000000000000)
    async with get_db_session_context() as session:
        try:
            stmt = select(db_model_class)
            if ids:
                stmt = stmt.where(db_model_class.id.in_(ids))
            if name:
                stmt = stmt.where(db_model_class.name == name)
            if short_name:
                stmt = stmt.where(db_model_class.short_name == short_name)
            if description:
                stmt = stmt.where(db_model_class.description == description)
            if group:
                stmt = stmt.where(db_model_class.group == group)
            if modified_since is not None and hasattr(db_model_class, "last_updated"):
                ms = modified_since
                if isinstance(ms, datetime.datetime) and ms.tzinfo is not None:
                    ms = ms.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                stmt = stmt.where(db_model_class.last_updated >= ms)
            if offset is not None:
                stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)
            if resource_type:
                stmt = stmt.where(db_model_class.type == resource_type)
            if type:
                stmt = stmt.where(db_model_class.type == type)
            if status:
                stmt = stmt.where(db_model_class.status == status)
            if current_status:
                stmt = stmt.where(db_model_class.current_status == current_status)
            if site_id:
                stmt = stmt.where(db_model_class.site_id == site_id)
            if resolution:
                stmt = stmt.where(db_model_class.resolution == resolution)
            if from_ is not None:
                ms = from_.astimezone(datetime.timezone.utc).replace(tzinfo=None) if from_.tzinfo else from_
                if hasattr(db_model_class, "start"):
                    stmt = stmt.where(db_model_class.start >= ms)
                elif hasattr(db_model_class, "occurred_at"):
                    stmt = stmt.where(db_model_class.occurred_at >= ms)
            if to is not None:
                ms = to.astimezone(datetime.timezone.utc).replace(tzinfo=None) if to.tzinfo else to
                if hasattr(db_model_class, "end"):
                    stmt = stmt.where(db_model_class.end.isnot(None), db_model_class.end < ms)
                elif hasattr(db_model_class, "occurred_at"):
                    stmt = stmt.where(db_model_class.occurred_at < ms)
            if time_ is not None:
                ms = time_.astimezone(datetime.timezone.utc).replace(tzinfo=None) if time_.tzinfo else time_
                if hasattr(db_model_class, "start") and hasattr(db_model_class, "end"):
                    stmt = stmt.where(db_model_class.start <= ms)
                    stmt = stmt.where(or_(db_model_class.end.is_(None), db_model_class.end > ms))
                elif hasattr(db_model_class, "occurred_at"):
                    stmt = stmt.where(db_model_class.occurred_at == ms)
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving database objects: {e}")

# Function to extract a list of facility entries from a list of IDs (or all if no IDs provided)
async def get_db_facilities(
    ids: List[str] = None,
    modified_since: datetime.datetime | None = None,
    ) -> List[db_models.Facility]:
    return await get_db_objects(
        db_models.Facility, 
        ids=ids,
        modified_since=modified_since
    )

# Function to extract a list of resource entries from a list of IDs (or all if no IDs provided)
async def get_db_resources(
    ids: List[str] = None, 
    name: str = None, 
    description: str = None,
    group: str = None,
    modified_since: datetime.datetime | None = None,
    offset: int = None,
    limit: int = None,
    resource_type: str = None,
    current_status: str = None,
    site_id: str = None
    ) -> List[db_models.Resource]:
    return await get_db_objects(
        db_models.Resource, 
        ids=ids,
        name=name, 
        description=description, 
        group=group,
        modified_since=modified_since,
        offset=offset,
        limit=limit,
        resource_type=resource_type,
        current_status=current_status,
        site_id=site_id
    )

# Function to extract a list of site entries from a list of IDs (or all if no IDs provided)
async def get_db_sites(
    ids: List[str] = None, 
    name: str = None, 
    short_name: str = None,
    offset: int = None, 
    limit: int = None,
    modified_since: datetime.datetime | None = None,
    ) -> List[db_models.Site]:
    return await get_db_objects(
        db_models.Site, 
        ids=ids, 
        offset=offset, 
        limit=limit,
        name=name,
        short_name=short_name,
        modified_since=modified_since,
    )

# Function to extract a list of incident entries from a list of IDs (or all if no IDs provided)
async def get_db_incidents(
    ids: List[str] = None, 
    offset: int = None, 
    limit: int = None,
    name: str = None,
    description: str = None,
    status: str = None,
    type: str = None,
    resolution: str = None,
    modified_since: datetime.datetime | None = None,
    from_: datetime.datetime | None = None,
    to: datetime.datetime | None = None,
    time_: datetime.datetime | None = None,
    ) -> List[db_models.Incident]:
    return await get_db_objects(
        db_models.Incident, 
        ids=ids, 
        offset=offset, 
        limit=limit,
        name=name,
        description=description,
        status=status,
        type=type,
        resolution=resolution,
        modified_since=modified_since,
        from_=from_,
        to=to,
        time_=time_,
    )

# Function to extract a list of event entries from a list of IDs (or all if no IDs provided)
async def get_db_events(
    ids: List[str] = None, 
    offset: int = None, 
    limit: int = None,
    name: str = None,
    description: str = None,
    status: str = None,
    modified_since: datetime.datetime | None = None,
    from_: datetime.datetime | None = None,
    to: datetime.datetime | None = None,
    time_: datetime.datetime | None = None,
    ) -> List[db_models.Event]:
    return await get_db_objects(
        db_models.Event, 
        ids=ids, 
        offset=offset, 
        limit=limit,
        name=name,
        description=description,
        status=status,
        modified_since=modified_since,
        from_=from_,
        to=to,
        time_=time_,
    )

# Function to extract a list of user entries from a list of IDs (or all if no IDs provided)
async def get_db_users(
    ids: List[str] = None, 
    offset: int = None, 
    limit: int = None
    ) -> List[db_models.User]:
    return await get_db_objects(
        db_models.User, 
        ids=ids, 
        offset=offset, 
        limit=limit
    )

# Function to extract tasks for a specific user
async def get_db_tasks_by_user(
    user_id: str,
    offset: int = None, 
    limit: int = None,
    status: str = None
    ) -> List[db_models.Task]:
    if offset:
        offset = min(offset, 9000000000000000000)
    async with get_db_session_context() as session:
        try:
            stmt = select(db_models.Task).where(db_models.Task.user_id == user_id)
            if status:
                stmt = stmt.where(db_models.Task.status == status)
            if offset is not None:
                stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)
            stmt = stmt.order_by(db_models.Task.created_at.desc())
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving tasks: {e}")
