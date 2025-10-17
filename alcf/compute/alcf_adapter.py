from fastapi import HTTPException
from starlette.status import HTTP_501_NOT_IMPLEMENTED, HTTP_304_NOT_MODIFIED, HTTP_400_BAD_REQUEST
from app.routers.compute.facility_adapter import FacilityAdapter as ComputeFacilityAdapter

# Typing
from app.routers.compute import models as compute_models
from app.routers.status import models as status_models
from app.routers.account import models as account_models


class AlcfAdapter(ComputeFacilityAdapter):
    """Facility adapter definition for the IRI Facility API."""

    # Submit job
    def submit_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_spec: compute_models.JobSpec,
    ) -> compute_models.Job:
        
        # Error if input variables are not supported yet
        if job_spec.inherit_environment == False:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'inherit_environment' not supported yet.")
        if job_spec.environment:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'environment' not supported yet.")
        if job_spec.stdin_path:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'stdin_path' not supported yet.")
        if job_spec.pre_launch:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'pre_launch' not supported yet.")
        if job_spec.post_launch:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'post_launch' not supported yet.")
        if job_spec.launcher:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'launcher' not supported yet.")
        if job_spec.resources.node_count:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'node_count' not supported yet.")
        if job_spec.resources.process_count:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'process_count' not supported yet.")
        if job_spec.resources.processes_per_node:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'processes_per_node' not supported yet.")
        if job_spec.resources.cpu_cores_per_process:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'cpu_cores_per_process' not supported yet.")
        if job_spec.resources.gpu_cores_per_process:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'gpu_cores_per_process' not supported yet.")
        if job_spec.resources.exclusive_node_use == False:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'exclusive_node_use' not supported yet.")
        if job_spec.attributes.account:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'account' not supported yet.")
        if job_spec.attributes.reservation_id:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'reservation_id' not supported yet.")
        if job_spec.attributes.custom_attributes:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, details="'custom_attributes' not supported yet.")
            

        # JobSpec
        #executable : str | None = None
        #arguments: list[str] = []
        #directory: str | None = None
        #name: str | None = None
        #stdout_path: str | None = None
        #stderr_path: str | None = None
        #resources: ResourceSpec | None = None
        #attributes: JobAttributes | None = None

        # ResourceSpec
        #memory: int | None = None

        # JobAttributes
        #duration: datetime.timedelta = datetime.timedelta(minutes=10)
        #queue_name: str | None = None

        return {}


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
