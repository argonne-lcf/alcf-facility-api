from typing import List
from fastapi import HTTPException
from app.routers.compute.facility_adapter import FacilityAdapter as ComputeFacilityAdapter
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter
from alcf.auth.utils import KEYCLOAK_FLAG
from alcf.auth.keycloak_utils import generate_user_keycloak_token
from alcf.compute.graphql.converters import (
    get_graphql_job_from_iri_jobspec,
    get_iri_job_from_graphql_job
)
from alcf.maintenance import require_component_operational
from alcf.enums import APIComponent

# Typing
from app.routers.compute import models as compute_models
from app.routers.status import models as status_models
from app.types.user import User
from alcf.compute.graphql import models as graphql_models
from alcf.compute.logs import log_compute_operation

# HTTP codes
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED, 
)

# GraphQL query utils
from alcf.compute.graphql.utils import (
    validate_job_response,
    build_submit_job_query,
    build_get_job_query,
    build_cancel_job_query,
    build_update_job_query,
    post_graphql,
    get_graphql_url
)


class AlcfAdapter(ComputeFacilityAdapter, AlcfAuthenticatedAdapter):
    """Compute facility adapter definition for the IRI Facility API."""

    # Submit job
    @require_component_operational(APIComponent.COMPUTE)
    @log_compute_operation
    async def submit_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        job_spec: compute_models.JobSpec,
    ) -> compute_models.Job:
        
        # [TEMPORARY]
        # Error if input variables are not supported yet
        if job_spec.inherit_environment == False:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'inherit_environment' not supported yet.")
        if job_spec.environment:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'environment' not supported yet.")
        if job_spec.stdin_path:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'stdin_path' not supported yet.")
        if job_spec.pre_launch:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'pre_launch' not supported yet.")
        if job_spec.post_launch:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'post_launch' not supported yet.")
        if job_spec.launcher:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'launcher' not supported yet.")
        if job_spec.resources:
            if job_spec.resources.process_count:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'process_count' not supported yet.")
            if job_spec.resources.processes_per_node:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'processes_per_node' not supported yet.")
            if job_spec.resources.cpu_cores_per_process:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'cpu_cores_per_process' not supported yet.")
            if job_spec.resources.gpu_cores_per_process:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'gpu_cores_per_process' not supported yet.")
            if job_spec.resources.exclusive_node_use == False:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'exclusive_node_use' not supported yet.")
        if job_spec.attributes:
            if job_spec.attributes.reservation_id:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'reservation_id' not supported yet.")
            
        # Mandatory fields for PBS
        if not job_spec.stdout_path:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="'stdout_path' is mandatory.")
        if not job_spec.stderr_path:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="'stderr_path' is mandatory.")
        
        # Recover GraphQL URL
        graphql_url = get_graphql_url(resource.name)

        # Convert IRI Job spec into GraphQL Job spec
        graphql_data = get_graphql_job_from_iri_jobspec(job_spec, resource.name)

        # Generate Keycloak access token for user if necessary
        if KEYCLOAK_FLAG in user.api_key:
            user_keycloak_access_token = user.api_key.replace(KEYCLOAK_FLAG, "")
        else:
            user_keycloak_access_token = generate_user_keycloak_token(user)

        # Submit query to GraphQL API
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_submit_job_query(user, graphql_data),
            url=graphql_url
        )

        # Create and return IRI-compliant job response
        response = self.__extract_job_response(response, ["data", "createJob"])
        iri_response = get_iri_job_from_graphql_job(response.node)
        return iri_response
    

    # Submit job script
    @require_component_operational(APIComponent.COMPUTE)
    @log_compute_operation
    async def submit_job_script(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        job_script_path: str,
        args: list[str] = [],
    ) -> compute_models.Job:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Capability not implemented")


    # Update job
    @require_component_operational(APIComponent.COMPUTE)
    @log_compute_operation
    async def update_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        job_spec: compute_models.JobSpec,
        job_id: str,
    ) -> compute_models.Job:
        
        # Recover GraphQL URL
        graphql_url = get_graphql_url(resource.name)
        
        # Convert IRI Job spec into GraphQL Job spec
        graphql_data = get_graphql_job_from_iri_jobspec(job_spec, resource.name)

        # Generate Keycloak access token for user if necessary
        if KEYCLOAK_FLAG in user.api_key:
            user_keycloak_access_token = user.api_key.replace(KEYCLOAK_FLAG, "")
        else:
            user_keycloak_access_token = generate_user_keycloak_token(user)
        
        # Submit query to GraphQL API
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_update_job_query(user, graphql_data, job_id),
            url=graphql_url
        )

        # Create and return IRI-compliant job response
        response = self.__extract_job_response(response, ["data", "updateJob"])
        iri_response = get_iri_job_from_graphql_job(response.node)
        return iri_response
    

    # Get job
    @require_component_operational(APIComponent.COMPUTE)
    @log_compute_operation
    async def get_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        job_id: str,
        historical: bool = False,
        include_spec: bool = False,
    ) -> compute_models.Job:

        # [TEMPORARY]
        # Error if input variables are not supported yet
        if include_spec:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'include_spec' not supported yet.")
        
        # Recover GraphQL URL
        graphql_url = get_graphql_url(resource.name)

        # Generate Keycloak access token for user if necessary
        if KEYCLOAK_FLAG in user.api_key:
            user_keycloak_access_token = user.api_key.replace(KEYCLOAK_FLAG, "")
        else:
            user_keycloak_access_token = generate_user_keycloak_token(user)
        
        # Submit query to GraphQL API
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_get_job_query(user, job_id=job_id, historical=historical),
            url=graphql_url
        )

        response = self.__extract_job_response(response, ["data", "jobs", "edges", 0])

        if not response.node:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} not found."
            )

        # Create and return IRI-compliant job response
        iri_response = get_iri_job_from_graphql_job(response.node)
        return iri_response

    
    # Get jobs
    @require_component_operational(APIComponent.COMPUTE)
    @log_compute_operation
    async def get_jobs(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        offset : int,
        limit : int,
        filters: dict[str, object] | None = None,
        historical: bool = False,
        include_spec: bool = False,
    ) -> list[compute_models.Job]:
        
        # [TEMPORARY]
        # Error if input variables are not supported yet
        if filters:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="filters not implemented")
        if include_spec:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'include_spec' not supported yet.")
        
        # Recover GraphQL URL
        graphql_url = get_graphql_url(resource.name)

        # Generate Keycloak access token for user if necessary
        if KEYCLOAK_FLAG in user.api_key:
            user_keycloak_access_token = user.api_key.replace(KEYCLOAK_FLAG, "")
        else:
            user_keycloak_access_token = generate_user_keycloak_token(user)

        # Submit query to GraphQL API
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_get_job_query(user, historical=historical),
            url=graphql_url
        )
        
        try:
            response = response["data"]["jobs"]["edges"]
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cannot access response['data']['jobs']['edges']: {response}"
            )

        # Create and return IRI-compliant job response        
        responses = [validate_job_response(edge) for edge in response if edge["node"]]
        responses = responses[offset:offset+limit]
        iri_response = [get_iri_job_from_graphql_job(r.node) for r in responses]
        return iri_response

    
    # Cancel job
    @require_component_operational(APIComponent.COMPUTE)
    @log_compute_operation
    async def cancel_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        job_id: str,
    ) -> bool:

        # Recover GraphQL URL
        graphql_url = get_graphql_url(resource.name)

        # Generate Keycloak access token for user if necessary
        if KEYCLOAK_FLAG in user.api_key:
            user_keycloak_access_token = user.api_key.replace(KEYCLOAK_FLAG, "")
        else:
            user_keycloak_access_token = generate_user_keycloak_token(user)
        
        # Submit query to GraphQL API
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_cancel_job_query(user, job_id),
            url=graphql_url
        )

        # Create and return IRI-compliant job response
        self.__extract_job_response(response, ["data", "deleteJob"])
        return True
    

    # Extract job response
    def __extract_job_response(self, response: dict, key_list: List[str]) -> graphql_models.JobResponse:

        # GraphQL error
        if "errors" in response:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"GraphQL error: {response['errors']}"
            )

        # Convert raw GraphQL response into a JobResponse pydantic model
        try:
            for key in key_list:
                response = response[key]
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cannot access response data with {key_list}: {response}"
            )
        
        # Convert raw GraphQL response into a GraphQL JobResponse pydantic model  
        response: graphql_models.JobResponse = validate_job_response(response)
        
        # Error if data validation went wrong
        if response.error:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error.errorMessage
            )
        
        # Return JobResponse object
        return response
    