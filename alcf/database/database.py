from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND
from typing import List
from contextlib import asynccontextmanager
from . import models as db_models
from alcf.config import DATABASE_URL


engine = create_async_engine(
    DATABASE_URL, 
    echo=True,
    future=True  # Ensures SQLAlchemy 2.0+ behavior
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


# Function to add an entry to the database
async def add_to_db(data: dict, db_model_class):
    async with get_db_session_context() as session:
        try:
            object_db = db_model_class(**data)
            session.add(object_db)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise ValueError(f"Error creating database object: {e}")


# Function to update an existing entry to the database
async def update_db(data: dict, db_model_class):
    async with get_db_session_context() as session:
        try:
            # Find the existing object
            stmt = select(db_model_class).where(db_model_class.id == data['id'])
            result = await session.execute(stmt)
            existing_obj = result.scalar_one_or_none()
            
            if existing_obj is None:
                raise ValueError(f"Object with id '{data['id']}' not found")
            
            # Update the object with new data
            for key, value in data.items():
                if hasattr(existing_obj, key):
                    setattr(existing_obj, key, value)
            
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise ValueError(f"Error updating database object: {e}")

# =======================================
# ===== Get single database objects =====
# =======================================

# Function to extract a single database entry from its id
async def get_db_object_from_id(id, db_model_class):
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

# Function to extract a single location entry from its id
async def get_db_location_from_id(id) -> db_models.Location:
    return await get_db_object_from_id(id, db_models.Location)

# Function to extract a single incident entry from its id
async def get_db_incident_from_id(id) -> db_models.Incident:
    return await get_db_object_from_id(id, db_models.Incident)

# Function to extract a single event entry from its id
async def get_db_event_from_id(id) -> db_models.Event:
    return await get_db_object_from_id(id, db_models.Event)

# ========================================
# ===== Get list of database objects =====
# ========================================

# Function to extract multiple database entries by list of IDs (or all if no IDs provided)
async def get_db_objects(
    db_model_class, 
    ids: List[str] = None, 
    name: str = None, 
    description: str = None,
    group: str = None,
    offset: int = None,
    limit: int = None,
    resource_type: str = None,
    status: str = None,
    type: str = None
    ):
    async with get_db_session_context() as session:
        try:
            stmt = select(db_model_class)
            if ids:
                stmt = stmt.where(db_model_class.id.in_(ids))
            if name:
                stmt = stmt.where(db_model_class.name == name)
            if description:
                stmt = stmt.where(db_model_class.description == description)
            if group:
                stmt = stmt.where(db_model_class.group == group)
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
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving database objects: {e}")

# Function to extract a list of facility entries from a list of IDs (or all if no IDs provided)
async def get_db_facilities(ids: List[str] = None) -> List[db_models.Facility]:
    return await get_db_objects(db_models.Facility, ids)

# Function to extract a list of resource entries from a list of IDs (or all if no IDs provided)
async def get_db_resources(
    ids: List[str] = None, 
    name: str = None, 
    description: str = None,
    group: str = None,
    offset: int = None,
    limit: int = None,
    resource_type: str = None
    ) -> List[db_models.Resource]:
    return await get_db_objects(
        db_models.Resource, 
        ids=ids,
        name=name, 
        description=description, 
        group=group,
        offset=offset,
        limit=limit,
        resource_type=resource_type
    )

# Function to extract a list of site entries from a list of IDs (or all if no IDs provided)
async def get_db_sites(
    ids: List[str] = None, 
    offset: int = None, 
    limit: int = None
    ) -> List[db_models.Site]:
    return await get_db_objects(
        db_models.Site, 
        ids=ids, 
        offset=offset, 
        limit=limit
    )

# Function to extract a list of location entries from a list of IDs (or all if no IDs provided)
async def get_db_locations(
    ids: List[str] = None, 
    offset: int = None, 
    limit: int = None
    ) -> List[db_models.Location]:
    return await get_db_objects(
        db_models.Location, 
        ids=ids, 
        offset=offset, 
        limit=limit
    )

# Function to extract a list of incident entries from a list of IDs (or all if no IDs provided)
async def get_db_incidents(
    ids: List[str] = None, 
    offset: int = None, 
    limit: int = None,
    name: str = None,
    description: str = None,
    status: str = None,
    type: str = None
    ) -> List[db_models.Incident]:
    return await get_db_objects(
        db_models.Incident, 
        ids=ids, 
        offset=offset, 
        limit=limit,
        name=name,
        description=description,
        status=status,
        type=type
    )

# Function to extract a list of event entries from a list of IDs (or all if no IDs provided)
async def get_db_events(
    ids: List[str] = None, 
    offset: int = None, 
    limit: int = None,
    name: str = None,
    description: str = None,
    status: str = None
    ) -> List[db_models.Event]:
    return await get_db_objects(
        db_models.Event, 
        ids=ids, 
        offset=offset, 
        limit=limit,
        name=name,
        description=description,
        status=status
    )
