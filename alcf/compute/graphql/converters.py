from fastapi import HTTPException
from starlette.status import (HTTP_500_INTERNAL_SERVER_ERROR)
from app.routers.account import models as account_models
from app.routers.compute import models as compute_models
from alcf.compute.graphql import models as graphql_models
from typing import Any


# Get nested value
def get_nested_value(obj, path):
    """
    Get a nested value from an object using dot notation.
    Returns None if any part of the path is None or doesn't exist.
    """
    try:
        for attr in path.split('.'):
            if obj is None:
                return None
            obj = getattr(obj, attr, None)
        return obj
    
    # Error message if something goes wrong
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not get nested value for IRI -> GraphQL conversion: {e}"
        )


# Set nested value
def set_nested_value(data: dict, path: str, value: Any) -> dict:
    """Set a value in a nested dictionary structure using dot notation."""

    # Don't do anythin if the value is None
    if value is None:
        return data

    # Get list of keys to navitage through the dictionary
    keys = path.split('.')
    
    # Navigate/create the nested structure
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # Set the final value
    current[keys[-1]] = value

    # Return the modified data
    return data


# Get GraphQL Job from IRI JobSpec
def get_graphql_job_from_iri_jobspec(iri_jobspec: compute_models.JobSpec) -> graphql_models.Job:
    """Convert an IRI JobSpec to a GraphQL Job model."""
    
    # Define mapping ('graphql_job':'iri_job')
    field_mapping = {
        'name': 'name',
        'remoteCommand': 'executable',
        'commandArgs': lambda js: js.arguments if js.arguments else None,
        'workDir': 'directory',
        'errorPath': 'stderr_path',
        'outputPath': 'stdout_path',
        'resourcesRequested.jobResources.wallClockTime': lambda js: js.attributes.duration.seconds if js.attributes and js.attributes.duration else None,
        'resourcesRequested.jobResources.physicalMemory': lambda js: js.resources.memory if js.resources else None,
        'queue.name': lambda js: js.attributes.queue_name if js.attributes else None,
    }
    
    # Apply mapping
    graphql_data = generate_dictionary_from_mapping(iri_jobspec, field_mapping)
        
    # Create and return the GraphQL Job object
    return graphql_models.Job(**graphql_data)


# Get IRI Job from GraphQL Job
def get_iri_job_from_graphql_job(graphql_job: graphql_models.Job) -> compute_models.Job:
    """Convert a GraphQL Job to an IRI Job."""
    
    # Define mapping ('iri_job':'graphql_job')
    field_mapping = {
        'id': 'jobId',
        'status.state': lambda j: get_iri_state_from_pbs_state(graphql_job.status.state) if j.status and j.status.state is not None else None,
        'status.exit_code': lambda j: j.status.exitStatus if j.status else None
    }
    
    # Apply mapping
    iri_data = generate_dictionary_from_mapping(graphql_job, field_mapping)
        
    # Create and return the IRI Job object
    return compute_models.Job(**iri_data)


# Generate dictionary from mapping
def generate_dictionary_from_mapping(source_model: Any, field_mapping: dict) -> dict:
    """Create a dictionary from nested mapping instructions"""

    # Declare the data dictionary
    destination_data = {}
    
    # For each mapping ...
    for target_path, source in field_mapping.items():

        # Extract value from source
        if callable(source):
            value = source(source_model)
        else:
            value = get_nested_value(source_model, source)
        
        # Set value in the destination dictionary
        destination_data = set_nested_value(destination_data, target_path, value)

    # Return the dictionary
    return destination_data

    
# Get IRI job state from PBS state
def get_iri_state_from_pbs_state(state: int) -> int:
    """Return the IRI Facility API compliant state from a PBS GraphQL state."""

    # Known states
    if state in [0]:
        return compute_models.JobState.NEW.value
    elif state in [3]:
        return compute_models.JobState.QUEUED.value
    elif state in [6, 7]:
        return compute_models.JobState.ACTIVE.value
    elif state in [10]:
        return compute_models.JobState.COMPLETED.value
    elif state in [12]:
        return compute_models.JobState.CANCELED.value
    elif state in [11]:
        return compute_models.JobState.FAILED.value

    # Unknown state
    else:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PBS job state {state} not supported."
        )