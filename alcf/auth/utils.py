from enum import Enum
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
from typing import Optional, List, Tuple
import globus_sdk
import time
from cachetools import TTLCache, cached

# Tool to log access requests
import logging
log = logging.getLogger(__name__)

# Auth services
class AuthServices(Enum):
    globus = "Globus"
    keycloak = "Keycloak"

# Keycloak input token flag
KEYCLOAK_FLAG = "keycloak_flag_"

# Helper allowed domain error message
ALLOWED_DOMAIN_STR = f"Make sure you authenticate with {AUTHORIZED_IDP_DOMAIN}."

# Helper logout error message
LOGOUT_MESSAGE_STR = ""
LOGOUT_MESSAGE_STR += "Please logout by visiting https://app.globus.org/logout "
LOGOUT_MESSAGE_STR += "and re-authenticate. Use an incognito browser or clear "
LOGOUT_MESSAGE_STR += "browser cache to make sure you can enter your credentials."

class GlobusDependentTokens(BaseModel):
    group: str = None
    compute: str = None
    transfer: str = None

class UserPydantic(BaseModel):
    id: str
    name: str
    username: str
    user_group_uuids: List[str] = Field(default_factory=lambda: [])
    idp_id: str
    idp_name: str
    auth_service: str

class TokenValidationResponse(BaseModel):
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

    # Set short cache time if an error is triggered
    if result[0] is None:
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
        error_message = f"Could not create Globus confidential client."
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
        error_message = f"Could not introspect token with Globus /v2/oauth2/token/introspect. {LOGOUT_MESSAGE_STR}"
        log.warning(error_message)
        return None, [], None, error_message
    
    # Make sure the token is valid/active
    if introspection.get("active", False) is False:
        error_message = f"Globus token not active. {LOGOUT_MESSAGE_STR}"
        log.warning(error_message)
        return None, [], None, error_message
    
    # Get dependent access tokens
    try:
        dependent_tokens_response = client.oauth2_get_dependent_tokens(access_token)
        dependent_tokens = GlobusDependentTokens()
    except Exception:
        error_message = f"Could not recover dependent access tokens."
        log.warning(error_message)
        return None, [], None, error_message
    
    # Exract Globus Group token
    try:
        dependent_tokens.group = dependent_tokens_response["groups.api.globus.org"]["access_token"]
    except Exception:
        error_message = f"Could not recover Globus Group access token from dependent tokens."
        log.warning(error_message)
        return None, [], None, error_message
    
    # Exract Globus Compute token
    try:
        dependent_tokens.compute = dependent_tokens_response["funcx_service"]["access_token"]
    except Exception:
        error_message = f"Could not recover Globus Compute access token from dependent tokens."
        log.warning(error_message)
        return None, [], None, error_message
    
    # Extract Globus Transfer token (with no fail to allow not break existing user workflow)
    try:
        dependent_tokens.transfer = dependent_tokens_response["transfer.api.globus.org"]["access_token"]
    except Exception:
        error_message = f"Could not recover Globus Compute access token from dependent tokens."
        log.warning(error_message)
        # [TEMPORARY] No fail to allow not break existing user workflow
        # return None, [], None, error_message
        dependent_tokens.transfer = None

    # Create a Globus Group Client using the access token sent by the user
    try:
        authorizer = globus_sdk.AccessTokenAuthorizer(dependent_tokens.group)
        groups_client = globus_sdk.GroupsClient(authorizer=authorizer)
    except Exception as e:
        error_message = f"Could not create GroupsClient."
        log.warning(error_message)
        return None, [], None, error_message

    # Get the list of user's group memberships
    try:
        user_groups_response = groups_client.get_my_groups()
        user_groups = [group["id"] for group in user_groups_response]
    except Exception as e:
        error_message = f"Could not recover user group memberships."
        log.warning(error_message)
        return None, [], None, error_message
        
    # Return the introspection data along with the group and compute token (with empty error message)
    return introspection_data, user_groups, dependent_tokens, ""


