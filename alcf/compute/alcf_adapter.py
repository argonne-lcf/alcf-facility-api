import json
from functools import wraps
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from app.routers.compute.facility_adapter import FacilityAdapter as ComputeFacilityAdapter
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter
from alcf.auth.utils import KEYCLOAK_FLAG
from alcf.database.database import add_access_log_to_db, add_compute_log_to_db
from alcf.auth.keycloak_utils import generate_user_keycloak_token
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
    post_graphql,
    get_graphql_url
)

# Function wrapper to create access log object
def create_log_objects(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Extract function inputs
        try:
            user: account_models.User = kwargs["user"]
            resource: status_models.Resource = kwargs["resource"]
        except Exception:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not acces user and or resource from kwargs."
            )

        # Create AccessLog data
        try:
            kwargs["db_access_log"] = {
                "id": str(uuid4()),
                "user_id": user.id,
                "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
                "api_route": f"compute/{func.__name__}",
                "origin_ip": user.client_ip,
            }
        except Exception:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create AccessLog initial data."
            )
        
        # Create ComputeLog data
        try:
            kwargs["db_compute_log"] = {
                "id": str(uuid4()),
                "access_log_id": kwargs["db_access_log"]["id"],
                "resource_id": resource.id,
            }
        except Exception:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create ComputeLog initial data."
            )

        # Execute the function
        return await func(*args, **kwargs)
    return wrapper


