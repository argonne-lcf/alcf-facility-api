from alcf.endpoints import get_endpoint, EndpointType, APIComponent
from starlette.status import HTTP_501_NOT_IMPLEMENTED, HTTP_500_INTERNAL_SERVER_ERROR
from fastapi import HTTPException
from app.types.user import User

from alcf.enums import EndpointType
from alcf.globus.utils_compute import submit_compute_task, get_compute_task_status
from alcf.globus.utils_transfer import submit_transfer_task, get_transfer_task_status
from alcf.globus.schemas import GlobusSubmitResponse


# Submit task
async def submit_task(
        function_name: str, 
        resource_name: str, 
        input_data: dict, 
        user: User
    ) -> GlobusSubmitResponse:
    """Extract Globus endpoint, submit task, and return task ID and result (if possible)."""
        
    # Extract filesystem endpoint for the targetted resource
    globus_endpoint = get_endpoint(
        api_component=APIComponent.FILESYSTEM.value,
        resource_name=resource_name,
        operation=function_name,
    )

    # Submit Globus Compute task
    if globus_endpoint.endpoint_type == EndpointType.GLOBUS_MULTI_USER_ENDPOINT.value:
        return await submit_compute_task(
            globus_endpoint,
            input_data, 
            user
        )

    # Submit Globus Transfer task
    if globus_endpoint.endpoint_type == EndpointType.GLOBUS_TRANSFER_ENDPOINT.value:
        return await submit_transfer_task(
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


# Get task status
async def get_task_status(
    user: User,
    task_id: str,
    globus_endpoint_type: str
) -> tuple[str, str]:
    """Get latest status of a Globus task."""
    if globus_endpoint_type == EndpointType.GLOBUS_MULTI_USER_ENDPOINT.value:
        return get_compute_task_status(user, task_id)
    elif globus_endpoint_type == EndpointType.GLOBUS_TRANSFER_ENDPOINT.value:
        return get_transfer_task_status(user, task_id)
    else:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Task status query not supported for {globus_endpoint_type}."
        )




