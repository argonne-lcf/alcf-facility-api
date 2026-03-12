import asyncio
import datetime
from fastapi import HTTPException, Query
from starlette.status import HTTP_304_NOT_MODIFIED, HTTP_400_BAD_REQUEST, HTTP_501_NOT_IMPLEMENTED
from app.routers.status.facility_adapter import FacilityAdapter as StatusFacilityAdapter

# Typing
from typing import List
from app.routers.status import models as status_models
from alcf.database import models as db_models
from app.types.models import Capability

# Safety net to recover resource status
from alcf.database.ingestion.ingest_activity_data import ingest_activity_data_for_resource
from alcf.database.database import get_db_session_context

# Functions to extract objects from the database
from alcf.database.database import (
    get_db_resources,
    get_db_incidents,
    get_db_events,
    get_db_resource_from_id,
    get_db_incident_from_id,
    get_db_event_from_id
)


class AlcfAdapter(StatusFacilityAdapter):
    """Facility adapter definition for the Status component of the IRI Facility API."""

    # Get resources
    async def get_resources(
        self : "AlcfAdapter",
        offset: int,
        limit: int,
        name: str | None = None,
        description: str | None = None,
        group: str | None = None,
        modified_since: datetime.datetime | None = None,
        resource_type: status_models.ResourceType | None = None,
        current_status: status_models.Status | None = None,
        capability: Capability | None = None,
        site_id: str | None = None,
        ) -> list[status_models.Resource]:
        """Update and return all resources from the database."""

        # Error for unsupported filters
        if site_id:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'site_id' not supported yet.")

        # Gather resources from database with filters
        resources = await get_db_resources(
            name=name,
            description=description,
            group=group,
            modified_since=modified_since,
            offset=offset,
            limit=limit,
            resource_type=resource_type.value if resource_type else None,
            current_status=current_status.value if current_status else None
        )

        # Update resources if needed
        resources = await asyncio.gather(*[self.__update_resource_if_needed(resource) for resource in resources])   

        # Format resources into IRI specification and return
        return [self.__format_resource(resource) for resource in resources]


    # Get resource
    async def get_resource(
        self : "AlcfAdapter",
        id : str
        ) -> status_models.Resource:
        """Return the resource object tied to a given resource ID."""
        resource = await get_db_resource_from_id(id)
        resource = await self.__update_resource_if_needed(resource) # Backup if cron job failed    
        return self.__format_resource(resource)


    # Get events
    async def get_events(
        self : "AlcfAdapter",
        offset: int,
        limit: int,
        incident_id: str | None = None,
        resource_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        status: status_models.Status | None = None,
        from_: datetime.datetime | None = None,
        to: datetime.datetime | None = None,
        time_: datetime.datetime | None = None,
        modified_since: datetime.datetime | None = None,
        ) -> list[status_models.Event]:
        """Return all events from the database."""

        # Error for unsupported filters
        if from_:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'from' filter not supported yet.")
        if to:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'to' filter not supported yet.")
        if time_:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'time' filter not supported yet.")

        # Get incident from database
        if incident_id:
            incident = await get_db_incident_from_id(incident_id)
            event_ids = incident.event_ids
        else:
            event_ids = None

        # Gather events from database with filters
        events = await get_db_events(
            ids=event_ids,
            offset=offset,
            limit=limit,
            name=name,
            description=description,
            status=status.value if status else None,
            modified_since=modified_since,
        )

        # Filter based on resource ID
        if resource_id:
            events = [event for event in events if event.resource_id == resource_id]

        # Format events into IRI specification and return
        return [self.__format_event(event) for event in events]

    
    # Get event
    async def get_event(
        self : "AlcfAdapter",
        id : str
        ) -> status_models.Event:
        """Return the event object tied to a given event ID."""

        # Get event from database
        event = await get_db_event_from_id(id)

        # Format event into IRI specification and return
        return self.__format_event(event)


    # Get incidents
    async def get_incidents(
        self : "AlcfAdapter",
        offset: int,
        limit: int,
        name: str | None = None,
        description: str | None = None,
        status: status_models.Status | None = None,
        type_: status_models.IncidentType | None = None,
        from_: datetime.datetime | None = None,
        to: datetime.datetime | None = None,
        time_: datetime.datetime | None = None,
        modified_since: datetime.datetime | None = None,
        resource_id: str | None = None,
        resolution: status_models.Resolution | None = None,
        ) -> list[status_models.Incident]:
        """Return all incidents from the database."""

        # Error for unsupported filters
        if from_:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'from' filter not supported yet.")
        if to:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'to' filter not supported yet.")
        if time_:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'time' filter not supported yet.")

        # Gather incidents from database with filters
        incidents = await get_db_incidents(
            offset=offset,
            limit=limit,
            name=name,
            description=description,
            status=status.value if status else None,
            type=type_.value if type_ else None,
            resolution=resolution.value if resolution else None,
            modified_since=modified_since,
        )

        # Filter based on resource ID
        if resource_id:
            incidents = [incident for incident in incidents if resource_id in incident.resource_ids]

        # Format incidents into IRI specification and return
        return [self.__format_incident(incident) for incident in incidents]

    
    # Get incident
    async def get_incident(
        self : "AlcfAdapter",
        id : str
        ) -> status_models.Incident:
        """Return the incident object tied to a given incident ID."""
        incident = await get_db_incident_from_id(id)
        return self.__format_incident(incident)


    # Format resource
    def __format_resource(self, db_resource: db_models.Resource) -> status_models.Resource:
        """Format a database resource object into a pydantic resource object."""
        return status_models.Resource(
            id=db_resource.id,
            name=db_resource.name,
            description=db_resource.description,
            last_modified=db_resource.last_updated,
            current_status=db_resource.current_status,
            capability_ids=[],
            group=db_resource.group,
            resource_type=db_resource.type,
            site_id=db_resource.site_id,
        )

    # Format incident
    def __format_incident(self, db_incident: db_models.Incident) -> status_models.Incident:
        """Format a database incident object into a pydantic incident object."""
        return status_models.Incident(
            id=db_incident.id,
            name=db_incident.name,
            description=db_incident.description,
            last_modified=db_incident.last_updated,
            start=db_incident.start,
            end=db_incident.end,
            status=db_incident.status,
            type=db_incident.type,
            resolution=db_incident.resolution,
            event_ids=db_incident.event_ids,
            resource_ids=db_incident.resource_ids,
        )

    # Format event
    def __format_event(self, db_event: db_models.Event) -> status_models.Event:
        """Format a database event object into a pydantic event object."""
        return status_models.Event(
            id=db_event.id,
            name=db_event.name,
            description=db_event.description,
            last_modified=db_event.last_updated,
            status=db_event.status,
            occurred_at=db_event.occurred_at,
            resource_id=db_event.resource_id,
            incident_id=db_event.incident_id,
        )


    # ---------------------------
    #  Private utility functions
    # ---------------------------

    # Update resource if needed
    async def __update_resource_if_needed(self, resource: db_models.Resource) -> db_models.Resource:
        """Update the resource manually if the ingestiong cron job failed."""

        # If the resource status has not been verified in the last 2 minutes ...
        current_datetime = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        if resource.last_verified is None or (current_datetime - resource.last_verified).total_seconds() > 120:

            # Update the resource manually
            async with get_db_session_context() as db_session:
                _, _, resource = await ingest_activity_data_for_resource(resource.id, db_session)

        # Return the original resource object or the updated one
        return resource

    # Remove not modified
    def __remove_not_modified(self, obj_list: List, if_modified_since: str) -> List:
        """Only include an object if it was modified since the if_modified_since date string."""
        objs = []
        for obj in obj_list:
            if self.__is_modified_since(timestamp=obj.last_updated, if_modified_since=if_modified_since):
                objs.append(obj)
        return objs


    # Is modified since
    def __is_modified_since(self, timestamp: datetime = None, if_modified_since: str = None):
        """Return True if the timestamp is later than if_modified_since datetime string."""

        # Return True if no input if_modified_since string was provided
        if if_modified_since is None:
            return True

        # Try to convert the if_modified_since string into a datetime object
        # If the datetime doesn't have timezone info, assume it's UTC
        try:
            input_datetime = datetime.datetime.fromisoformat(if_modified_since)
            if input_datetime.tzinfo is None:
                input_datetime = input_datetime.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            error_message = "Invalid isoformat for 'if_modified_since' string."
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=error_message)
        
        # Return whether the timestamp is later than if_modified_since
        return timestamp > input_datetime


    # Check if modified
    def __check_if_modified(self, timestamp: datetime = None, if_modified_since: str = None, object_name: str = None):
        """Raise an error if the timestamp is earlier than the if_modified_since data."""

        # Raise an error if the object was not modified
        if not self.__is_modified_since(timestamp=timestamp, if_modified_since=if_modified_since):
            error_message = f"The requested {object_name} was not modified."
            raise HTTPException(status_code=HTTP_304_NOT_MODIFIED, detail=error_message)
    