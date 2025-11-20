from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column
from typing import List, Optional
from datetime import datetime, timezone


class NamedObject(SQLModel):
    """Base class for all named objects with common fields."""
    id: str = Field(primary_key=True, index=True)
    name: Optional[str] = None
    short_name: Optional[str] = None
    description: Optional[str] = None
    last_updated: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

class Facility(NamedObject, table=True):
    """Facility entity."""
    organization_name: Optional[str] = None
    support_url: Optional[str] = None

class Site(NamedObject, table=True):
    """Site entity."""
    operating_organization: Optional[str] = None
    location_id: Optional[str] = None

class Location(NamedObject, table=True):
    """Location entity."""
    country_name: Optional[str] = None
    locality_name: Optional[str] = None
    state_or_province_name: Optional[str] = None
    street_address: Optional[str] = None
    unlocode: Optional[str] = None
    altitude: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

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
