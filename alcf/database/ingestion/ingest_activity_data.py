# Add the project root to Python path to enable absolute imports
import os
import sys
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
import argparse
from enum import Enum
from uuid import uuid4
from typing import List, Optional
from datetime import datetime, timezone
import httpx
from json.decoder import JSONDecodeError
from sqlalchemy import delete
from sqlmodel import SQLModel
from pydantic import BaseModel, ValidationError
from asyncache import cached
from cachetools import TTLCache
from alcf.database.models import (
    Incident, Event, Resource
)
from alcf.database.database import get_db_session_context, get_db_resource_from_id, engine
from app.routers.status.models import Status, IncidentType

# List of ALCF resource IDs
class ALCF_RESOURCE_ID_LIST(str, Enum):
    polaris = "55c1c993-1124-47f9-b823-514ba3849a9a"
    sophia = "9674c7e1-aecc-4dbb-bf01-c9197e027cd6"
    crux = "8b9b42f7-572a-4909-8472-a0453436304c"
    aurora = "0325fc07-6fb7-4453-b772-3d5030b2df72"
    edith = "7f7d0593-162e-43b9-8476-07d7d137d6ab"

# List of URLs to fetch activity.json files
class ALCF_RESOURCE_URLS(str, Enum):
    polaris = "https://status.alcf.anl.gov/polaris/activity.json"
    sophia = "https://status.alcf.anl.gov/sophia/activity.json"
    crux = "https://status.alcf.anl.gov/crux/activity.json"
    aurora = "https://status.alcf.anl.gov/aurora/activity.json"

# Map between ALCF resource IDs and activity.json URLs
ALCF_RESOURCE_ID_TO_URL = {
    ALCF_RESOURCE_ID_LIST.polaris.value: ALCF_RESOURCE_URLS.polaris.value,
    ALCF_RESOURCE_ID_LIST.sophia.value: ALCF_RESOURCE_URLS.sophia.value,
    ALCF_RESOURCE_ID_LIST.crux.value: ALCF_RESOURCE_URLS.crux.value,
    ALCF_RESOURCE_ID_LIST.aurora.value: ALCF_RESOURCE_URLS.aurora.value,
}

# Available fields in the "running" block of activity.json file
class Activity_Response_Running(BaseModel):
    color: str
    jobid: str
    location: List[str]
    mode: str
    nodes: int
    project: str
    queue: str
    runtimef: str
    starttime: str
    state: str
    submittime: int
    walltime: int
    walltimef: str

# Available fields in the "queued" block of activity.json file
class Activity_Response_Queued(BaseModel):
    jobid: str
    mode: str
    nodes: int
    project: str
    queue: str
    queuedtimef: str
    score: float
    starttime: str
    state: str
    submittime: int
    walltime: int
    walltimef: str

# Activity.json content 
class Activity_Response(BaseModel):
    dimensions: Optional[dict] = {}
    motd_info: Optional[list] = []
    nodeinfo: Optional[dict] = {}
    queued: Optional[List[Activity_Response_Queued]] = []
    reservation: Optional[list] = []
    running: Optional[List[Activity_Response_Running]] = []
    starting: Optional[list] = []
    updated: Optional[int] = 0
    maint: Optional[bool] = False # For maintenance
    start: Optional[int] = 0 # For maintenance
    end: Optional[int] = 0 # For maintenance
    def __hash__(self) -> int:
        return hash(self.updated)

# Summary job content
class Summary_Job(BaseModel):
    running: int
    queued: int
    starting: int
    utilized_nodes: int


# Fetch an activity.json file from ALCF
@cached(TTLCache(maxsize=1024, ttl=60))
async def fetch_activity_json(resource_id):

    # Recover the URL to fetch status
    try:
        url = ALCF_RESOURCE_ID_TO_URL[resource_id]
    except KeyError:
        raise ValueError(f"Status not implemented yet for resource_id: {resource_id}")
    except Exception as e:
        raise RuntimeError(f"Internal server error: {e}")

    # Fetch and decode raw data from URL
    try:
        async with httpx.AsyncClient() as client:
            activity_response = await client.get(url, timeout=15)
            activity_response = activity_response.json()
    except httpx.TimeoutException:
        raise TimeoutError("Request timed out while fetching activity data")
    except JSONDecodeError:
        raise ValueError("Could not decode status response")
    except Exception as e:
        raise RuntimeError(f"Could not reach resource: {e}")
        
    # Validate input data
    try:
        activity_response = Activity_Response(**activity_response)
    except ValidationError as e:
        raise ValueError(f"Activity response not valid: {e}")
    except Exception as e:
        raise RuntimeError(f"Could not validate activity response: {e}")
        
    # Return the validated activity response
    return activity_response


