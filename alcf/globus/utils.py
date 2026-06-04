from alcf.endpoints import get_endpoint, EndpointType, APIComponent
from alcf.globus.utils_compute import submit_compute_task
from starlette.status import HTTP_501_NOT_IMPLEMENTED
from fastapi import HTTPException
from app.types.user import User
from typing import Tuple

from alcf.config import CACHE_TTL_GLOBUS
from alcf.cache.manager import cache_manager


# Submit task
async def submit_task(
        function_name: str, 
        resource_name: str, 
        input_data: dict, 
        user: User
    ) -> Tuple[str, dict]:
    """Extract Globus endpoint, submit task, and return task ID and result (if possible)."""
        
    # Extract filesystem endpoint for the targetted resource
    globus_endpoint = get_endpoint(
        api_component=APIComponent.FILESYSTEM.value,
        resource_name=resource_name,
        operation=function_name,
    )

    # Submit Globus Compute task
    if globus_endpoint.endpoint_type == EndpointType.GLOBUS_MULTI_USER_ENDPOINT.value:
        task_id, result = await submit_compute_task(
            globus_endpoint,
            input_data, 
            user
        )

    # Submit Globus Transfer task
    if globus_endpoint.endpoint_type == EndpointType.GLOBUS_TRANSFER_ENDPOINT.value:
        task_id, result = await submit_transfer_task(
            function_name, 
            globus_endpoint,
            input_data, 
            user
        )

    # Error if endpoint not supported 
    else:
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED, 
            detail=f"Endpoint for {function_name} on {resource_name} is not supported."
        )

    return task_id, result




