from alcf.auth.utils import introspect_token as globus_introspect_token
from alcf.endpoints import _BaseEndpoint
from app.routers.task import models as task_models
from app.types.user import User
from typing import Tuple
from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from globus_compute_sdk import Client, Executor
from globus_compute_sdk.sdk.login_manager import AuthorizerLoginManager
from globus_compute_sdk.sdk.login_manager.manager import ComputeScopeBuilder
from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_sdk import AccessTokenAuthorizer
ComputeScopes = ComputeScopeBuilder()

from alcf.config import CACHE_TTL_GLOBUS
from alcf.cache.manager import cache_manager
from alcf.globus.schemas import GlobusSubmitResponse


# Get Globus Compute Executor
@cache_manager.cached(ttl=CACHE_TTL_GLOBUS)
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
@cache_manager.cached(ttl=CACHE_TTL_GLOBUS)
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

        # Create Compute client
        return Client(login_manager=compute_login_manager)
    
    # Error if something wrong happen
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Could not create Globus Compute client for user {user_name}: {e}"
        )
    

# Submit Globus Compute task
async def submit_compute_task(
        globus_endpoint: _BaseEndpoint,
        input_data: dict, 
        user: User
    ) -> GlobusSubmitResponse:

    # Recover Globus Compute access token (from cache)
    _, _, dependent_tokens, _ = globus_introspect_token(user.api_key)

    # Get Globus Compute client from user's token
    gcc = get_compute_client(user.name, dependent_tokens.compute)

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
        
    # Return the Globus Compute task ID with no result
    # Task ID, empty result, False for not failed
    return GlobusSubmitResponse(task_id=task_id)


# Get Globus Compute task status
# TODO: cache this
def get_compute_task_status(user: User, task_id: str) -> tuple[str, str]:
    """Check the status of a task with Globus Compute and return result if completed."""

    # Recover Globus Compute access token (from cache)
    _, _, dependent_tokens, _ = globus_introspect_token(user.api_key)

    # Get Globus Compute client using user's credentials
    gcc = get_compute_client(user.name, dependent_tokens.compute)

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
