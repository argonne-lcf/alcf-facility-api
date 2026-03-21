import time
import httpx
from fastapi import HTTPException
from alcf.cache.redis import get_redis_client
from cachetools import TTLCache, cached
import hashlib
import json
from json.decoder import JSONDecodeError
from app.routers.account import models as account_models
from alcf.auth.utils import introspect_token as globus_introspect_token
from app.config import logger
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
)
from alcf.config import (
    KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_ID,
    KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_SECRET,
    KEYCLOAK_REALM_NAME,
    KEYCLOAK_PBS_GRAPHQL_AUDIENCE,
    KEYCLOAK_SERVER_URL,
    KEYCLOAK_ID_TOKEN_CLIENT_ID
)

# Keycloak URL to generate and exchange tokens
KEYCLOAK_TOKEN_ENDPOINT_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM_NAME}/protocol/openid-connect/token"

# Prepare request headers
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded"
}


# Post request to Keycloak (using Redis cache)
def post_keycloak(payload: dict = None, url: str = None):
    """
    Post request to Keycloak server.
    Uses Redis cache for multi-worker support with fallback to in-memory cache.
    Returns serializable data.
    """
    
    # Create cache key from token hash
    # Store the entire hash to avoid collisions where different users would have the same last hash digits
    input_str = f"{json.dumps(payload)}-{url}"
    token_hash = hashlib.sha256(input_str.encode()).hexdigest()
    cache_key = f"post_keycloak:{token_hash}"
    
    # Try to get post result from cache first
    try:
        redis_client = get_redis_client()
        if redis_client:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        
    # Fall back to in-memory cache if needed
    except Exception as e:
        logger.warning(f"Redis cache error for post request to Keycloak: {e}")
        return _post_keycloak_memory_cache(payload=payload, url=url)

    # Perform the token introspection if not taken from the cache
    result = _perform_post_keycloak(payload=payload, url=url)

    # Set short cache time if an error is triggered
    if result[0] is None:
        ttl = 60

    # If the post request was successful ...
    else:

        # Calculate time until token expiration (Unix timestamp difference)
        if "exp" in result[0]:
            seconds_until_expiration = result[0]["exp"] - int(time.time())
        else:
            seconds_until_expiration = 600

        # Set cache time and make sure it is not shorter than the time until token expiration
        ttl = min(600, seconds_until_expiration)
    
    # Cache the result (successful or error)
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.setex(cache_key, ttl, json.dumps(result))
    except Exception as e:
        logger.warning(f"Failed to cache post request to Keycloak: {e}")
        # Still return the result even if caching fails
    
    return result


# Post request to Keycloak (using fallback in-memory cache)
@cached(cache=TTLCache(maxsize=1024, ttl=60*10))
def _post_keycloak_memory_cache(payload: dict = None, url: str = None):
    return _perform_post_keycloak(payload=payload, url=url)


# Make actual post requests to Keycloak
def _perform_post_keycloak(payload: dict = None, url: str = None):
    """
    Do not raise exception here so that we can cache repeated errors.
    """

    # Make query to Keycloak
    try:
        with httpx.Client() as client:
            response = client.post(
                url,
                data=payload,
                headers=HEADERS,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json(), None
        
    # Handle errors
    except httpx.TimeoutException:
        error_message = "Keycloak query timed out."
        logger.exception(error_message)
        return None, error_message
    except JSONDecodeError as e:
        error_message = "Keycloak query response could not be parsed."
        logger.exception(error_message)
        return None, error_message
    except Exception as e:
        error_message = "Keycloak query failed."
        logger.exception(error_message)
        return None, error_message


# Get impersonation token
def get_keycloak_impersonation_client_token():

    # Post request to Keycloak
    post_response, error_message = post_keycloak(
        payload={
            "grant_type": "client_credentials",
            "client_id": KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_ID,
            "client_secret": KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_SECRET,
        },
        url=KEYCLOAK_TOKEN_ENDPOINT_URL
    )

    # Error message
    if error_message:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"get_keycloak_impersonation_client_token: {error_message}"
        )
    
    # Return request response if no error occured
    return post_response


# Get user token
def get_impersonated_user_token(subject_token: str = None, requested_subject: str = None):
    
    # Post request to Keycloak
    post_response, error_message = post_keycloak(
        payload={
            "client_id": KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_ID,
            "client_secret": KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_SECRET,
            "subject_token": subject_token,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "requested_subject": requested_subject,
            "audience": KEYCLOAK_PBS_GRAPHQL_AUDIENCE,
        },
        url=KEYCLOAK_TOKEN_ENDPOINT_URL
    )

    # Error message
    if error_message:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"get_impersonated_user_token: {error_message}"
        )
    
    # Return request response if no error occured
    return post_response


# Introspect token
def introspect_token(token: str = None):
    
    # Post request to Keycloak
    post_response, error_message = post_keycloak(
        payload={
            "client_id": KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_ID,
            "client_secret": KEYCLOAK_IMPERSONATION_SERVICE_CLIENT_SECRET,
            "token": token
        },
        url=f"{KEYCLOAK_TOKEN_ENDPOINT_URL}/introspect"
    )

    # Error message
    if error_message:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"introspect_token: {error_message}"
        )
    
    # Return request response if no error occured
    return post_response


# Generate user Keycloak token
def generate_user_keycloak_token(
    user: account_models.User = None
    ) -> str:
    """
    Take the already-vetted pydantic user object and attempt to generate a 
    Keycloak access token on their behalf.
    """

    # Recover the Globus token introspection from cache
    globus_introspection, _, _, error_message = globus_introspect_token(user.api_key)
    if len(error_message) > 0:
        logger.error(f"generate_user_keycloak_token: {error_message}")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Could not recover Globus token introspection in the context of GraphQL submission."
        )
    
    # Try to extract the original Keycloak ID token from Globus introspection
    id_token = globus_introspection["session_info"].get("id_token", None)
    if id_token is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Could not extract original ID token from Globus introspection."
        )
    
    # Try to introspect the ID token
    id_token_introspection = introspect_token(id_token)
    if id_token_introspection is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not introspect ID token with Keycloak."
        )
    
    # Error if Keycloak ID token is not valid
    if id_token_introspection.get("active", False) == False:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Keycloak ID token not valid or expired. Try to re-authenticate."
        )
    
    # Verify origin of the Keycloak ID token
    if id_token_introspection.get("client_id", "unknown_client_id") != KEYCLOAK_ID_TOKEN_CLIENT_ID:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Unrecognized source client for Keycloak ID token generation."
        )

    # Extract the ALCF username from the Keycloak ID token
    alcf_username = id_token_introspection.get("username", None)
    if alcf_username == "" or alcf_username is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Could not recover ALCF username from Keycloak ID token."
        )
    
    # Get Keycloak impersonation client token from credentials
    impersonation_token_response = get_keycloak_impersonation_client_token()
    impersonation_access_token = impersonation_token_response.get("access_token", None)
    if impersonation_access_token is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Could not generate Keycloak access token from client credentials."
        )
        
    # Generate Keycloak access token for the user
    user_token_response = get_impersonated_user_token(
        subject_token=impersonation_access_token, 
        requested_subject=alcf_username
    )
    user_access_token = user_token_response.get("access_token", None)
    if user_access_token is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Could not generate user access token using Keycloak client credentials."
        )

    # Return the user access token
    return user_access_token

