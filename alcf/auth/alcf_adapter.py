from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
from app.routers.iri_router import AuthenticatedAdapter
from app.routers.account.models import User
from alcf.config import KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET, KEYCLOAK_REALM_NAME, SECRET_DEV_KEY
from keycloak import KeycloakOpenID
from alcf.auth.utils import validate_access_token
from alcf.database.database import exists_in_db, add_user_to_db
from alcf.database import models as db_models
import logging

log = logging.getLogger(__name__)

# Configure Keycloak client
keycloak_openid = KeycloakOpenID(
    server_url="https://keycloak-internal.alcf.anl.gov",
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
    
        # If this is a Globus token ...
        # -----------------------------

        # Try to validate the API key with Globus Auth
        token_response = validate_access_token(api_key)

        # If the token is a valid Globus Auth token ...
        if token_response.is_valid:

            # If the user is authorized ...
            if token_response.is_authorized and token_response.user is not None:

                # Store user in database if not already present
                try:
                    if not await exists_in_db(user_id, db_models.User):
                        await add_user_to_db({
                            "id": token_response.user.id,
                            "name": token_response.user.name,
                            "username": token_response.user.username,
                            "idp_id": token_response.user.idp_id,
                            "idp_name": token_response.user.idp_name,
                            "auth_service": token_response.user.auth_service
                        })
                        log.info(f"Added new user to database: {user_id}")
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

        # If this is a Keyckoak token ...
        # -------------------------------

        # Try to validate the API key with Keycloak
        # TODO: Cache this
        introspection = keycloak_openid.introspect(api_key)

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
        token_response = validate_access_token(api_key)
        if token_response.is_valid:
            if token_response.is_authorized and token_response.user is not None:
                api_key = token_response.user.access_token
        
        # Temporary - allow specific username
        if user_id == "bcote":
            return User(id="bcote", name="Benoit Cote", api_key=api_key, client_ip=client_ip)
        elif user_id == "richp":
            return User(id="richp", name="Paul Rich", api_key=api_key, client_ip=client_ip)
        elif user_id == "eaba2ae5-b943-453e-9bef-4e137a7032cf": # Globus bcote@alcf.anl.gov
            return User(id="eaba2ae5-b943-453e-9bef-4e137a7032cf", name="Benoit Cote", api_key=api_key, client_ip=client_ip)
        else:
            return None
