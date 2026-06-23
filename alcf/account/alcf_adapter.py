from fastapi import HTTPException
from app.routers.account.facility_adapter import FacilityAdapter as AccountFacilityAdapter
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter
from alcf.maintenance import require_component_operational
from alcf.enums import APIComponent
from alcf.logging.decorators import log_account_operation
from alcf.auth.utils import generate_error_message
from alcf.account import models as ni_models

# Typing
from app.types import models as types_models
from app.types.user import User
from app.types.scalars import StrictDateTime
from app.routers.account import models as account_models

# HTTP codes
from starlette.status import ( 
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from alcf.account.utils import get_ni_rest_api_url, get_ni_rest
from alcf.auth.keycloak_utils import generate_user_keycloak_token


class AlcfAdapter(AccountFacilityAdapter, AlcfAuthenticatedAdapter):
    """Account facility adapter definition for the IRI Facility API."""

    # Get capabilities
    @require_component_operational(APIComponent.ACCOUNT)
    @log_account_operation
    async def get_capabilities(
        self: "AlcfAdapter", 
        name: str | None = None, 
        modified_since: StrictDateTime | None = None, 
        offset: int = 0, 
        limit: int = 1000
    ) -> list[types_models.Capability]:
        
        # Submit query to Ni REST API
        response = await get_ni_rest(
            url=f"{get_ni_rest_api_url()}/capabilities"
        )

        # Validate data
        ni_capabilities = ni_models.NiCapabilities(capabilities=response).capabilities
        
        # Format response
        iri_response = [await self._format_capability(c) for c in ni_capabilities if c]

        # Apply filters
        if name:
            iri_response = [capability for capability in iri_response if capability.name == name]
        if modified_since:
            iri_response = [capability for capability in iri_response if capability.last_modified >= modified_since]

        # Return formatted and filtered IRI response
        return iri_response[offset:offset + limit]

    
    # Get projects
    @require_component_operational(APIComponent.ACCOUNT)
    @log_account_operation
    async def get_projects(
        self: "AlcfAdapter", 
        user: User
    ) -> list[account_models.Project]:
        
        # Submit query to Ni REST API
        response = await get_ni_rest(
            url=f"{get_ni_rest_api_url()}/projects",
            access_token=generate_user_keycloak_token(user)
        )

        # Validate data
        ni_projects = ni_models.NiProjects(projects=response).projects

        # Return response in IRI format
        return [self._format_project(p) for p in ni_projects]

    
    # Get project allocations
    @require_component_operational(APIComponent.ACCOUNT)
    @log_account_operation
    async def get_project_allocations(
        self: "AlcfAdapter", 
        project: account_models.Project, 
        user: User
    ) -> list[account_models.ProjectAllocation]:
        
        # Submit query to Ni REST API
        response = await get_ni_rest(
            url=f"{get_ni_rest_api_url()}/projects/{project.name}/project_allocations",
            access_token=generate_user_keycloak_token(user)
        )

        # Validate data
        ni_allocations = ni_models.NiAllocations(allocations=response).allocations

        # Return response in IRI format
        return [self._format_allocation(project, a) for a in ni_allocations]

    
    # Get user allocations
    @require_component_operational(APIComponent.ACCOUNT)
    @log_account_operation
    async def get_user_allocations(
        self: "AlcfAdapter", 
        user: User, 
        project_allocation: account_models.ProjectAllocation
    ) -> list[account_models.UserAllocation]:
        
        # Return mostly the same as project allocation since we do not have specific user allocation
        return [
            account_models.UserAllocation(
                id=project_allocation.id,
                project_id=project_allocation.project_id,
                project_allocation_id=project_allocation.id,
                user_id=user.id,
                entries=project_allocation.entries
            )
        ]


    async def _format_capability(
        self: "AlcfAdapter",
        ni_capability: ni_models.NiCapability,
    ) -> types_models.Capability:
        """Create IRI capability from Ni data"""
        try:
            return types_models.Capability(
                id=ni_capability.id,
                name=ni_capability.name,
                description=ni_capability.description,
                units=ni_capability.units,
                last_modified=ni_capability.last_updated,
            )
        except Exception as e:
            error_message = generate_error_message("Cannot parse capability", e)
            raise HTTPException(
                detail=error_message,
                status_code=HTTP_500_INTERNAL_SERVER_ERROR
            )
        

    def _format_project(
        self: "AlcfAdapter", 
        ni_project: ni_models.NiProject
    ) -> account_models.Project:
        """Create IRI project from Ni data"""
        try:
            return account_models.Project(
                id=ni_project.id,
                name=ni_project.name,
                description=ni_project.description,
                user_ids=ni_project.users,
                last_modified=ni_project.last_modified
            )
        except Exception as e:
            error_message = generate_error_message("Cannot parse project", e)
            raise HTTPException(
                detail=error_message,
                status_code=HTTP_500_INTERNAL_SERVER_ERROR
            )
        

    def _format_allocation(
        self: "AlcfAdapter",
        project: account_models.Project,
        ni_allocation: ni_models.NiAllocation
    ) -> account_models.ProjectAllocation:
        """Create IRI allocation from Ni data"""
        try:
            return account_models.ProjectAllocation(
                id=ni_allocation.allocation_id,
                project_id=project.id,
                capability_id=ni_allocation.resource, # TODO use ID when available
                entries=[
                    account_models.AllocationEntry(
                        allocation=ni_allocation.deposits,
                        usage=ni_allocation.used,
                        unit=ni_allocation.unit
                    )
                ]
         
            )
        except Exception as e:
            error_message = generate_error_message("Cannot parse allocation", e)
            raise HTTPException(
                detail=error_message,
                status_code=HTTP_500_INTERNAL_SERVER_ERROR
            )
