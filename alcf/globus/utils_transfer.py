import asyncio
import stat

from pathlib import Path
from typing import Tuple, Any, Callable

from fastapi import HTTPException
from globus_sdk import AccessTokenAuthorizer, TransferClient, TransferAPIError
from alcf.endpoints import GlobusTransferEndpoint
from alcf.auth.utils import introspect_token as globus_introspect_token
from alcf.auth.utils import LOGOUT_MESSAGE_STR
from app.types.user import User
from starlette.status import HTTP_501_NOT_IMPLEMENTED, HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

from alcf.auth.utils import generate_error_message
from alcf.cache.manager import cache_manager
from alcf.config import CACHE_TTL_GLOBUS
from alcf.filesystem.validation import ALLOWED_PATH_BASES
from alcf.globus.schemas import GlobusSubmitResponse


# Get Globus Transfer Client
@cache_manager.cached(ttl=CACHE_TTL_GLOBUS)
def get_transfer_client(access_token: str, user_name: str) -> TransferClient:
    """Create a Globus Transfer SDK client from user's access token"""
    try:
        return TransferClient(authorizer=AccessTokenAuthorizer(access_token))
    except Exception as e:
        error_message = generate_error_message(
            f"Could not create Globus Transfer client for user {user_name}", e
        )
        raise HTTPException(
            status_code=500, 
            detail=error_message
        )
    

# Strip base
def __strip_base(path: str, location: str) -> str:
    """Remove base path from path to start at the base of a Globus collection."""
    path = Path(path) if isinstance(path, str) else path
    for base in ALLOWED_PATH_BASES[location]:
        try:
            return str(path.relative_to(base))
        except ValueError:
            pass
    raise HTTPException(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"Could not remove the base path for {str(path)} for {location} collection."
    )
    

# Execute ls command
async def transfer_ls(
    globus_endpoint: GlobusTransferEndpoint,
    input_data: dict, 
    user: User
) -> GlobusSubmitResponse:
    
    # Unsupported parameters
    for bool_parameter in ["numeric_uid", "recursive", "dereference"]:
        if input_data.get(bool_parameter, False):
            raise HTTPException(
                status_code=HTTP_501_NOT_IMPLEMENTED, 
                detail=f"{bool_parameter} not supported with Globus Transfer ls operation."
            )

    # Prepare the input data
    input_data = {
        "path": __strip_base(input_data.get("path", None), globus_endpoint.location),
        "show_hidden": input_data.get("show_hidden", False)
    }
    
    # Submit operation and return generated response object
    transfer_client: TransferClient = get_transfer_client(get_globus_transfer_access_token(user), user.name)
    response = await submit_transfer_client_operation(
        transfer_client.operation_ls, globus_endpoint.endpoint_id, **input_data
    )

    # Return formatted response
    if not response.failed:
        response.result = __format_ls_response(response.result)
    return response


# Execute mkdir command
async def transfer_mkdir(
    globus_endpoint: GlobusTransferEndpoint,
    input_data: dict, 
    user: User
) -> GlobusSubmitResponse:
    
    # Unsupported parameters
    if input_data.get("parent", False):
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED, 
            detail=f"'parent' argument not supported with Globus Transfer mkdir operation."
        )
    
    # Prepare the input data
    path = __strip_base(input_data.get("path", None), globus_endpoint.location)
    
    # Submit operation and return generated response object
    transfer_client: TransferClient = get_transfer_client(get_globus_transfer_access_token(user), user.name)
    response = await submit_transfer_client_operation(
        transfer_client.operation_mkdir, globus_endpoint.endpoint_id, path
    )

    # Return formatted response
    if not response.failed:
        response.result = {"output": None}
    return response



async def submit_transfer_client_operation(
    client_operation: Callable,
    endpoint_id: str,
    *args,
    **kwargs
) -> GlobusSubmitResponse:
    """Submit Globus transfer operation and return response if possible"""
    try:
        result = await asyncio.to_thread(client_operation, endpoint_id, *args, **kwargs)
        return GlobusSubmitResponse(result=result)
    except TransferAPIError as e:
        return GlobusSubmitResponse(result=str(e.message), failed=True)
    except Exception as e:
        error_message = generate_error_message("Could not submit Globus Transfer task.", e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=error_message
        )

    
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
    "ls": transfer_ls,
    "mkdir": transfer_mkdir
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


# Format ls response
def __format_ls_response(ls_response: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert ls Transfer response to IRI response."""

    # Extract ls result
    try:
        ls_data = ls_response.data["DATA"]
    except Exception as e:
        error_message = generate_error_message("Could not extract result from Globus Transfer ls task.", e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=error_message
        )
    
    # Format all entries
    return [__format_ls_entry(entry) for entry in ls_data]


# Format ls entry
def __format_ls_entry(ls_entry: dict[str, Any]) -> dict[str, Any]:
    """Convert ls Transfer entry to IRI entry."""

    try:
        # Filter to only keep relevant keys
        formatted_entry = {
            key: ls_entry[key]
            for key in (
                "name",
                "type",
                "link_target",
                "user",
                "group",
                "permissions",
                "last_modified",
                "size",
            )
        }

        # Adjust formatting
        formatted_entry["permissions"] = stat.filemode(int(formatted_entry["permissions"], 8))[1:]
        formatted_entry["size"] = str(formatted_entry["size"])

        # Return IRI-compliant formated entry
        return formatted_entry
    
    # Error handling
    except Exception as e:
        error_message = generate_error_message("Could format Globus Transfer ls entry.", e)
        raise HTTPException(
            status_code=500, 
            detail=error_message
        )