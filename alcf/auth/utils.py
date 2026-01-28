from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR 
import globus_sdk
from alcf.config import (
    GLOBUS_SERVICE_API_CLIENT_ID, 
    GLOBUS_SERVICE_API_CLIENT_SECRET, 
    GLOBUS_HA_POLICY,
    GLOBUS_GROUP,
    AUTHORIZED_IDP_DOMAIN
)
from alcf.cache.redis import get_redis_client
import json
import hashlib
from pydantic import BaseModel, Field
from typing import Optional, List
import globus_sdk
import time
from cachetools import TTLCache, cached

# Tool to log access requests
import logging
log = logging.getLogger(__name__)

 
class UserPydantic(BaseModel):
    id: str
    name: str
    username: str
    user_group_uuids: List[str] = Field(default_factory=lambda: [])
    idp_id: str
    idp_name: str
    auth_service: str
    access_token: str = None

class TokenValidationResponse(BaseModel):
    is_valid: bool = False
    is_authorized: bool = False
    user: Optional[UserPydantic] = None

# Get Globus SDK confidential client
def get_globus_service_api_client():
    return globus_sdk.ConfidentialAppAuthClient(
        GLOBUS_SERVICE_API_CLIENT_ID, 
        GLOBUS_SERVICE_API_CLIENT_SECRET
    )


# Introspect token
def introspect_token(access_token: str):
    """
    Introspect a token with policies, collect group memberships, and return the response.
    Uses Redis cache for multi-worker support with fallback to in-memory cache.
    
    Returns serializable data instead of Globus SDK objects.
    """
    
    # Create cache key from token hash
    # Store the entire hash to avoid collisions where different users would have the same last hash digits
    token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    cache_key = f"token_introspect:{token_hash}"
    
    # Try to get introspection from cache first
    try:
        redis_client = get_redis_client()
        if redis_client:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        
    # Fall back to in-memory cache if needed
    except Exception as e:
        log.warning(f"Redis cache error for token introspection: {e}")
        return _introspect_token_memory_cache(access_token)

    # Perform the token introspection if not taken from the cache
    result = _perform_token_introspection(access_token)

    # If the introspection triggered an error ...
    if result[0] is None:

        # Set cache time (shorter for errors)
        ttl = 60

    # If the introspection was successful ...
    else:

        # Calculate time until token expiration (Unix timestamp difference)
        try:
            introspection_exp = result[0]["exp"]
            seconds_until_expiration = introspection_exp - int(time.time())
        except Exception as e:
            log.warning(f"Failed to extract introspection result[0]['exp']: {e}")
            seconds_until_expiration = 0

        # Set cache time and make sure it is not shorter than the time until token expiration
        ttl = min(600, seconds_until_expiration)
    
    # Cache the result (successful or error)
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.setex(cache_key, ttl, json.dumps(result))
    except Exception as e:
        log.warning(f"Failed to cache token introspection: {e}")
        # Still return the result even if caching fails
    
    return result


# Introspect token memory cache
@cached(cache=TTLCache(maxsize=1024, ttl=60*10))
def _introspect_token_memory_cache(access_token: str):
    """
    Fallback in-memory cache for token introspection
    """
    return _perform_token_introspection(access_token)


