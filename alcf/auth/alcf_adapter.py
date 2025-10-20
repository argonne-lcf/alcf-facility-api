from app.routers.iri_router import AuthenticatedAdapter
from app.routers.account.models import User
from alcf.config import SECRET_DEV_KEY

class AlcfAuthenticatedAdapter(AuthenticatedAdapter):

    # TODO: Should make this async
    def get_current_user(
        self : "AlcfAuthenticatedAdapter",
        api_key: str,
        ip_address: str|None,
        ) -> str:
        """
            Decode the api_key and return the authenticated user's id.
            This method is not called directly, rather authorized endpoints "depend" on it.
            (https://fastapi.tiangolo.com/tutorial/dependencies/)
        """
    
        # Check if this is the authorized dev user (bcote)
        # TODO: Change this for a proper auth check once integrated
        api_key = api_key.replace("Bearer ", "")
        if api_key == SECRET_DEV_KEY:
            return "bcote-id"
        else:
            return None


    # Get User
    async def get_user(
        self : "AlcfAuthenticatedAdapter",
        user_id: str,
        api_key: str,
        ) -> User:
        """
            Retrieve additional user information (name, email, etc.) for the given user_id.
        """
        # TODO: Change this for a proper auth check once integrated
        api_key = api_key.replace("Bearer ", "")
        if user_id == "bcote-id" and api_key == SECRET_DEV_KEY:
            return User(id="bcote-id", name="Benoit Cote", api_key=api_key)
        else:
            return None