class AlcfAdapter(ComputeFacilityAdapter, AlcfAuthenticatedAdapter):
    """Compute facility adapter definition for the IRI Facility API."""

    # Submit job
    @create_log_objects
    async def submit_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_spec: compute_models.JobSpec,
        db_access_log: dict = None,
        db_compute_log: dict = None,
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
        graphql_data = get_graphql_job_from_iri_jobspec(job_spec)

        # Generate Keycloak access token for user if necessary
        if KEYCLOAK_FLAG in user.api_key:
            user_keycloak_access_token = user.api_key.replace(KEYCLOAK_FLAG, "")
            alcf_username = user.user_id
        else:
            user_keycloak_access_token, alcf_username = generate_user_keycloak_token(user)

        # Submit query to GraphQL API
        db_compute_log["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_submit_job_query(user, graphql_data),
            url=graphql_url
        )
        db_compute_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

        # Extract raw job response into GraphQL JobResponse pydantic object
        response = self.__extract_job_response(response, ["data", "createJob"])
        
        # Create IRI-compliant job response
        iri_response = get_iri_job_from_graphql_job(response.node)
    
        # Finalize database logging
        db_compute_log["input"] = json.dumps({
            "job_spec": job_spec.model_dump()
        })
        db_compute_log["result"] = json.dumps(iri_response.model_dump())
        db_compute_log["alcf_username"] = alcf_username
        db_access_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        db_access_log["status_code"] = 200
        await add_compute_log_to_db(db_compute_log)
        await add_access_log_to_db(db_access_log)
    
        # Return IRI-compliant response
        return iri_response
    

    # Submit job script
    @create_log_objects
    async def submit_job_script(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_script_path: str,
        args: list[str] = [],
        db_access_log: dict = None,
        db_compute_log: dict = None,
    ) -> compute_models.Job:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Capability not implemented")


    # Update job
    @create_log_objects
    async def update_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_spec: compute_models.JobSpec,
        job_id: str,
        db_access_log: dict = None,
        db_compute_log: dict = None,
    ) -> compute_models.Job:
        
        # Recover GraphQL URL
        graphql_url = get_graphql_url(resource.name)
        
        # Convert IRI Job spec into GraphQL Job spec
        graphql_data = get_graphql_job_from_iri_jobspec(job_spec)

        # Generate Keycloak access token for user if necessary
        if KEYCLOAK_FLAG in user.api_key:
            user_keycloak_access_token = user.api_key.replace(KEYCLOAK_FLAG, "")
            alcf_username = user.user_id
        else:
            user_keycloak_access_token, alcf_username = generate_user_keycloak_token(user)
        
        # Submit query to GraphQL API
        db_compute_log["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_update_job_query(user, graphql_data, job_id),
            url=graphql_url
        )
        db_compute_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

        # Extract raw job response into GraphQL JobResponse pydantic object
        response = self.__extract_job_response(response, ["data", "updateJob"])
        
        # Create IRI-compliant job response
        iri_response = get_iri_job_from_graphql_job(response.node)
    
        # Finalize database logging
        db_compute_log["input"] = json.dumps({
            "job_spec": job_spec.model_dump(),
            "job_id": job_id
        })
        db_compute_log["result"] = json.dumps(iri_response.model_dump())
        db_compute_log["alcf_username"] = alcf_username
        db_access_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        db_access_log["status_code"] = 200
        await add_compute_log_to_db(db_compute_log)
        await add_access_log_to_db(db_access_log)

        # Return IRI-compliant response
        return iri_response
    

    # Get job
    @create_log_objects
    async def get_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
        historical: bool = False,
        include_spec: bool = False,
        db_access_log: dict = None,
        db_compute_log: dict = None,
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
            alcf_username = user.user_id
        else:
            user_keycloak_access_token, alcf_username = generate_user_keycloak_token(user)
        
        # Submit query to GraphQL API
        db_compute_log["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_get_job_query(user, job_id=job_id, historical=historical),
            url=graphql_url
        )
        db_compute_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

        # Extract raw job response into GraphQL JobResponse pydantic object
        response = self.__extract_job_response(response, ["data", "jobs", "edges", 0])

        # Error if no job exists
        if not response.node:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} not found."
            )

        # Create IRI-compliant job response
        iri_response = get_iri_job_from_graphql_job(response.node)
    
        # Finalize database logging
        db_compute_log["input"] = json.dumps({
            "job_id": job_id,
            "historical": historical,
            "include_spec": include_spec
        })
        db_compute_log["result"] = json.dumps(iri_response.model_dump())
        db_compute_log["alcf_username"] = alcf_username
        db_access_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        db_access_log["status_code"] = 200
        await add_compute_log_to_db(db_compute_log)
        await add_access_log_to_db(db_access_log)

        # Return IRI-compliant response
        return iri_response

    
    # Get jobs
    @create_log_objects
    async def get_jobs(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        offset : int,
        limit : int,
        filters: dict[str, object] | None = None,
        historical: bool = False,
        include_spec: bool = False,
        db_access_log: dict = None,
        db_compute_log: dict = None,
    ) -> list[compute_models.Job]:
        
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
        graphql_url = get_graphql_url(resource.name)

        # Generate Keycloak access token for user if necessary
        if KEYCLOAK_FLAG in user.api_key:
            user_keycloak_access_token = user.api_key.replace(KEYCLOAK_FLAG, "")
            alcf_username = user.user_id
        else:
            user_keycloak_access_token, alcf_username = generate_user_keycloak_token(user)

        # Submit query to GraphQL API
        db_compute_log["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_get_job_query(user, historical=historical),
            url=graphql_url
        )
        db_compute_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        
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

        # Return IRI-compliant job response
        iri_response = [get_iri_job_from_graphql_job(r.node) for r in responses]
    
        # Finalize database logging
        db_compute_log["input"] = json.dumps({
            "offset": offset,
            "limit": limit,
            "filters": filters,
            "historical": historical,
            "include_spec": include_spec
        })
        db_compute_log["result"] = json.dumps([r.model_dump() for r in iri_response])
        db_compute_log["alcf_username"] = alcf_username
        db_access_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        db_access_log["status_code"] = 200
        await add_compute_log_to_db(db_compute_log)
        await add_access_log_to_db(db_access_log)

        # Return IRI-compliant response
        return iri_response

    
    # Cancel job
    @create_log_objects
    async def cancel_job(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        job_id: str,
        db_access_log: dict = None,
        db_compute_log: dict = None,
    ) -> bool:

        # Recover GraphQL URL
        graphql_url = get_graphql_url(resource.name)

        # Generate Keycloak access token for user if necessary
        if KEYCLOAK_FLAG in user.api_key:
            user_keycloak_access_token = user.api_key.replace(KEYCLOAK_FLAG, "")
            alcf_username = user.user_id
        else:
            user_keycloak_access_token, alcf_username = generate_user_keycloak_token(user)
        
        # Submit query to GraphQL API
        db_compute_log["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        response = await post_graphql(
            access_token=user_keycloak_access_token,
            query=build_cancel_job_query(user, job_id),
            url=graphql_url
        )
        db_compute_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

        # Extract raw job response into GraphQL JobResponse pydantic object
        response = self.__extract_job_response(response, ["data", "deleteJob"])

        # Finalize database logging
        db_compute_log["input"] = json.dumps({
            "job_id": job_id
        })
        db_compute_log["result"] = json.dumps(response.model_dump())
        db_compute_log["alcf_username"] = alcf_username
        db_access_log["responded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        db_access_log["status_code"] = 200
        await add_compute_log_to_db(db_compute_log)
        await add_access_log_to_db(db_access_log)
        
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
    