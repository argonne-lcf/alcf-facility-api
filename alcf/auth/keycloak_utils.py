import httpx
from fastapi import HTTPException
from json.decoder import JSONDecodeError
from app.types.user import User
from alcf.auth.utils import (
    generate_error_message,
    get_alcf_username_from_token,
)
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
)
from alcf.cache.manager import cache_manager

# Keycloak URL to generate and exchange tokens
KEYCLOAK_TOKEN_ENDPOINT_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM_NAME}/protocol/openid-connect/token"

# Prepare request headers
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded"
}


# Make actual post requests to Keycloak
@cache_manager.cached(ttl=600)
def post_keycloak(payload: dict = None, url: str = None):
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
        error_message = generate_error_message("Keycloak query response could not be parsed.", e)
        return None, error_message
    except Exception as e:
        error_message = generate_error_message("Keycloak query failed.", e)
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
    user: User = None
    ) -> str:
    """
    Take the already-vetted pydantic user object and attempt to generate a 
    Keycloak access token on their behalf.
    """

    # Recover ALCF username from the Globus introspection
    alcf_username, error_message = get_alcf_username_from_token(user.api_key)
    if error_message:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"GraphQL pre-submission error: {error_message}"
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