# Perform token introspection
def _perform_token_introspection(access_token: str):
    """
    Perform the actual token introspection and return serializable data.
    """

    # Create Globus SDK confidential client
    try:
        client = get_globus_service_api_client()
    except Exception as e:
        return None, [], None, f"Could not create Globus confidential client. {e}"

    # Prepare the introspection data
    introspect_body = {
        "token": access_token,
        "authentication_policies": GLOBUS_HA_POLICY,
        "include": "session_info,identity_set_detail"
    }

    # Introspect token and convert response into a serializable dictionary for caching
    try: 
        introspection = client.post("/v2/oauth2/token/introspect", data=introspect_body, encoding="form")
        introspection_data = dict(introspection.data) if hasattr(introspection, 'data') else dict(introspection)
    except Exception as e:
        return None, [], None, f"Could not introspect token with Globus /v2/oauth2/token/introspect. {e}"
    
    # Make sure the token is valid/active
    if introspection.get("active", False) is False:
        return None, [], None, f"Token not active."
    
    # Get dependent access token to view group membership and use Globus Compute
    try:
        dependent_tokens = client.oauth2_get_dependent_tokens(access_token)
        access_token = dependent_tokens.by_resource_server["groups.api.globus.org"]["access_token"]
        globus_compute_access_token = dependent_tokens.by_resource_server["funcx_service"]["access_token"]
    except Exception as e:
        return None, [], None, f"Could not recover dependent access tokens. {e}"

    # Create a Globus Group Client using the access token sent by the user
    try:
        authorizer = globus_sdk.AccessTokenAuthorizer(access_token)
        groups_client = globus_sdk.GroupsClient(authorizer=authorizer)
    except Exception as e:
        return None, [], None, f"Could not create GroupsClient. {e}"

    # Get the list of user's group memberships
    try:
        user_groups_response = groups_client.get_my_groups()
        user_groups = [group["id"] for group in user_groups_response]
    except Exception as e:
        return None, [], None, f"Could not recover user group memberships. {e}"
        
    # Return the introspection data along with the group and compute token (with empty error message)
    return introspection_data, user_groups, globus_compute_access_token, ""


# Get user details
def get_user_details(introspection, user_groups) -> UserPydantic:
    """
        Look into the session_info field of the token introspection
        and check whether the authentication was made through one 
        of the authorized identity providers. Collect and return the
        User details if possible
    """

    # Try to check if an authentication came from authorized provider
    try:

        # For each active authentication session ...
        session_info_identities = []
        for session_idp in [auth["idp"] for auth in introspection["session_info"]["authentications"].values()]:

            # Recover the domain (e.g. anl.gov) tied to the active session
            identity = next((i for i in introspection["identity_set_detail"] if i["identity_provider"] == session_idp))
            session_domain = identity["username"].split("@")[1]
            session_info_identities.append(identity)

            # If the domain is authorized by the service ...
            if session_domain in AUTHORIZED_IDP_DOMAIN:

                # Create and return the User object from the Globus introspection
                try:
                    return UserPydantic(
                        id=identity["sub"],
                        name=identity["name"] if isinstance(identity["name"], str) else "",
                        username=identity["username"],
                        user_group_uuids=user_groups,
                        idp_id=identity["identity_provider"],
                        idp_name=identity["identity_provider_display_name"],
                        auth_service="Globus"
                    )
                except Exception as e:
                    return None
            
    # No user if something went wrong
    except Exception as e:
        return None
    
    # No user if no authorized session was found
    return None


# Validate access token sent by user
def validate_access_token(access_token):
    """This function returns an instance of the TokenValidationResponse pydantic data structure."""

    # Introspect the access token
    introspection, user_groups, globus_compute_access_token, error_message = introspect_token(access_token)
    if len(error_message) > 0:
        return TokenValidationResponse(
            is_valid=False, 
            is_authorized=False,
            user=None
        )

    # Make sure the token is not expired
    expires_in = introspection["exp"] - time.time()
    if expires_in <= 0:
        return TokenValidationResponse(
            is_valid=False, 
            is_authorized=False,
            user=None
        )
    
    # Make sure the Globus high-assurance policy is respected
    for policies in introspection["policy_evaluations"].values():
        if policies.get("evaluation", False) == False:
            return TokenValidationResponse(
                is_valid=True,
                is_authorized=False,
                user=None
            )
        
    # Make sure the user is part of the Globus Group
    if GLOBUS_GROUP:
        if GLOBUS_GROUP not in user_groups:
            return TokenValidationResponse(
                is_valid=True,
                is_authorized=False,
                user=None
            )
        
    # Gather the user details
    user = get_user_details(introspection, user_groups)
    if user is None or len(user.username) == 0:
        return TokenValidationResponse(
            is_valid=True,
            is_authorized=False,
            user=None
        )
    
    # Add Globus Compute access token to the user details
    user.access_token = globus_compute_access_token
    
    # Return the user details
    return TokenValidationResponse(
        is_valid=True,
        is_authorized=True,
        user=user
    )
