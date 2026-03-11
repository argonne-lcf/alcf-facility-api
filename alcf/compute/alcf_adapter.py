from fastapi import HTTPException
from app.routers.compute.facility_adapter import FacilityAdapter as ComputeFacilityAdapter
from alcf.database.ingestion.ingest_activity_data import ALCF_RESOURCE_ID_LIST
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter, AMSC_DEMO_FLAG
from alcf.config import GRAPHQL_URLS
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

    # Submit job
    async def submit_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_spec: compute_models.JobSpec,
    ) -> compute_models.Job:
        
        # [TEMPORARY]
        # TODO: Need to swap to a service account
        if AMSC_DEMO_FLAG in user.id:
            raise HTTPException(
                status_code=HTTP_501_NOT_IMPLEMENTED,
                detail="Mapping to service account not supported yet."
            )

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
            if job_spec.attributes.reservation_id:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'reservation_id' not supported yet.")
            
        # Mandatory fields for PBS
        if not job_spec.stdout_path:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="'stdout_path' is mandatory.")
        if not job_spec.stderr_path:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="'stderr_path' is mandatory.")
        
        # Recover GraphQL URL
        graphql_url = self.__get_graphql_url(resource.name)

        # Convert IRI Job spec into GraphQL Job spec
        graphql_data = get_graphql_job_from_iri_jobspec(job_spec)

        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_submit_job_query(user, graphql_data),
            url=graphql_url
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
        
        # [TEMPORARY]
        # TODO: Need to swap to a service account
        if AMSC_DEMO_FLAG in user.id:
            raise HTTPException(
                status_code=HTTP_501_NOT_IMPLEMENTED,
                detail="Mapping to service account not supported yet."
            )

        # Recover GraphQL URL
        graphql_url = self.__get_graphql_url(resource.name)
        
        # Convert IRI Job spec into GraphQL Job spec
        graphql_data = get_graphql_job_from_iri_jobspec(job_spec)
        
        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_update_job_query(user, graphql_data, job_id),
            url=graphql_url
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
        include_spec: bool = False,
    ) -> compute_models.Job:
        
        # [TEMPORARY]
        # TODO: Need to swap to a service account
        if AMSC_DEMO_FLAG in user.id:
            raise HTTPException(
                status_code=HTTP_501_NOT_IMPLEMENTED,
                detail="Mapping to service account not supported yet."
            )

        # [TEMPORARY]
        # Error if input variables are not supported yet
        if include_spec:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'include_spec' not supported yet.")
        
        # Recover GraphQL URL
        graphql_url = self.__get_graphql_url(resource.name)
        
        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_get_job_query(user, job_id=job_id, historical=historical),
            url=graphql_url
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
        include_spec: bool = False,
    ) -> list[compute_models.Job]:
        
        # [TEMPORARY]
        # TODO: Need to swap to a service account
        if AMSC_DEMO_FLAG in user.id:
            raise HTTPException(
                status_code=HTTP_501_NOT_IMPLEMENTED,
                detail="Mapping to service account not supported yet."
            )
        
        # [TEMPORARY]
        # Error if input variables are not supported yet
        if filters:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="filters not implemented")
        if limit > 0:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="limit not implemented")
        if offset > 0:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="offset not implemented")
        if include_spec:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'include_spec' not supported yet.")
        
        # Recover GraphQL URL
        graphql_url = self.__get_graphql_url(resource.name)

        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_get_job_query(user, historical=historical),
            url=graphql_url
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
        
        # [TEMPORARY]
        # TODO: Need to swap to a service account
        if AMSC_DEMO_FLAG in user.id:
            raise HTTPException(
                status_code=HTTP_501_NOT_IMPLEMENTED,
                detail="Mapping to service account not supported yet."
            )

        # Recover GraphQL URL
        graphql_url = self.__get_graphql_url(resource.name)
        
        # Submit query to GraphQL API
        response = await post_graphql(
            user=user,
            query=build_cancel_job_query(user, job_id),
            url=graphql_url
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
    
    # Get GraphQL URL
    def __get_graphql_url(self, resource_name: str) -> str:

        # Extract GraphQL for the targetted resource
        graphql_url = GRAPHQL_URLS.get(resource_name.lower(), None)

        # Error if resource does not have GraphQL
        if graphql_url is None:
            raise HTTPException(
                status_code=HTTP_501_NOT_IMPLEMENTED, 
                detail=f"Job submission for {resource_name} not available yet."
            )
        
        # Return URL
        return graphql_url