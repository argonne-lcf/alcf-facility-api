from cachetools import TTLCache, cached
from alcf.endpoints import get_endpoint, EndpointType, APIComponent
from alcf.auth.utils import introspect_token as globus_introspect_token
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST
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
def get_compute_executor(user_name: str, user_api_key: str) -> Executor:
    """Create a Globus Compute SDK client from user's access token"""
    try:

        # Get Globus Compute client
        gcc = get_compute_client(user_name, user_api_key)

        # Create and return the executor
        return Executor(
            client=gcc,
            batch_size=1,
            api_burst_limit=1,
            serializer = ComputeSerializer(strategy_code=CombinedCode())
        )
        
    # Error if something wrong happen
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not create Globus Compute executor for user {user_name}: {e}")


# Get Globus Compute Client
@cached(cache=TTLCache(maxsize=1024, ttl=60 * 60))
def get_compute_client(user_name: str, user_api_key: str) -> Client:
    """Create a Globus Compute SDK client from user's access token"""
    try:

        # Get Globus authorizers
        compute_auth = AccessTokenAuthorizer(user_api_key)

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
        raise HTTPException(
            status_code=500, 
            detail=f"Could not create Globus Compute client for user {user_name}: {e}"
        )
    

# Submit task and get result
# TODO (if you keep this, make this async)
def submit_task_and_get_result(
        function_name: str, 
        resource_name: str, 
        input_data: dict, 
        user: account_models.User
    ):
    """Extract endpoint and function IDs, submit task, and wait for result."""
        
    # Extract Globus multi-user endpoint for the targetted resource
    globus_endpoint = get_endpoint(
        api_component=APIComponent.FILESYSTEM.value,
        resource_name=resource_name,
        operation=function_name,
    )

    # Make sure the endpoint is a Globus multi-user endpoint
    if globus_endpoint.endpoint_type != EndpointType.GLOBUS_MULTI_USER_ENDPOINT.value:    
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, 
            detail=f"Endpoint for {resource_name} is not a Globus multi-user endpoint."
        )
        
    # Get Globus Compute executor from user's token
    gce = get_compute_executor(user.name, user.api_key)
    gce.endpoint_id = globus_endpoint.endpoint_id

    # Make sure the endpoint runs on the login node
    gce.user_endpoint_config = {"provider": "local"}

    # Submit task to Globus Compute
    try:
        future = gce.submit_to_registered_function(globus_endpoint.function_id, args=[input_data])
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
        resource_name: str, 
        input_data: dict, 
        user: account_models.User
    ) -> str:
    """Extract endpoint and function IDs, submit task, and return task ID."""
        
    # Extract Globus multi-user endpoint for the targetted resource
    globus_endpoint = get_endpoint(
        api_component=APIComponent.FILESYSTEM.value,
        resource_name=resource_name,
        operation=function_name,
    )

    # Make sure the endpoint is a Globus multi-user endpoint
    if globus_endpoint.endpoint_type != EndpointType.GLOBUS_MULTI_USER_ENDPOINT.value:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, 
            detail=f"Endpoint for {resource_name} is not a Globus multi-user endpoint."
        )

    # Recover Globus Compute access token (from cache)
    _, _, globus_compute_access_token, _ = globus_introspect_token(user.api_key)
    user.api_key = globus_compute_access_token

    # Get Globus Compute client from user's token
    gcc = get_compute_client(user.name, user.api_key)

    # Submit task to Globus Compute
    try:
        batch = gcc.create_batch()
        batch.add(globus_endpoint.function_id, [input_data])
        batch_response = gcc.batch_run(globus_endpoint.endpoint_id, batch)
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not submit task to Globus Compute: {e}"
        )
    
    # Try to recover the task ID
    try:
        task_id = list(batch_response["tasks"].values())[0][0]
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not recover Globus Compute task ID: {e}"
        )
        
    # Return the Globus Compute task ID
    return task_id


# Get task status
# TODO: cache this
def get_task_status(user: account_models.User, task_id: str):
    """Check the status of a task with Globus Compute and return result if completed."""

    # Recover Globus Compute access token (from cache)
    _, _, globus_compute_access_token, _ = globus_introspect_token(user.api_key)
    user.api_key = globus_compute_access_token

    # Get Globus Compute client using user's credentials
    gcc = get_compute_client(user.name, user.api_key)

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
            result = {
                "error": result["error"]
            }

        # Completed
        else:
            status = task_models.TaskStatus.completed.value
            result = result["output"]

    # Failed if an error occured outside of the function execution
    else:
        status = task_models.TaskStatus.failed.value
        result = {
            "error": "Unexpected error outside of the function execution."
        }

    # Return the status and result (if any)
    return status, result

