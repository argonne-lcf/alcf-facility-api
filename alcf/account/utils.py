from asyncache import cached
from cachetools import TTLCache

from starlette.status import HTTP_400_BAD_REQUEST
from fastapi import HTTPException

from alcf.endpoints import get_endpoint
from alcf.enums import EndpointType, APIComponent, AllType
from alcf.httpx_client import AsyncHttpClient
from alcf.config import ACCOUNT_REQUEST_TIMEOUT_SEC


def get_ni_rest_api_url() -> str:
    """Get URL for the Ni REST API for accounting tasks."""

    # Extract GraphQL endpoint for the targetted resource
    ni_rest_api_endpoint = get_endpoint(
        api_component=APIComponent.ACCOUNT.value,
        resource_name=AllType.ALL.value,
        operation=AllType.ALL.value
    )

    # Return Ni REST API URL
    if ni_rest_api_endpoint.endpoint_type == EndpointType.NI_REST_API.value:    
        return ni_rest_api_endpoint.url
    else:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, 
            detail=f"Endpoint for Account is not a Ni REST API endpoint."
        )
    

# TODO: introduce reusable Redis caching functions with in-memory fallback
@cached(cache=TTLCache(maxsize=1024, ttl=600))
async def get_ni_rest(
    url: str = None,
    access_token: str = None,
) -> dict:
    """Make an authenticated POST call to the Ni REST API"""

    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    httpx_client = AsyncHttpClient(
        timeout=ACCOUNT_REQUEST_TIMEOUT_SEC,
        headers=headers
    )

    return await httpx_client.get(url)