import httpx
from datetime import datetime, timezone
from asyncache import cached
from cachetools import TTLCache
from typing import Dict, List
from json.decoder import JSONDecodeError
from uuid import uuid4

from app.routers.status.models import Status, IncidentType
from alcf.database.models import (
    Incident, Event, Resource
)

INFERENCE_STATUS_URL = "https://inference-api.alcf.anl.gov/resource_server/status"


# Create Incident and Event objects from the Inference Service status page
async def get_incident_event_from_status_url():
    """Create and return an Incident and Event objects from parsing an ALCF activity.json file."""

    # Record timestamp where the fetch/parse occured (in UTC, timezone-naive for database compatibility)
    current_datetime = datetime.now(timezone.utc).replace(tzinfo=None)

    # Fetch data from status URL
    try:
        # Get status from URL
        status_response: List[Dict[str, bool]] = await fetch_status(INFERENCE_STATUS_URL)

        # Extrac list of clusters that are up and down
        up_clusters = []
        down_clusters = []
        for cluster, is_up in status_response.items():
            (up_clusters if is_up else down_clusters).append(cluster)

        # Set status and description depending on the cluster statuses
        if len(up_clusters) > 0 and len(down_clusters) > 0:
            status = Status.degraded.value
            description = f"The following clusters are up: {up_clusters}. The following clusters are down: {down_clusters}."
        elif len(down_clusters) > 0:
            status = Status.down.value
            description = f"All clusters are down."
        elif len(up_clusters) > 0:
            status = Status.up.value
            description = f"All clusters are up."
        else:
            status = Status.unknown.value
            description = f"No cluster listed."
        incident_type = IncidentType.planned.value

    except Exception as e:
        status = Status.unknown.value
        description = "could not access status for the Inference Service."
        incident_type = IncidentType.unplanned.value
    
    # Create an incident database object
    try:
        incident_id = str(uuid4())
        incident = Incident(
            id=incident_id,
            name="Inference Service incident",
            short_name="inference_service_incident",
            description=description,
            last_updated=current_datetime,
            status=status,
            type=incident_type,
            start=current_datetime,
            end=datetime.now(timezone.utc).replace(tzinfo=None),
            resolution="completed"
        )
    except Exception as e:
        raise ValueError(f"Could not create incident: {e}")

    # Create an event database object
    try:
        event_id = str(uuid4())
        event = Event(
            id=event_id,
            name="Inference Service event",
            short_name="inference_service_event",
            description=description,
            last_updated=current_datetime,
            status=status,
            occurred_at=current_datetime
        )
    except Exception as e:
        raise ValueError(f"Could not create event: {e}")

    # Return the Incident and Event objects
    return incident, event


# Fetch an activity.json file from ALCF
@cached(TTLCache(maxsize=1024, ttl=60))
async def fetch_status(url) -> Dict[str, bool]:

    # Fetch and decode raw data from URL
    try:
        async with httpx.AsyncClient() as client:
            status_response = await client.get(url, timeout=5)
            status_response = status_response.json()
    except httpx.TimeoutException:
        raise TimeoutError("Request timed out while fetching inference service status data")
    except JSONDecodeError:
        raise ValueError("Could not decode inference service status response")
    except Exception as e:
        raise RuntimeError(f"Could not reach resource: {e}")
    
    # Validate input data
    if not isinstance(status_response, dict):
        raise ValueError(f"status response must be Dict[str, bool]")
    for key, value in status_response.items():
        if not isinstance(key, str) or not isinstance(value, bool):
            raise ValueError(f"status response must be Dict[str, bool]")
        
    # Return the validated activity response
    return status_response