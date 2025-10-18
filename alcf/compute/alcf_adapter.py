import httpx
from json.decoder import JSONDecodeError
from fastapi import HTTPException
from app.routers.compute.facility_adapter import FacilityAdapter as ComputeFacilityAdapter
from alcf.database.ingestion.ingest_activity_data import ALCF_RESOURCE_ID_LIST

# Typing
from app.routers.compute import models as compute_models
from app.routers.status import models as status_models
from app.routers.account import models as account_models

# HTTP codes
from starlette.status import (
    HTTP_304_NOT_MODIFIED, 
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_408_REQUEST_TIMEOUT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED, 
    HTTP_502_BAD_GATEWAY,
)

# GraphQL query utils
from alcf.compute.utils_graphql import (
    build_mutation_createjob_query
)

class AlcfAdapter(ComputeFacilityAdapter):
    """Facility adapter definition for the IRI Facility API."""

    def __init__(self):
        self.__pbs_graphql_api_urls = {
           ALCF_RESOURCE_ID_LIST.edith.value: "https://edtb-01:8080/graphql"
        }
        self.user = account_models.User(id="bcote", name="Benoit Cote", api_key="12345")


    # Get current_user
    async def get_current_user(
        self : "AlcfAdapter",
        api_key: str,
        ip_address: str|None,
        ) -> str:
        """
            Decode the api_key and return the authenticated user's id.
            This method is not called directly, rather authorized endpoints "depend" on it.
            (https://fastapi.tiangolo.com/tutorial/dependencies/)
        """
        # TODO CHANGE after testing
        return "bcote"


    # Get User
    async def get_user(
        self : "AlcfAdapter",
        user_id: str,
        api_key: str,
        ) -> account_models.User:
        """
            Retrieve additional user information (name, email, etc.) for the given user_id.
        """
        # TODO CHANGE after testing
        return self.user


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
        if job_spec.attributes.account:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'account' not supported yet.")
        if job_spec.attributes.reservation_id:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'reservation_id' not supported yet.")
        if job_spec.attributes.custom_attributes:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'custom_attributes' not supported yet.")
            
        # Get API URL from the resource object for the job submition
        pbs_url = self.__pbs_graphql_api_urls[resource.id]

        # Build GraphQL query
        query = self.__build_submit_job_query(resource, user, job_spec)
        print("========")
        print(query)

        response = await self.__post_graphql(query=query, user=user, url=pbs_url)
        print("========")
        print(response)

        job = compute_models.Job(
            id="1",
            status=compute_models.JobStatus(
                state=compute_models.JobState.NEW
            )
        )
        return job


    # Update job
    def update_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_spec: compute_models.JobSpec,
        job_id: str,
    ) -> compute_models.Job:
        pass


    # Get job
    def get_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
        historical: bool = False,
    ) -> compute_models.Job:
        pass

    
    # Get jobs
    def get_jobs(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        offset : int,
        limit : int,
        filters: dict[str, object] | None = None,
        historical: bool = False,
    ) -> list[compute_models.Job]:
        pass

    
    # Cancel job
    def cancel_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
    ) -> bool:
        pass


    # ----------------------
    # Build GraphQL Querries
    # ----------------------

    # Job submission query
    def __build_submit_job_query(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_spec: compute_models.JobSpec
    ) -> str:
        
        # Build input data
        input_data = {
            "remoteCommand": job_spec.executable,
            "commandArgs": job_spec.arguments,
            "name": job_spec.name,
            "errorPath": job_spec.stderr_path,
            "outputPath": job_spec.stdout_path,
            "queue": {
                "name": job_spec.attributes.queue_name
            },
            "resourcesRequested": {
                "jobResources": {
                    "index": "",
                    "physicalMemory": job_spec.resources.memory,
                    "wallClockTime": job_spec.attributes.duration.seconds
                }
            }
        }

        # Generate and return the job submission GraphQL query
        return build_mutation_createjob_query(input_data)


    # ----
    # Submit GraphQL Queries
    # --------

    # Post GraphQL
    # TODO: Remove verify_ssl once PBS GraphQL is outside of the dev environment
    async def __post_graphql(
        self: "AlcfAdapter",
        query: str = None,
        user: account_models.User = None,
        url: str = None,
        verify_ssl: bool = False
        ):
        """Generic command to send post requests to GraphQL."""

        # Generate request headers
        try:
            headers = {
                "Authorization": f"Bearer {user.api_key}",
                "Content-Type": "application/json"
            }
        except Exception:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, 
                detail="Cannot extract user's API key."
            )

        # Submit request to GraphQL API 
        try:
            async with httpx.AsyncClient(verify=verify_ssl) as client:
                response = await client.post(url, json={"query": query}, headers=headers, timeout=10)
                response = response.json()
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=HTTP_408_REQUEST_TIMEOUT,
                detail="Compute query timed out."
            )
        except JSONDecodeError as e:
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail=f"Compute query response could not be parsed: {e}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Compute query failed: {e}"
            )
        
        # Return the response (already parsed)
        return response