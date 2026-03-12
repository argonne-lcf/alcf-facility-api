from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
from app.routers.iri_router import AuthenticatedAdapter
from app.routers.account.models import User
from alcf.config import KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET, KEYCLOAK_REALM_NAME, KEYCLOAK_SERVER_URL
from keycloak import KeycloakOpenID
from alcf.auth.utils import validate_access_token, validate_amsc_demo_access_token, TokenValidationResponse
from alcf.database.database import exists_in_db, add_user_to_db, get_db_user_from_id
from alcf.database import models as db_models
from alcf.config import (
    KEYCLOAK_ENABLED,
    KEYCLOAK_AUTHORIZED_USERNAMES,
    GLOBUS_AUTHORIZED_USERNAMES,
    GLOBUS_AMSC_AUTHORIZED_USERNAMES,
)
import logging

log = logging.getLogger(__name__)

# [TEMPORARY]
AMSC_DEMO_FLAG = "-amsc-demo"

# Configure Keycloak client
if KEYCLOAK_ENABLED:
    keycloak_openid = KeycloakOpenID(
        server_url=KEYCLOAK_SERVER_URL,
        client_id=KEYCLOAK_CLIENT_ID,
        realm_name=KEYCLOAK_REALM_NAME,
        client_secret_key=KEYCLOAK_CLIENT_SECRET,
        verify=True
    )
    config_well_known = keycloak_openid.well_known()


class AlcfAuthenticatedAdapter(AuthenticatedAdapter):

    # Get current user
    async def get_current_user(
        self : "AlcfAuthenticatedAdapter",
        api_key: str,
        ip_address: str = None,
        ) -> str:
        """
        Decode the api_key and return the authenticated user's id.
        This method is not called directly, rather authorized endpoints "depend" on it.
        (https://fastapi.tiangolo.com/tutorial/dependencies/)
        """

        # Clean API key
        api_key = api_key.replace("Bearer ", "")

        # Auth for Globus AmSC demo token ...
        # -----------------------------------

        # AmSC demo token userinfo details
        #amsc_demo_token_response = validate_amsc_demo_access_token(api_key)

        # Try to extract the user ID (will only return the ID if authorized)
        #if amsc_demo_token_response.is_valid:
        #    user_id = await self.__get_authorized_globus_user_id(amsc_demo_token_response)
        #    if user_id:
        #        return user_id+AMSC_DEMO_FLAG

    
        # Auth for Facility Globus token
        # ------------------------------

        # Try to validate the API key with Globus Auth
        token_response = validate_access_token(api_key)

        # Try to extract the user ID (will only return the ID if authorized)
        if token_response.is_valid:
            user_id = await self.__get_authorized_globus_user_id(token_response)
            if user_id:
                return user_id
        
        # If this is a Keyckoak token ...
        # -------------------------------
        
        # Only if Keycloak is enabled ...
        if KEYCLOAK_ENABLED:

            # Try to validate the API key with Keycloak
            # TODO: Cache this
            try:
                introspection = keycloak_openid.introspect(api_key)
            except Exception:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail=f"Could not introspect token with Keycloak."
                )

            # If the token is a valid Keycloak token ...
            if introspection.get("active", False):

                # Give permission to continue through the API if appropriate
                # TODO look for ID instead
                user_id = introspection.get("username", None)
                
                # Store user in database if not already present
                try:
                    if not await exists_in_db(user_id, db_models.User):
                        await add_user_to_db({
                            "id": user_id,
                            "name": introspection.get("name", ""),
                            "username": introspection.get("username"),
                            "idp_id": introspection.get("client_id"),
                            "idp_name": introspection.get("iss", "iss-not found in Keycloak token"),
                            "auth_service": "Keycloak"
                        })
                        log.info(f"Added new user to database: {user_id}")
                except Exception as e:
                    raise HTTPException(
                        status_code=HTTP_401_UNAUTHORIZED,
                        detail=f"Failed to store or verify user in database. {e}"
                    )
                
                # Give permission to continue through the API
                return user_id

        # Revoke access if no introspection worked
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="User token not valid with Keycloak or Globus Auth."
        )


    # Get User
    async def get_user(
        self : "AlcfAuthenticatedAdapter",
        user_id: str,
        api_key: str,
        client_ip: str = None
        ) -> User:
        """
        Retrieve additional user information (name, email, etc.) for the given user_id.
        """

        # Clean API key
        api_key = api_key.replace("Bearer ", "")

        # Swap API key to use the Globus Compute dependent token if necessary
        # Only relevant for Facility Globus token
        token_response = validate_access_token(api_key)
        if token_response.is_valid:
            if token_response.is_authorized and token_response.user is not None:
                api_key = token_response.user.access_token

        # Extract user from the database
        try:
            if AMSC_DEMO_FLAG in user_id:
                user_id_for_db = user_id.replace(AMSC_DEMO_FLAG, "")
            else:
                user_id_for_db = user_id
            db_user = await get_db_user_from_id(user_id_for_db)
        except Exception:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=f"User ID {user_id} could not be recovered from the database"
            )
        
        # Facility Globus token: authorized if in list or if list is none
        if db_user.auth_service == "Globus":
            if GLOBUS_AUTHORIZED_USERNAMES:
                is_authorized = db_user.username in GLOBUS_AUTHORIZED_USERNAMES
            else:
                is_authorized = True

        # AmSC demo Globus token: only authorized if in list
        elif "Globus AmSC Demo" in db_user.auth_service:
            if GLOBUS_AMSC_AUTHORIZED_USERNAMES:
                is_authorized = db_user.username in GLOBUS_AMSC_AUTHORIZED_USERNAMES
            else:
                is_authorized = False
        
        # Facility Keycloak token: authorized if in list or if list is none
        elif db_user.auth_service == "Keycloak":
            if KEYCLOAK_AUTHORIZED_USERNAMES:
                is_authorized = db_user.username in KEYCLOAK_AUTHORIZED_USERNAMES
            else:
                is_authorized = True

        # Unsuported auth service
        else:
            is_authorized = False

        # Return user object if authorized
        if is_authorized:
            return User(id=user_id, name=db_user.name, api_key=api_key, client_ip=client_ip)
        else:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=f"User {db_user.name} ({db_user.username}) not authorized."
            )


    # Get user ID if user is authorized
    async def __get_authorized_globus_user_id(self, token_response: TokenValidationResponse):
        """
        Return user ID if the token is valid and if the user is authorized.
        If the token is valid, but user is not authorized, raise error.
        If the token is not valid, return None.
        """

        # If the token is a valid Globus Auth token ...
        if token_response.is_valid:

            # If the user is authorized ...
            if token_response.is_authorized and token_response.user is not None:

                # Store user in database if not already present
                try:
                    if not await exists_in_db(token_response.user.id, db_models.User):
                        await add_user_to_db({
                            "id": token_response.user.id,
                            "name": token_response.user.name,
                            "username": token_response.user.username,
                            "idp_id": token_response.user.idp_id,
                            "idp_name": token_response.user.idp_name,
                            "auth_service": token_response.user.auth_service
                        })
                        log.info(f"Added new user to database: {token_response.user.id}")
                except Exception as e:
                    raise HTTPException(
                        status_code=HTTP_401_UNAUTHORIZED,
                        detail=f"Failed to store or verify user in database. {e}"
                    )
                # Give permission to continue through the API
                return token_response.user.id
            
            # Revoke access if not authorized
            else:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail=token_response.error_message
                )
            
        # Return None if token is not valid
        return None