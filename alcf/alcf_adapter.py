import asyncio
import datetime
from fastapi import HTTPException
from starlette.status import HTTP_304_NOT_MODIFIED, HTTP_400_BAD_REQUEST
from app.routers.status.facility_adapter import FacilityAdapter as StatusFacilityAdapter

# Typing
from typing import List
from app.routers.status import models as status_models
from alcf.database import models as db_models

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
    """Facility adapter definition for the IRI Facility API."""
    FACILITY_ID = "8da81144-304b-4fd0-b2fe-eda33bb38720"

    # Get resources
    async def get_resources(
        self : "AlcfAdapter",
        offset : int,
        limit : int,
        name : str | None = None,
        description : str | None = None,        
        group : str | None = None,
        updated_since : datetime.datetime | None = None,
        resource_type : status_models.ResourceType | None = None,
        ids: List[str] | None = None, # Addition from FacilityAdapter
        ) -> list[status_models.Resource]:
        """Update and return all resources from the database."""
        resources = await get_db_resources(ids=ids)
        resources = await asyncio.gather(*[self.__update_resource_if_needed(resource) for resource in resources])
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
        incident_id : str,
        offset : int,
        limit : int,
        resource_id : str | None = None,
        name : str | None = None,
        description : str | None = None,
        status : status_models.Status | None = None,
        from_ : datetime.datetime | None = None,
        to : datetime.datetime | None = None,
        time : datetime.datetime | None = None,
        updated_since : datetime.datetime | None = None,
        ids: List[str] | None = None, # Addition from FacilityAdapter
        ) -> list[status_models.Event]:
        """Return all events from the database."""
        events = await get_db_events(ids=ids)
        return [self.__format_event(event) for event in events]

    
    # Get event
    async def get_event(
        self : "AlcfAdapter",
        incident_id : str,
        id : str
        ) -> status_models.Event:
        """Return the event object tied to a given event ID."""

        # Get event from database
        event = await get_db_event_from_id(id)

        # Make sure the event belongs to the incident
        if event.incident_id != incident_id:
            raise HTTPException(status_code=404, detail=f"Event not found for Incident {incident_id}.")

        # Format and return data
        return self.__format_event(event)


    # Get incidents
    async def get_incidents(
        self : "AlcfAdapter",
        offset : int,
        limit : int,
        name : str | None = None,
        description : str | None = None,
        status : status_models.Status | None = None,
        type : status_models.IncidentType | None = None,
        from_ : datetime.datetime | None = None,
        to : datetime.datetime | None = None,
        time_ : datetime.datetime | None = None,
        updated_since : datetime.datetime | None = None,
        resource_id : str | None = None,
        ids: List[str] | None = None, # Addition from FacilityAdapter
        ) -> list[status_models.Incident]:
        """Return all incidents from the database."""
        incidents = await get_db_incidents(ids=ids)
        return [self.__format_incident(incident) for incident in incidents]

    
    # Get incident
    async def get_incident(
        self : "AlcfAdapter",
        id : str
        ) -> status_models.Incident:
        """Return the incident object tied to a given incident ID."""
        incident = await get_db_incident_from_id(id)
        return self.__format_incident(incident)


    # --------------------
    #  Get related objects
    # --------------------

    # Get resource by event
    #async def get_resource_by_event(self, event_id: str, str = None) -> status_models.Resource:
    #    """Return the resource object associated with the specified event id via the impacts relationship."""
    #    event = await get_db_event_from_id(event_id)
    #    resource = await get_db_resource_from_id(event.resource_id)
    #    return self.__format_resource(resource)

    # Get incident by event
    #async def get_incident_by_event(self, event_id: str, db_session: AsyncSession, if_modified_since: str = None) -> Incident:
    #    """Return the incident object associated with the specified event id via the generatedBy relationship."""
    #    event = await get_db_event_from_id(event_id, db_session)
    #    return await self.get_incident(event.incident_id, db_session)

    # Get location by site
    #async def get_location_by_site(self, site_id: str, db_session: AsyncSession, if_modified_since: str = None) -> Location:
    #    """Return the location object tied to a given site."""
    #    site = await get_db_site_from_id(site_id, db_session)
    #    return await self.get_location(site.location_id, db_session)

    # Get resources by site
    #async def get_resources_by_site(self, site_id: str, db_session: AsyncSession, if_modified_since: str = None) -> List[Resource]:
    #    """Return list of resource objects tied to a given site."""
    #    #TODO: check for updates needed
    #    site = await get_db_site_from_id(site_id, db_session)
    #    return await self.get_resources(db_session, if_modified_since, ids=site.resource_ids)

    # Get events by incident
    #async def get_events_by_incident(self, incident_id: str, db_session: AsyncSession, if_modified_since: str = None) -> List[Event]:
    #    """Return list of event objects tied to a given incident."""
    #    incident = await get_db_incident_from_id(incident_id, db_session)
    #    return await self.get_events(db_session, if_modified_since, ids=incident.event_ids)

    # Get resources by incident
    #async def get_resources_by_incident(self, incident_id: str, db_session: AsyncSession, if_modified_since: str = None) -> List[Resource]:
    #    """Return list of resource objects tied to a given incident."""
    #    #TODO: check for updates needed
    #    incident = await get_db_incident_from_id(incident_id, db_session)
    #    return await self.get_resources(db_session, if_modified_since, ids=incident.resource_ids)

    # --------------------------------------
    #  Private frontend formatting functions
    # --------------------------------------

    # Format site
    #def __format_site(self, db_site: db_models.Site) -> status_models.Site:
    #    """Format a database site object into a pydantic site object."""
    #
    #    # Build data structure from pydantic model
    #    return status_models.Site(
    #        id=db_site.id,
    #        name=db_site.name,
    #        description=db_site.description,
    #        last_modified=db_site.last_modified,
    #        operating_organization=db_site.operating_organization
    #    )

    # Format location
    #def __format_location(self, db_location: db_models.Location) -> status_models.Location:
    #    """Format a database location object into a pydantic location object."""
    #
    #    # Build data structure from pydantic model
    #    return status_models.Location(
    #        id=db_location.id,
    #        name=db_location.name,
    #        description=db_location.description,
    #        last_modified=db_location.last_modified,
    #        country_name=db_location.country_name,
    #        locality_name=db_location.locality_name,
    #        state_or_province_name=db_location.state_or_province_name,
    #        street_address=db_location.street_address,
    #        unlocode=db_location.unlocode
    #    )

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
            resource_type=db_resource.type
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
        if (current_datetime - resource.last_verified).total_seconds() > 120:

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
    