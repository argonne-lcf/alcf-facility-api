from fastapi import HTTPException
from starlette.status import HTTP_304_NOT_MODIFIED, HTTP_400_BAD_REQUEST
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
        pass


    @abstractmethod
    def update_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_spec: compute_models.JobSpec,
        job_id: str,
    ) -> compute_models.Job:
        pass


    @abstractmethod
    def get_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
        historical: bool = False,
    ) -> compute_models.Job:
        pass

    
    @abstractmethod
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

    
    @abstractmethod
    def cancel_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
    ) -> bool:
        pass
