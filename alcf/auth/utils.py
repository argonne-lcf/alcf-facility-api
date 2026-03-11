from fastapi import HTTPException
import requests
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR 
import globus_sdk
from alcf.config import (
    GLOBUS_SERVICE_API_CLIENT_ID, 
    GLOBUS_SERVICE_API_CLIENT_SECRET, 
    GLOBUS_HA_POLICY,
    GLOBUS_GROUP,
    AUTHORIZED_IDP_DOMAIN,
    GLOBUS_AMSC_CLIENT_ID,
    GLOBUS_AMSC_CLIENT_SECRET,
    GLOBUS_AMSC_AUTHORIZED_USERNAMES
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

# Maximum allowed length for a Globus access token
MAX_GLOBUS_TOKEN_LENGTH = 130
 
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
    error_message: Optional[str] = None


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
        error_message = f"Could not create Globus confidential client. {e}"
        log.warning(error_message)
        return None, [], None, error_message

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
        error_message = f"Could not introspect token with Globus /v2/oauth2/token/introspect. {e}"
        log.warning(error_message)
        return None, [], None, error_message
    
    # Make sure the token is valid/active
    if introspection.get("active", False) is False:
        error_message = f"Globus token not active."
        log.warning(error_message)
        return None, [], None, error_message
    
    # Get dependent access token to view group membership and use Globus Compute
    try:
        dependent_tokens = client.oauth2_get_dependent_tokens(access_token)
        access_token = dependent_tokens.by_resource_server["groups.api.globus.org"]["access_token"]
        globus_compute_access_token = dependent_tokens.by_resource_server["funcx_service"]["access_token"]
    except Exception as e:
        error_message = f"Could not recover dependent access tokens. {e}"
        log.warning(error_message)
        return None, [], None, error_message

    # Create a Globus Group Client using the access token sent by the user
    try:
        authorizer = globus_sdk.AccessTokenAuthorizer(access_token)
        groups_client = globus_sdk.GroupsClient(authorizer=authorizer)
    except Exception as e:
        error_message = f"Could not create GroupsClient. {e}"
        log.warning(error_message)
        return None, [], None, error_message

    # Get the list of user's group memberships
    try:
        user_groups_response = groups_client.get_my_groups()
        user_groups = [group["id"] for group in user_groups_response]
    except Exception as e:
        error_message = f"Could not recover user group memberships. {e}"
        log.warning(error_message)
        return None, [], None, error_message
        
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
            if session_domain == AUTHORIZED_IDP_DOMAIN:

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

    # Ignore tokens that are too long (likely Keycloak tokens)
    if len(access_token) > MAX_GLOBUS_TOKEN_LENGTH:
        log.warning(f"Access token ignored with Globus (token too long).")
        return TokenValidationResponse(
            is_valid=False, 
            is_authorized=False,
            user=None
        )

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
                user=None,
                error_message="User authentication is not compliant with the adopted Globus policy."
            )
        
    # Make sure the user is part of the Globus Group
    if GLOBUS_GROUP:
        if GLOBUS_GROUP not in user_groups:
            return TokenValidationResponse(
                is_valid=True,
                is_authorized=False,
                user=None,
                error_message="User not in the authorized Globus Group."
            )
        
    # Gather the user details
    user = get_user_details(introspection, user_groups)
    if user is None or len(user.username) == 0:
        return TokenValidationResponse(
            is_valid=True,
            is_authorized=False,
            user=None,
            error_message="User details could not be recovered from Globus token introspection."
        )
    
    # Add Globus Compute access token to the user details
    user.access_token = globus_compute_access_token
    
    # Return the user details
    return TokenValidationResponse(
        is_valid=True,
        is_authorized=True,
        user=user
    )


# ====================
# ==== AmSC demo =====
# ====================

# AmSC demo instrospection responses
def amsc_demo_userinfo_introspection(access_token: str):
    """
    Get userinfo and introspection details from Globus Auth.
    Uses Redis cache for multi-worker support with fallback to in-memory cache.
    Returns serializable data instead of Globus SDK objects.
    """
    
    # Create cache key from token hash
    # Store the entire hash to avoid collisions where different users would have the same last hash digits
    token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    cache_key = f"token_amsc_introspection:{token_hash}"
    
    # Try to get userinfo from cache first
    try:
        redis_client = get_redis_client()
        if redis_client:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                log.info("Taking amsc demo userinfo/introspection from cache.")
                return json.loads(cached_data)
        
    # Fall back to in-memory cache if needed
    except Exception as e:
        log.warning(f"Redis cache error for token introspection: {e}")
        return _get_amsc_demo_introspection_memory_cache(access_token)

    # Perform the userinfo/introspection calls if not taken from the cache
    result = _perform_get_amsc_demo_introspection(access_token)

    # If the userinfo/introspection calls triggered an error ...
    if result[0] is None:

        # Set cache time (shorter for errors)
        ttl = 60

    # If the userinfo/introspection calls was successful ...
    else:
        introspection = result[0].get("introspection", {})

        # Calculate time until token expiration (Unix timestamp difference)
        try:
            exp = introspection["exp"]
            seconds_until_expiration = exp - int(time.time())
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
        log.info("Succesfully cached amsc demo userinfo/introspection results.")
    except Exception as e:
        log.warning(f"Failed to cache amsc demo userinfo/introspection results: {e}")
        # Still return the result even if caching fails
    
    return result


