from fastapi import APIRouter, HTTPException, Request, Query, Depends
import datetime
from . import models
from ...config import DATABASE_ENABLED
from ...database import get_db_session

router = APIRouter(
    prefix="/status",
    tags=["status"],
)


@router.get(
    "/resources",
    summary="Get all resources",
    description="Get a list of all resources at this facility. You can optionally filter the returned list by specifying attribtes."
)
async def get_resources(
    request : Request,
    name : str | None = None,
    description : str | None = None,
    group : str | None = None,
    offset : int | None = 0,
    limit : int | None = 100,
    updated_since : datetime.datetime | None = None,
    resource_type : models.ResourceType | None = None,
    session = Depends(get_db_session),
    ) -> list[models.Resource]:
    kwargs = {"session": session} if DATABASE_ENABLED else {}
    return await request.app.state.adapter.get_resources(offset, limit, name, description, group, updated_since, resource_type, **kwargs)


@router.get(
    "/resources/{resource_id}",
    summary="Get a specific resource",
    description="Get a specific resource for a given id"
)
async def get_resource(
    request : Request,
    resource_id : str,
    session = Depends(get_db_session),
    ) -> models.Resource:
    kwargs = {"session": session} if DATABASE_ENABLED else {}
    item = await request.app.state.adapter.get_resource(resource_id, **kwargs)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get(
    "/incidents",
    summary="Get all incidents without their events",
    description="Get a list of all incidents. Each incident will be returned without its events.  You can optionally filter the returned list by specifying attribtes."
)
async def get_incidents(
    request : Request,
    name : str | None = None,
    description : str | None = None,
    status : models.Status | None = None,
    type : models.IncidentType | None = None,
    from_ : datetime.datetime | None = Query(alias="from", default=None),
    time_ : datetime.datetime | None = Query(alias="time", default=None),
    to : datetime.datetime | None = None,
    updated_since : datetime.datetime | None = None,
    resource_id : str | None = None,
    offset : int | None = 0,
    limit : int | None = 100,
    session = Depends(get_db_session),
    ) -> list[models.Incident]:
    kwargs = {"session": session} if DATABASE_ENABLED else {}
    return await request.app.state.adapter.get_incidents(offset, limit, name, description, status, type, from_, to, time_, updated_since, resource_id, **kwargs)


@router.get(
    "/incidents/{incident_id}",
    summary="Get a specific incident and its events",
    description="Get a specific incident for a given id. The incident's events will also be included.  You can optionally filter the returned list by specifying attribtes."
)
async def get_incident(
    request : Request,
    incident_id : str,
    session = Depends(get_db_session),
    ) -> models.Incident:
    kwargs = {"session": session} if DATABASE_ENABLED else {}
    item = await request.app.state.adapter.get_incident(incident_id, **kwargs)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get(
    "/incidents/{incident_id}/events",
    summary="Get all events for an incident",
    description="Get a list of all events in this incident.  You can optionally filter the returned list by specifying attribtes."
)
async def get_events(
    request : Request,
    incident_id : str,
    resource_id : str | None = None,
    name : str | None = None,
    description : str | None = None,
    status : models.Status | None = None,
    from_ : datetime.datetime | None = Query(alias="from", default=None),
    time_ : datetime.datetime | None = Query(alias="time", default=None),
    to : datetime.datetime | None = None,
    offset : int | None = 0,
    limit : int | None = 100,
    updated_since : datetime.datetime | None = None,
    session = Depends(get_db_session),
    ) -> list[models.Event]:
    kwargs = {"session": session} if DATABASE_ENABLED else {}
    return await request.app.state.adapter.get_events(incident_id, offset, limit, resource_id, name, description, status, from_, to, time_, updated_since, **kwargs)


@router.get(
    "/incidents/{incident_id}/events/{event_id}",
    summary="Get a specific event",
    description="Get a specific event for a given id"
)
async def get_event(
    request : Request,
    incident_id : str,
    event_id : str,
    session = Depends(get_db_session),
    ) -> models.Event:
    kwargs = {"session": session} if DATABASE_ENABLED else {}
    item = await request.app.state.adapter.get_event(incident_id, event_id, **kwargs)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
