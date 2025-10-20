import httpx
from json.decoder import JSONDecodeError
from fastapi import HTTPException
from app.routers.compute.facility_adapter import FacilityAdapter as ComputeFacilityAdapter
from alcf.database.ingestion.ingest_activity_data import ALCF_RESOURCE_ID_LIST
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter

# Typing
from app.routers.compute import models as compute_models
from app.routers.status import models as status_models
from app.routers.account import models as account_models
from alcf.compute.graphql import models as graphql_models

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
from alcf.compute.graphql.utils import (
    build_mutation_createjob_query,
    build_query_jobs_query,
    build_mutation_deletejob_query
)

class AlcfAdapter(ComputeFacilityAdapter, AlcfAuthenticatedAdapter):
    """Facility adapter definition for the IRI Facility API."""

    # Initialization for constants and convertions 
    def __init__(self):

        # Temporary user during development
        # TODO: REMOVE
        #self.user = account_models.User(id="bcote", name="Benoit Cote", api_key="12345")

        # URLs for PBS GraphQL API on different resource
        self.__pbs_graphql_api_urls = {
           ALCF_RESOURCE_ID_LIST.edith.value: "https://edtb-01:8080/graphql"
        }
        # TODO: Soon this will be https://edtb-pbs-02.lab.alcf.anl.gov/graphql

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
        query = self.__build_submit_job_query(user, job_spec)
        print("========")
        print(query)

        # Submit query to GraphQL API
        #response = await self.__post_graphql(query=query, user=user, url=pbs_url)
        #print("========")
        #print(response)

        # TODO: Temp while we seek access to GraphQL
        import json
        response = json.loads("""
            {
                "data": {
                    "createJob": {
                    "node": {
                        "jobId": "77721.edtb-01.mcp.alcf.anl.gov",
                        "status": {
                            "state": 0
                        }
                    },
                    "error": null
                    }
                }
            }
        """)

        # Validate query response
        try:
            response = graphql_models.CreateJobResponse(**response["data"]["createJob"])
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Compute query response could not be parsed: {e}"
            )
        
        # Return IRI-compliant job submission response
        return self.__format_submit_job(response)


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
    async def get_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
        historical: bool = False,
    ) -> compute_models.Job:
        
        # Get API URL from the resource object for the job submition
        pbs_url = self.__pbs_graphql_api_urls[resource.id]

        # Build GraphQL query
        query = self.__build_get_job_query(user, job_id, historical)
        print("========")
        print(query)

        # Submit query to GraphQL API
        #response = await self.__post_graphql(query=query, user=user, url=pbs_url)

        # TEMP
        import json
        response = json.loads("""
            {
            "data": {
                "jobs": {
                "edges": [
                    {
                    "node": {
                        "jobId": "77730.edtb-01.mcp.alcf.anl.gov",
                        "status": {
                        "state": 7,
                        "exitStatus": 0
                        }
                    }
                    }
                ]
                }
            }
            }
        """)

        # Validate query response
        try:
            response = response["data"]["jobs"]["edges"][0]
            response = graphql_models.CreateJobResponse(**response)
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Compute query response could not be parsed: {e}"
            )

        # Return IRI-compliant job submission response
        return self.__format_get_job(response)

    
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
    async def cancel_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
    ) -> bool:
        
        # Get API URL from the resource object for the job submition
        pbs_url = self.__pbs_graphql_api_urls[resource.id]

        # Build GraphQL query
        query = self.__build_cancel_job_query(user, job_id)
        print("========")
        print(query)

        # Submit query to GraphQL API
        #response = await self.__post_graphql(query=query, user=user, url=pbs_url)

        # TEMP
        import json
        response = json.loads("""
            {
            "data": {
                "deleteJob": {
                "node": {
                    "jobId": "77730.edtb-01.mcp.alcf.anl.gov"
                },
                "error": null
                }
            }
            }
        """)

        # Validate query response
        try:
            response = response["data"]["deleteJob"]
            response = graphql_models.CreateJobResponse(**response)
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Compute query response could not be parsed: {e}"
            )
        
        # Error message if any
        if response.error:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=response.error.errorMessage
            )

        # Return IRI-compliant job submission response
        #return self.__format_get_job(response)
        return True

    # -----------------
    # GraphQL Functions
    # -----------------

    # Build submit job query
    def __build_submit_job_query(
        self: "AlcfAdapter",
        user: account_models.User, 
        job_spec: compute_models.JobSpec
    ) -> str:
        
        # Build queue
        queue = graphql_models.Queue(
            name=job_spec.attributes.queue_name
        )

        # Build job resources
        jobResources = graphql_models.JobTasksResources(
            physicalMemory=job_spec.resources.memory,
            wallClockTime=job_spec.attributes.duration.seconds
        )

        # Build resources requested
        resourcesRequested = graphql_models.JobResources(
            jobResources=jobResources
        )
        
        # Build query data
        input_data = graphql_models.Job(
            remoteCommand=job_spec.executable,
            commandArgs=job_spec.arguments,
            name=job_spec.name,
            errorPath=job_spec.stderr_path,
            outputPath=job_spec.stdout_path,
            queue=queue,
            resourcesRequested=resourcesRequested
        )

        # Generate and return the job submission GraphQL query
        return build_mutation_createjob_query(input_data)
    

    # Build get job query
    def __build_get_job_query(
        self: "AlcfAdapter",
        user: account_models.User, 
        job_id: str,
        historical: bool = False,
    ) -> str:
        
        # Build job query filter
        filter_data = graphql_models.QueryJobsFilter(
            withHistoryJobs=historical,
            jobIds=job_id
        )

        # Generate and return the job submission GraphQL query
        return build_query_jobs_query(filter_data)
    

    # Build candel job query
    def __build_cancel_job_query(
        self: "AlcfAdapter",
        user: account_models.User, 
        job_id: str,
    ) -> str:
        return build_mutation_deletejob_query(job_id)


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
    

    # Get IRI job state
    def __get_iri_job_state_from_graphql(self, state: int):
        """Return the IRI Facility API compliant state from a PBS GraphQL state."""
        
        # New
        if state == 0:
            return compute_models.JobState.NEW.value
        
        # Running
        elif state == 7:
            return compute_models.JobState.ACTIVE.value

        # Completed
        elif state == 10:
            return compute_models.JobState.COMPLETED.value
        
        # Error if state not supported
        else:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Job state {state} not supported."
            )
        
    # --------------------------------------
    #  Private frontend formatting functions
    # --------------------------------------

    # Format submit job
    def __format_submit_job(self, response: graphql_models.CreateJobResponse) -> compute_models.Job:
        """Format a GraphQL submit job response into a pydantic Job object."""
        state = self.__get_iri_job_state_from_graphql(response.node.status.state)
        status = compute_models.JobStatus(
            state=state
        )
        return compute_models.Job(
            id=response.node.jobId,
            status=status
        )
    
    # Format get job
    def __format_get_job(self, response: graphql_models.CreateJobResponse) -> compute_models.Job:
        """Format a GraphQL get job response into a pydantic Job object."""
        state = self.__get_iri_job_state_from_graphql(response.node.status.state)
        status = compute_models.JobStatus(
            state=state,
            exit_code=response.node.status.exitStatus
        )
        return compute_models.Job(
            id=response.node.jobId,
            status=status
        )
