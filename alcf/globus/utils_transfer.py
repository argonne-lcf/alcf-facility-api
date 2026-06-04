from cachetools import TTLCache, cached
from fastapi import HTTPException
from globus_sdk import AccessTokenAuthorizer, TransferClient
from alcf.endpoints import GlobusTransferEndpoint
from alcf.auth.utils import introspect_token as globus_introspect_token
from alcf.auth.utils import LOGOUT_MESSAGE_STR
from app.types.user import User
from starlette.status import HTTP_501_NOT_IMPLEMENTED, HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR
from typing import Tuple
from uuid import uuid4

# Get Globus Transfer Client
@cached(cache=TTLCache(maxsize=1024, ttl=60 * 60))
def get_transfer_client(user_name: str, user_api_key: str) -> TransferClient:
    """Create a Globus Transfer SDK client from user's access token"""
    try:
        return TransferClient(authorizer=AccessTokenAuthorizer(user_api_key))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Could not create Globus Transfer client for user {user_name}: {e}"
        )
    

# Execute ls command
async def transfer_ls(
    globus_endpoint: GlobusTransferEndpoint,
    input_data: dict, 
    user: User
) -> Tuple[str, dict]:
    
    # Unsupported parameters
    for bool_parameter in ["numeric_uid", "recursive", "dereference"]:
        if input_data.get(bool_parameter, False):
            raise HTTPException(
                status_code=HTTP_501_NOT_IMPLEMENTED, 
                detail=f"{bool_parameter} not supported with Globus Transfer ls operation."
            )

    # Extract Globus Transfer access token
    access_token = get_globus_transfer_access_token(user)

    # Get Globus Transfer client using the user's token
    transfer_client = get_transfer_client(user.name, access_token)

    # Prepare the input data
    input_data = {
        "path": input_data.get("path", None),
        "show_hidden": input_data.get("show_hidden", False)
    }

    # Generate a task ID (since Globus Transfer ls is synchronous)
    task_id = str(uuid4())

    # Submit
    # TODO make this async
    try:
        response = transfer_client.operation_ls(globus_endpoint.endpoint_id, path="inference_service/vllm_logs")
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Could not submit Globus Transfer ls task: {e}"
        )
    
    # Extract ls result
    try:
        result = response.data["DATA"]
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Could not extract result from Globus Transfer ls task."
        )

    # Format result
    result = [
        {
            "name"
        }
    for ...]
    HEHEHEHEHEHEHEHEHEH
    THINK carefully here, do you want to hardcode this here? or do you want a 
    special per-transfer/per-compute formatting special fancy thing that would separate submittion from formatting?????
    {
        "name": "parsl.GlobusComputeEngine-HighThroughputExecutor.block-0.1764194504.5648103.nodes",
        "type": "file",
        "link_target": "",
        "user": "bcote",
        "group": "users",
        "permissions": "rw-r--r--",
        "last_modified": "2025-11-26T22:01:47Z",
        "size": "25"
      }
    {
       'name': 'sophia_vllm_nvidia', 
       'type': 'dir', 
       'link_target': None, 
       'user': 'openinference_svc',
        'group': 'inference_service',
        'permissions': '2755', 
       'last_modified': '2026-04-07 23:17:41+00:00', 
       'size': 4096, 
       }
    
    # Return task ID and result
    return task_id, result
    #def for entry in transfer_client.operation_ls(globus_endpoint.endpoint_id, path="inference_service/vllm_logs"):
    #print(entry)

    #input_data = {
    #        "path": path,
    #        "show_hidden": show_hidden,
    #        #"numeric_uid": numeric_uid,
    #        #"recursive": recursive,
    #        #"dereference": dereference
    #    }

def get_globus_transfer_access_token(user: User) -> str:

    # Recover Globus access token from the introspection (from cache)
    _, _, dependent_tokens, _ = globus_introspect_token(user.api_key)

    # [TEMPORARY]
    # Error if users still use the old auth token script that does not include transfer scope
    if dependent_tokens.transfer is None:
        error_message = ""
        error_message += "Missing new dependent token. Please use the latest "
        error_message += "alcf_facility_api_globus_token.py script at "
        error_message += "https://github.com/argonne-lcf/alcf-facility-api-token. "
        error_message += LOGOUT_MESSAGE_STR
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, 
            detail=error_message
        )
    
    # Return transfer token
    return dependent_tokens.transfer


# Map between function names and transfer functions
TRANSFER_FUNCTION_MAP = {
    "ls": transfer_ls
}


# Submit transfer task
async def submit_transfer_task(
    function_name: str, 
    globus_endpoint: GlobusTransferEndpoint,
    input_data: dict, 
    user: User
) -> Tuple[str, dict]:
    """Route a task to the appropriate Globus Transfer function."""

    # Error if function mapping not implemented yet
    if function_name not in TRANSFER_FUNCTION_MAP:
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED, 
            detail=f"Function {function_name} not integrated in the Globus Transfer map."
        )

    # Submit the transfer command
    return await TRANSFER_FUNCTION_MAP[function_name](globus_endpoint, input_data, user)