# Get session info identities
def get_session_info_identities(introspection) -> Tuple[List[dict], str]:
    """
    Look into the session_info field of the token introspection
    and collect the identities that are present. 
    Returns list of identities and error message if any.
    """

    # Return nothing if no authentication is found
    if "authentications" not in introspection["session_info"]:
        return [], ""

    # Initialize list of identities present in the session_info introspection field
    session_info_identities = []

    # Attempt to collect identities
    try:

        # For each active authentication session ...
        for session_idp in [auth["idp"] for auth in introspection["session_info"]["authentications"].values()]:

            # Recover the identity data tied to the active session
            identity = next((i for i in introspection["identity_set_detail"] if i["identity_provider"] == session_idp))
            session_info_identities.append(identity)
            
    # Error message if identities could not be recovered
    except Exception:
        return None, "Could not recover list of identities from session_info."
    
    # Return list of identities without any error
    return session_info_identities, ""


# Get user details
def get_user_details(session_info_identities, user_groups) -> Tuple[UserPydantic, str]:
    """
    Look at session_info_identities and check whether the
    authentication was made through one of the authorized identity providers.
    Collect and return the User details if possible along with error message if any.
    """

    # Attempt to find an authorized identity
    try:

        # For each identity tied to the session info ...
        for identity in session_info_identities:

            # Collect identity domain (e.g, alcf.anl.gov)
            session_username = identity["username"]
            session_domain = session_username.split("@")[1]

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
                        auth_service=AuthServices.globus.value
                    ), ""
                except Exception as e:
                    return None, f"Could not create UserPydantic instance for {session_username}."
            
    # Error if something went wrong
    except Exception:
        return None, "Could not scan through list of identities tied to session_info."
    
    # Build list of session_info usernames that are not authorized (in string form)
    try:
        user_str = []
        for identity in session_info_identities:
            user_str.append(f"{identity['name']} ({identity['username']})")
        user_str = ", ".join(user_str)
        if len(user_str) == 0:
            user_str = "Unknown (no active session found)"
    except Exception:
        return None, "Could not gather user_str for unauthorized identities."

    # Error message if no authorized identity were found
    error_message = ""
    error_message += f"{ALLOWED_DOMAIN_STR} "
    error_message += f"Currently authenticated as {user_str}."
    return None, error_message


# Validate access token sent by user
def validate_access_token(access_token) -> TokenValidationResponse:
    """This function returns an instance of the TokenValidationResponse pydantic data structure."""

    # Introspect the access token
    introspection, user_groups, dependent_tokens, error_message = introspect_token(access_token)
    if len(error_message) > 0:
        return TokenValidationResponse(
            is_authorized=False,
            user=None,
            error_message=error_message
        )
    
    # Make sure the token is not expired
    expires_in = introspection["exp"] - time.time()
    if expires_in <= 0:
        return TokenValidationResponse(
            is_authorized=False,
            user=None,
            error_message=f"Globus token expired. {LOGOUT_MESSAGE_STR}"
        )
    
    # Gather list of identities from session_info
    session_info_identities, error_message = get_session_info_identities(introspection)
    if len(session_info_identities) == 0:
        return TokenValidationResponse(
            is_authorized=False,
            user=None,
            error_message=f"No identity found in the session info. {LOGOUT_MESSAGE_STR}"
        )
    if error_message:
        return TokenValidationResponse(
            is_authorized=False,
            user=None,
            error_message=error_message
        )

    # Gather the user details
    user, error_message = get_user_details(session_info_identities, user_groups)
    if error_message:
        return TokenValidationResponse(
            is_authorized=False,
            user=None,
            error_message=f"{error_message} {LOGOUT_MESSAGE_STR}"
        )
    
    # Make sure the Globus high-assurance policy is respected
    for policies in introspection["policy_evaluations"].values():
        if policies.get("evaluation", False) == False:
            error_message = ""
            error_message += "Authentication not compliant with Globus policy, "
            error_message += f"likely due to a high-assurance timeout. {LOGOUT_MESSAGE_STR} {ALLOWED_DOMAIN_STR}"
            return TokenValidationResponse(
                is_authorized=False,
                user=None,
                error_message=error_message
            )
        
    # Make sure the user is part of the Globus Group
    if GLOBUS_GROUP:
        if GLOBUS_GROUP not in user_groups:
            return TokenValidationResponse(
                is_authorized=False,
                user=None,
                error_message=f"User {user.username} not in the authorized Globus Group. Please contact adminstrators."
            )
    
    # Return the user details
    return TokenValidationResponse(
        is_authorized=True,
        user=user
    )