# AmSC introspection calls using python memory cache
@cached(cache=TTLCache(maxsize=1024, ttl=60*10))
def _get_amsc_demo_introspection_memory_cache(access_token: str):
    """
    Fallback in-memory cache for userinfo/introspection calls
    """
    return _perform_token_introspection(access_token)


# Perform AmSC introspection calls
def _perform_get_amsc_demo_introspection(access_token: str):
    """
    Perform the actual userinfo/introspection calls and return serializable data.
    """

    # Create client for token userinfo call
    try:
        userinfo_client = globus_sdk.AuthClient(authorizer=globus_sdk.AccessTokenAuthorizer(access_token))
        userinfo = userinfo_client.userinfo()
    except Exception as e:
        error_message = "Could not recover userinfo from token."
        log.warning(error_message)
        return None, error_message
        
    # Create client for token introspection call
    introspection_client = globus_sdk.ConfidentialAppAuthClient(
        GLOBUS_AMSC_CLIENT_ID,
        GLOBUS_AMSC_CLIENT_SECRET
    )

    # Introspect access token
    try:
        introspection = introspection_client.oauth2_token_introspect(access_token)
    except Exception as e:
        error_message = "Could not recover introspection from token."
        log.warning(error_message)
        return None, error_message
    
    # Prepare and return results
    inserinfo_introspection = {
        "userinfo": dict(userinfo.data),
        "introspection": dict(introspection.data)
    }
    return inserinfo_introspection, ""


# Validate AmSC demo access token sent by user
def validate_amsc_demo_access_token(access_token):
    """This function returns an instance of the TokenValidationResponse pydantic data structure."""

    # Ignore tokens that are too long (likely Keycloak tokens)
    if len(access_token) > MAX_GLOBUS_TOKEN_LENGTH:
        log.warning(f"Access token ignored with Globus (token too long).")
        return TokenValidationResponse(
            is_valid=False, 
            is_authorized=False,
            user=None
        )

    # Introspect the access token
    userinfo_introspection, error_message = amsc_demo_userinfo_introspection(access_token)
    if len(error_message) > 0:
        return TokenValidationResponse(
            is_valid=False, 
            is_authorized=False,
            user=None
        )
    
    # Split userinfo and introspection
    userinfo = userinfo_introspection.get("userinfo", {})
    introspection = userinfo_introspection.get("introspection", {})
    name = userinfo.get("name", "Unknown")
    
    # Make sure the token is valid/active
    if introspection.get("active", False) is False:
        log.warning("AmSC Globus token not active.")
        return TokenValidationResponse(
            is_valid=False, 
            is_authorized=False,
            user=None
        )
    
    # Make sure the token is not expired
    expires_in = introspection.get("exp", -1) - time.time()
    if expires_in <= 0:
        log.warning("AmSC Globus token expired.")
        return TokenValidationResponse(
            is_valid=False, 
            is_authorized=False,
            user=None
        )
    
    # Isolate the ALCF identity in the list of linked identities
    alcf_identity = None
    alcf_username = None
    for identity in userinfo.get("identity_set", []):
        username = identity.get("username", "")
        if username.count("@") == 1 and "@alcf.anl.gov" in username:
            alcf_identity = identity
            alcf_username = username
            break
    
    # Unauthorized if no ALCF identity is found
    if alcf_identity is None:
        log.warning(f"User {name} does not have a linked ALCF identity.")
        return TokenValidationResponse(
            is_valid=True, 
            is_authorized=False,
            user=None
        )

    # Make sure the user is in the list of authorized identities
    if alcf_username not in GLOBUS_AMSC_AUTHORIZED_USERNAMES:
        log.warning(f"User {alcf_username} not in the list of authorized AmSC demo users.")
        return TokenValidationResponse(
            is_valid=True, 
            is_authorized=False,
            user=None
        )

    # Verify the token issuer
    aud = introspection.get("aud", [])
    if "auth.globus.org" not in aud or GLOBUS_AMSC_CLIENT_ID not in aud:
        log.warning(f"AmSC Globus token issued by an unauthorized client.")
        return TokenValidationResponse(
            is_valid=True, 
            is_authorized=False,
            user=None
        )
        
    # Gather the user details
    user = UserPydantic(
        id=alcf_identity["sub"],
        name=alcf_identity["name"] if isinstance(identity["name"], str) else "",
        username=alcf_identity["username"],
        user_group_uuids=[],
        idp_id=alcf_identity["identity_provider"],
        idp_name=alcf_identity["identity_provider_display_name"],
        auth_service=f"Globus AmSC Demo with client ID {GLOBUS_AMSC_CLIENT_ID}"
    )
    
    # Return the user details
    return TokenValidationResponse(
        is_valid=True,
        is_authorized=True,
        user=user
    )
