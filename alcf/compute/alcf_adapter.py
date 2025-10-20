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
    post_graphql
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
        query = build_submit_job_query(user, job_spec)
        print("======== submit_job ========")
        print(query)

        # Submit query to GraphQL API
        #response = await post_graphql(query=query, user=user, url=pbs_url)
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

        # Convert raw GraphQL response into a JobResponse pydantic model
        response = validate_job_response(response, ["data", "createJob"])
        
        # Return IRI-compliant job submission response
        return self.__format_submit_job(response)
    

    # Submit job script
    async def submit_job_script(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_script_path: str,
        args: list[str] = [],
    ) -> compute_models.Job:
        pass


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
        query = build_get_job_query(user, job_id, historical)
        print("======== get_job ========")
        print(query)

        # Submit query to GraphQL API
        #response = await post_graphql(query=query, user=user, url=pbs_url)

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

        # Convert raw GraphQL response into a JobResponse pydantic model
        response = validate_job_response(response, ["data", "jobs", "edges", 0])

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
        query = build_cancel_job_query(user, job_id)
        print("======== cancel_job ========")
        print(query)

        # Submit query to GraphQL API
        #response = await post_graphql(query=query, user=user, url=pbs_url)

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

        # Convert raw GraphQL response into a JobResponse pydantic model
        response = validate_job_response(response, ["data", "deleteJob"])
        
        # Error message if any
        if response.error:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=response.error.errorMessage
            )

        # Return IRI-compliant job submission response
        #return self.__format_get_job(response)
        return True
    
        
    # --------------------------------------
    #  Private frontend formatting functions
    # --------------------------------------

    # Format submit job
    def __format_submit_job(self, response: graphql_models.JobResponse) -> compute_models.Job:
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
    def __format_get_job(self, response: graphql_models.JobResponse) -> compute_models.Job:
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