import asyncio
import time
import json
from alcf.config import GLOBUS_COMPUTE_ENDPOINTS, GLOBUS_COMPUTE_FUNCTIONS
from starlette.status import HTTP_501_NOT_IMPLEMENTED, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_408_REQUEST_TIMEOUT
from fastapi import HTTPException
from app.routers.account import models as account_models
from app.routers.status import models as status_models
from app.routers.task import models as task_models
from globus_compute_sdk import Client, Executor
from globus_compute_sdk.sdk.login_manager import AuthorizerLoginManager
from globus_compute_sdk.sdk.login_manager.manager import ComputeScopeBuilder
from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_sdk import AccessTokenAuthorizer
ComputeScopes = ComputeScopeBuilder()


# Get Globus Compute Executor
def get_compute_executor(user: account_models.User) -> Executor:
    """Create a Globus Compute SDK client from user's access token"""
    try:

        # Get Globus Compute client
        gcc = get_compute_client(user)

        # Create and return the executor
        return Executor(
            client=gcc,
            batch_size=1,
            api_burst_limit=1,
            serializer = ComputeSerializer(strategy_code=CombinedCode())
        )
        
    # Error if something wrong happen
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not create Globus Compute executor for user {user.name}: {e}")


# Get Globus Compute Client
def get_compute_client(user: account_models.User) -> Client:
    """Create a Globus Compute SDK client from user's access token"""
    try:

        # Get Globus authorizers
        compute_auth = AccessTokenAuthorizer(user.api_key)

        # Create Globus login manager using tokens
        compute_login_manager = AuthorizerLoginManager(
            authorizers={
                ComputeScopes.resource_server: compute_auth,
            }
        )
        #compute_login_manager.ensure_logged_in()

        # Create Compute client
        return Client(login_manager=compute_login_manager)
    
    # Error if something wrong happen
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not create Globus Compute client for user {user.name}: {e}")
    

# Get Compute endpoint ID
def get_compute_endpoint_id(resource: status_models.Resource) -> str:
    """Return the UUID of the endpoint running for the targetted resource."""
    try: 
        return GLOBUS_COMPUTE_ENDPOINTS[resource.name.lower()]
    except:
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED, 
            detail=f"Remote commands not available for resource {resource.id}."
        )
    

# Get Compute function ID
def get_compute_function_id(function_name: str) -> str:
    """Return the UUID of the function for the targetted command."""
    try: 
        return GLOBUS_COMPUTE_FUNCTIONS[function_name.lower()]
    except:
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED, 
            detail=f"Remote commands {function_name} not available."
        )
    

# Submit task and get result
# TODO (if you keep this, make this async)
def submit_task_and_get_result(
        function_name: str, 
        resource: status_models.Resource, 
        input_data: dict, 
        user: account_models.User
    ):
    """Extract endpoint and function IDs, submit task, and wait for result."""
        
    # Extract Globus Compute endpoint and function IDs
    endpoint_id = get_compute_endpoint_id(resource)
    function_id = get_compute_function_id(function_name)
        
    # Get Globus Compute executor from user's token
    gce = get_compute_executor(user)
    gce.endpoint_id = endpoint_id

    # Make sure the endpoint runs on the login node
    gce.user_endpoint_config = {"provider": "local"}

    # Submit task to Globus Compute
    try:
        future = gce.submit_to_registered_function(function_id, args=[input_data])
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not submit task to Globus Compute: {e}"
        )
        
    # Wait for the response
    try:
        response = future.result(timeout=60)
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not recover result from Globus Compute: {e}"
        )
        
    # Error if something wrong happened
    if "error" in response and response["error"]:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Runtime error: {response["error"]}"
        )

    # Return result
    try:
        return response["output"]
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not parse Globus Compute response: {e}"
        )
    

# Submit task
async def submit_task(
        function_name: str, 
        resource: status_models.Resource, 
        input_data: dict, 
        user: account_models.User
    ) -> str:
    """Extract endpoint and function IDs, submit task, and return task ID."""
        
    # Extract Globus Compute endpoint and function IDs
    endpoint_id = get_compute_endpoint_id(resource)
    function_id = get_compute_function_id(function_name)
        
    # Get Globus Compute executor from user's token
    gce = get_compute_executor(user)
    gce.endpoint_id = endpoint_id

    # Make sure the endpoint runs on the login node
    gce.user_endpoint_config = {"provider": "local"}

    # Submit task to Globus Compute
    try:
        future = gce.submit_to_registered_function(function_id, args=[input_data])
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not submit task to Globus Compute: {e}"
        )
    
    # While the future object still does not have a task ID assigned ...
    start = time.monotonic()
    while future.task_id is None:

        # Sleep for a little while
        await asyncio.sleep(0.5)

        # Raise an error is something went wrong
        if future._exception:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Could not submit task to Globus Compute: {str(future._exception)}"
            )
        
        # Raise an error if the process is taking too long
        if time.monotonic() - start > 10:
            raise HTTPException(
                status_code=HTTP_408_REQUEST_TIMEOUT,
                detail=f"Timeout while retrieving task ID from Globus Compute."
            )
        
    # Return the Globus Compute task ID
    return future.task_id


# Get task status
# TODO: cache this
def get_task_status(user: account_models.User, task_id: str):
    """Check the status of a task with Globus Compute and return result if completed."""

    # Get Globus Compute client using user's credentials
    gcc = get_compute_client(user)

    # Try to get the task status from Globus
    try:
        task_status = gcc.get_task(task_id)
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not get task status from Globus Compute: {e}"
        )

    # Still pending
    if task_status["pending"]:
        status = task_models.TaskStatus.pending.value
        result = None

    # If function execution succeeded (but may still include an error) ...
    elif task_status.get("status", None) == "success":

        # Gather the result
        result = task_status.get("result", None)

        # Failed
        if result["error"]:
            status = task_models.TaskStatus.failed.value
            result = result["error"]

        # Completed
        else:
            status = task_models.TaskStatus.completed.value
            result = result["output"]

    # Failed if an error occured outside of the function execution
    else:
        status = task_models.TaskStatus.failed.value
        result = "?????"

    # Return the status and result (if any)
    return status, result