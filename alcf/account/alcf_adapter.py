from fastapi import HTTPException
from app.routers.account.facility_adapter import FacilityAdapter as AccountFacilityAdapter
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter

# Typing
from app.types import models as types_models
from app.routers.account import models as account_models

# HTTP codes
from starlette.status import ( 
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED, 
)


class AlcfAdapter(AccountFacilityAdapter, AlcfAuthenticatedAdapter):
    """Account facility adapter definition for the IRI Facility API."""

    # Get capabilities
    async def get_capabilities(
        self: "AlcfAdapter", 
        name: str | None = None, 
        modified_since: str | None = None, 
        offset: int = 0, 
        limit: int = 1000
    ) -> list[types_models.Capability]:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")

    
    # Get projects
    async def get_projects(
        self: "AlcfAdapter", 
        user: account_models.User
    ) -> list[account_models.Project]:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")

    
    # Get project allocations
    async def get_project_allocations(
        self: "AlcfAdapter", 
        project: account_models.Project, 
        user: account_models.User
    ) -> list[account_models.ProjectAllocation]:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")

    
    # Get user allocations
    async def get_user_allocations(
        self: "AlcfAdapter", 
        user: account_models.User, 
        project_allocation: account_models.ProjectAllocation
    ) -> list[account_models.UserAllocation]:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")