# Helper function to format datetime strings in human-readable format
def format_human_readable_datetime(iso_string):
    """Convert ISO datetime string to human-readable format."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except (ValueError, TypeError):
        return str(iso_string)


# Extract overall status of a resource from its activity.json file
def get_resource_status(activity_response: Activity_Response):
    """Extract overall status of a resource from its activity.json file, along with message."""

    # Maintenance
    if activity_response.maint:

        # Try to convert Unix timestamp to UTC datetime isoformat string
        try:
            end_timestamp = int(activity_response.end)
            end_datetime = datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
            end_string = end_datetime.isoformat()
        except (ValueError, TypeError):
            end_string = str(activity_response.end)
            
        # Convert to human-readable format
        human_readable_end = format_human_readable_datetime(end_string)

        # Return status and message
        return Status.down.value, f"maintenance with expected end on {human_readable_end}"
        
    # Up if jobs are running
    elif len(activity_response.running) > 0 or len(activity_response.queued) > 0:
        return Status.up.value, "resource is up and running"
        
    # Unknown if none of the check went through
    else:
        return Status.unknown.value, "could not extract status information from activity.json"


# Parse and summarize the nodeinfo block of an activity.json file
@cached(TTLCache(maxsize=1024, ttl=30))
async def summarize_nodes(activity_response: Activity_Response):
    """Parse and summarize the nodeinfo block of an activity.json file."""

    # Get list of state entries for all nodes
    try:
        state_entries = [n["state"] for n in activity_response.nodeinfo.values()]
    except:
        return {}

    # Extract list of unique states
    states = set(state_entries)

    # Build the number of nodes associated with each state
    summary = {}
    for state in states:
        summary[state] = state_entries.count(state)

    # Add total number of utilized nodes (from running jobs)
    nested_locations = [r.location for r in activity_response.running]
    nb_unique_locations = len(set([x for locations in nested_locations for x in locations]))
    summary["utilized"] = nb_unique_locations

    # Return the nodes summary
    return summary


# Parse and summarize jobs from an activity.json file
@cached(TTLCache(maxsize=1024, ttl=30))
async def summarize_jobs(activity_response: Activity_Response):
    """Parse and summarize jobs from an activity.json file."""
        
    # Get list of queue entries for each job state
    try:
        running_queue_entries = [r.queue for r in activity_response.running]
        queued_queue_entries = [r.queue for r in activity_response.queued]
        starting_queue_entries = [r.queue for r in activity_response.starting]
    except:
        return {}

    # Declare summary dictionary
    summary = {}

    # Extract list of unique utilized queues
    queues = []
    queues.extend(running_queue_entries)
    queues.extend(queued_queue_entries)
    queues.extend(starting_queue_entries)
    unique_queues = set(queues)

    # For each queue ...
    for queue in unique_queues:

        # Get list of running job locations for the targetted queue
        running_filter = [r for r in activity_response.running if r.queue == queue]
        nested_locations = [r.location for r in running_filter]
        nb_unique_locations = len(set([x for locations in nested_locations for x in locations]))

        summary[queue] = Summary_Job(
            running=running_queue_entries.count(queue),
            queued=queued_queue_entries.count(queue),
            starting=starting_queue_entries.count(queue),
            utilized_nodes=nb_unique_locations
        )

    # Add the jobs summary for all queues
    summary["total"] = Summary_Job(
        running=len(running_queue_entries),
        queued=len(queued_queue_entries),
        starting=len(starting_queue_entries),
        utilized_nodes=sum([v.utilized_nodes for q, v in summary.items() if q in queues])
    )

    # Return the jobs summary
    return summary


# Create Incident and Event objects from activity.json file
async def get_incident_event_from_activity_json(resource_id: str, resource_name: str):
    """Create and return an Incident and Event objects from parsing an ALCF activity.json file."""

    # Record timestamp where the fetch/parse occured (in UTC, timezone-naive for database compatibility)
    current_datetime = datetime.now(timezone.utc).replace(tzinfo=None)

    # Fetch data from activity.json and define resource status
    try:
        activity_response = await fetch_activity_json(resource_id)
        status, event_description = get_resource_status(activity_response)
        incident_type = IncidentType.planned.value
    except Exception as e:
        status = Status.unknown.value
        event_description = "could not extract status information from activity.json"
        incident_type = IncidentType.unplanned.value
    
    # Create an incident database object
    try:
        incident_id = str(uuid4())
        incident = Incident(
            id=incident_id,
            name=f"{resource_name} activity fetch",
            short_name=f"{resource_name}_activity_fetch",
            description=f"Parsed the activity.json data for {resource_name}",
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
            name=f"{resource_name} activity",
            short_name=f"{resource_name}_activity",
            description=f"{resource_name}: {event_description}.",
            last_updated=current_datetime,
            status=status,
            occurred_at=current_datetime
        )
    except Exception as e:
        raise ValueError(f"Could not create event: {e}")

    # Return the Incident and Event objects
    return incident, event


# Clear all activity data from the database
async def clear_activity_data(db):
    """Clear all activity-related data from the database (useful for testing)."""
    try:
        await db.execute(delete(Event))
        await db.execute(delete(Incident))
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise RuntimeError(f"Error clearing activity data: {e}")


async def ingest_activity_data_for_resource(resource_id: str, db):
    """Ingest activity data for a specific resource and save to database."""
    try:
        # Collect the resource entry from the database within current session
        resource: Resource = await db.get(Resource, resource_id)
        if resource is None:
            raise ValueError(f"Resource {resource_id} not found")

        # Create incident and event objects from activity.json file
        incident, event = await get_incident_event_from_activity_json(resource.id, resource.name)

        # Record current datetime (timezone-naive for database compatibility)
        current_datetime = datetime.now(timezone.utc).replace(tzinfo=None)

        # If there is a last event associated with the resource ...
        if resource.last_event_id:
            last_event: Event = await db.get(Event, resource.last_event_id)
            
            # If the last event is the same as the new event ...
            if last_event.description == event.description and last_event.status == event.status:
                
                # Update the time when the resource status was last verified and ensure current_status is synced
                resource.last_verified = current_datetime
                resource.current_status = event.status
                await db.commit()

                # Skip the creation of a new event or incident
                return None, None, resource

        # Create relationships
        event.incident_id = incident.id
        event.resource_id = resource.id
        resource.last_event_id = event.id
        
        # Update incident with event and resource IDs
        incident.event_ids = [event.id]
        incident.resource_ids = [resource.id]
        
        # Update resource's current_status and timestamps
        resource.current_status = event.status
        resource.last_updated = current_datetime
        resource.last_verified = current_datetime

        # Add to database
        db.add(incident)
        db.add(event)
        await db.commit() # Resource is already in session, so just modify and commit
        
        # Return database objects
        return incident, event, resource
        
    except Exception as e:
        await db.rollback()
        raise RuntimeError(f"Error processing {resource_id}: {e}")


async def main():
    """Main function to run activity data ingestion."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ingest activity data from ALCF status pages')
    parser.add_argument('--clear', action='store_true', 
                       help='Clear all existing activity data before ingestion')
    args = parser.parse_args()

    try:
        # Create tables if not already done
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        # Get database session using async context manager
        async with get_db_session_context() as db_session:
            try:
                
                # Clear activity data if requested
                if args.clear:
                    await clear_activity_data(db_session)
                    print("Activity data cleared successfully!")

                # Process each resource
                for resource_enum in ALCF_RESOURCE_ID_LIST:
                    resource_id = resource_enum.value
                    resource_name = resource_enum.name

                    # Ingest activity data for this resource
                    try:
                        _, _, _ = await ingest_activity_data_for_resource(resource_id, db_session)
                        print(f"  Successfully processed {resource_name}")
                    except Exception as e:
                        print(f"  Error processing {resource_id}: {e}")
                        await db_session.rollback()
                
                print("\nActivity data ingestion completed!")
                        
            except Exception as e:
                print(f"Unexpected error: {e}")
    finally:
        # Dispose of the engine to close all connections
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())