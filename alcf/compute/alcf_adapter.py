from fastapi import HTTPException
from app.routers.compute.facility_adapter import FacilityAdapter as ComputeFacilityAdapter
from alcf.database.ingestion.ingest_activity_data import ALCF_RESOURCE_ID_LIST
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter
from alcf.config import GRAPHQL_URL
from alcf.compute.graphql.converters import (
    get_graphql_job_from_iri_jobspec,
    get_iri_job_from_graphql_job
)

# Typing
from typing import List
from app.routers.compute import models as compute_models
from app.routers.status import models as status_models
from app.routers.account import models as account_models
from alcf.compute.graphql import models as graphql_models

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
    post_graphql
)

class AlcfAdapter(ComputeFacilityAdapter, AlcfAuthenticatedAdapter):
    """Compute facility adapter definition for the IRI Facility API."""

    # Initialization for constants and convertions 
    def __init__(self):

        # URLs for PBS GraphQL API on different resource 
        # For now just hardcoded to Edith
        self.__pbs_graphql_api_urls = {
           ALCF_RESOURCE_ID_LIST.edith.value: GRAPHQL_URL
        }

    # Submit job
    async def submit_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
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
            if job_spec.resources.node_count:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'node_count' not supported yet.")
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
            if job_spec.attributes.account:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'account' not supported yet.")
            if job_spec.attributes.reservation_id:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'reservation_id' not supported yet.")
            if job_spec.attributes.custom_attributes:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'custom_attributes' not supported yet.")
            
        # Convert IRI Job spec into GraphQL Job spec
        graphql_data = get_graphql_job_from_iri_jobspec(job_spec)

        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_submit_job_query(user, graphql_data),
            url=self.__pbs_graphql_api_urls[resource.id]
        )

        # Extract raw job response into GraphQL JobResponse pydantic object
        response = self.__extract_job_response(response, ["data", "createJob"])
        
        # Return IRI-compliant job response
        return get_iri_job_from_graphql_job(response.node)
    

    # Submit job script
    async def submit_job_script(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_script_path: str,
        args: list[str] = [],
    ) -> compute_models.Job:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Capability not implemented")


    # Update job
    async def update_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_spec: compute_models.JobSpec,
        job_id: str,
    ) -> compute_models.Job:
        
        # Convert IRI Job spec into GraphQL Job spec
        graphql_data = get_graphql_job_from_iri_jobspec(job_spec)
        
        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_update_job_query(user, graphql_data, job_id),
            url=self.__pbs_graphql_api_urls[resource.id]
        )

        # Extract raw job response into GraphQL JobResponse pydantic object
        response = self.__extract_job_response(response, ["data", "updateJob"])
        
        # Return IRI-compliant job response
        return get_iri_job_from_graphql_job(response.node)


    # Get job
    async def get_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
        historical: bool = False,
    ) -> compute_models.Job:
        
        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_get_job_query(user, job_id=job_id, historical=historical),
            url=self.__pbs_graphql_api_urls[resource.id]
        )
        
        # Extract raw job response into GraphQL JobResponse pydantic object
        response = self.__extract_job_response(response, ["data", "jobs", "edges", 0])

        # Error if no job exists
        if not response.node:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} not found."
            )

        # Return IRI-compliant job response
        return get_iri_job_from_graphql_job(response.node)

    
    # Get jobs
    async def get_jobs(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        offset : int,
        limit : int,
        filters: dict[str, object] | None = None,
        historical: bool = False,
    ) -> list[compute_models.Job]:
        
        # [TEMPORARY]
        # Error if input variables are not supported yet
        if filters:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="filters not implemented")
        if limit > 0:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="limit not implemented")

        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_get_job_query(user, historical=historical),
            url=self.__pbs_graphql_api_urls[resource.id]
        )
        
        # Access relevant data from the response
        try:
            response = response["data"]["jobs"]["edges"]
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cannot access response['data']['jobs']['edges']: {response}"
            )
        
        # Convert raw GraphQL response into a JobResponse pydantic model
        responses = [validate_job_response(edge) for edge in response if edge["node"]]

        # Return IRI-compliant job submission response
        return [get_iri_job_from_graphql_job(r.node) for r in responses]

    
    # Cancel job
    async def cancel_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
    ) -> bool:
        
        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_cancel_job_query(user, job_id),
            url=self.__pbs_graphql_api_urls[resource.id]
        )

        # Extract raw job response into GraphQL JobResponse pydantic object
        response = self.__extract_job_response(response, ["data", "deleteJob"])
        
        # Return IRI-compliant job submission response
        return True
    

    # Extract job response
    def __extract_job_response(self, response: dict, key_list: List[str]) -> graphql_models.JobResponse:

        # GraphQL error
        if "errors" in response:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"GraphQL error: {response["errors"]}"
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