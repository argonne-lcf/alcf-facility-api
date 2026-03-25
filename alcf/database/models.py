from sqlmodel import SQLModel, Field, JSON
from enum import Enum
from sqlalchemy import Column, DateTime
from typing import List, Optional
from datetime import datetime, timezone

# API component enumeration
class FilesystemSubmitMethods(str, Enum):
    GLOBUS_COMPUTE = "globus_compute"
    GLOBUS_TRANSFER = "globus_transfer"

class NamedObject(SQLModel):
    """Base class for all named objects with common fields."""
    id: str = Field(primary_key=True, index=True)
    name: Optional[str] = None
    short_name: Optional[str] = None
    description: Optional[str] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Facility(NamedObject, table=True):
    """Facility entity."""
    organization_name: Optional[str] = None
    support_uri: Optional[str] = None
    site_ids: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

class Site(NamedObject, table=True):
    """Site entity."""
    operating_organization: Optional[str] = None
    country_name: Optional[str] = None
    locality_name: Optional[str] = None
    state_or_province_name: Optional[str] = None
    street_address: Optional[str] = None
    unlocode: Optional[str] = None
    altitude: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    resource_ids: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

class Incident(NamedObject, table=True):
    """Incident entity."""
    status: str
    type: str
    start: datetime
    end: Optional[datetime] = None
    resolution: str
    event_ids: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    resource_ids: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

class Event(NamedObject, table=True):
    """Event entity."""
    status: str
    occurred_at: datetime
    resource_id: str
    incident_id: str

class Resource(NamedObject, table=True):
    """Resource entity."""
    type: str
    group: Optional[str] = None
    current_status: str
    last_event_id: Optional[str] = None
    last_verified: Optional[datetime] = None
    site_id: str
    capability_ids: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

class User(SQLModel, table=True):
    """User entity."""
    id: str = Field(primary_key=True, index=True)
    name: Optional[str] = None
    username: Optional[str] = None
    idp_id: Optional[str] = None
    idp_name: Optional[str] = None
    auth_service: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Task(SQLModel, table=True):
    """Task entity."""
    id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True)  # Foreign key to User
    status: str = Field(default="pending")  # pending, active, completed, failed, canceled
    result: Optional[str] = None
    task_command: str = Field(sa_column=Column(JSON))  # Store TaskCommand as JSON string
    globus_endpoint_id: Optional[str] = None
    globus_function_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class AccessLog(SQLModel, table=True):
    """Access log entry"""
    id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    responded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    api_route: str
    origin_ip: str
    status_code: int
    error: Optional[float] = None

class ComputeLog(SQLModel, table=True):
    """Compute submit log entry"""
    id: str = Field(primary_key=True, index=True)
    access_log_id: str = Field(index=True)
    resource_id: str = Field(index=True)
    input: str = Field(sa_column=Column(JSON))
    result: Optional[str] = None
    alcf_username: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    responded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))