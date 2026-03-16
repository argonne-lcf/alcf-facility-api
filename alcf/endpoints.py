from typing import Generic, TypeVar
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException
from enum import Enum
from alcf.config import ALCF_ENDPOINTS
from starlette.status import (
    HTTP_501_NOT_IMPLEMENTED,
    HTTP_404_NOT_FOUND,
    HTTP_400_BAD_REQUEST,
)

# ====================
# Reusable definitions
# ====================

# API component enumeration
class APIComponent(str, Enum):
    COMPUTE = "compute"
    FILESYSTEM = "filesystem"
    ACCOUNT = "account"


# Endpoint type enumeration
class EndpointType(str, Enum):
    PBS_GRAPHQL = "pbs_graphql"
    GLOBUS_MULTI_USER_ENDPOINT = "globus_multi_user_endpoint"


# Common pydantic model template for all types of endpoints
ConfigT = TypeVar("ConfigT", bound=BaseModel)
class _EndpointParams(BaseModel, Generic[ConfigT]):
    endpoint_type: str
    config: ConfigT


# Common base class for all types of endpoints
class _BaseEndpoint:

    # Data validation upon initialization
    def __init__(self, input_params: dict, params_model: type[BaseModel]):
        try:
            self._validated = params_model(**input_params)
        except ValidationError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid endpoint configuration: {e}"
            )

    # Endpoint type property
    @property
    def endpoint_type(self) -> str:
        return self._validated.endpoint_type


# ================
# GraphQL endpoint
# ================

# GraphQL endpoint configuration
class _PBSGraphqlEndpointConfig(BaseModel):
    url: str


# GraphQL endpoint implementation
class PBSGraphqlEndpoint(_BaseEndpoint):

    # Data validation upon initialization
    def __init__(self, input_params: dict):
        super().__init__(input_params, _EndpointParams[_PBSGraphqlEndpointConfig])

    # URL property
    @property
    def url(self) -> str:
        return self._validated.config.url


# ==========================
# Globus multi-user endpoint
# ==========================

# Globus multi-user endpoint configuration
class _GlobusMultiUserEndpointConfig(BaseModel):
    location: str
    endpoint_id: str
    function_id: str


# Globus multi-user endpoint implementation
class GlobusMultiUserEndpoint(_BaseEndpoint):

    # Data validation upon initialization
    def __init__(self, input_params: dict):
        super().__init__(input_params, _EndpointParams[_GlobusMultiUserEndpointConfig])

    # Location property
    @property
    def location(self) -> str:
        return self._validated.config.location

    # Endpoint ID property
    @property
    def endpoint_id(self) -> str:
        return self._validated.config.endpoint_id

    # Function ID property
    @property
    def function_id(self) -> str:
        return self._validated.config.function_id


# ==================
# Endpoint retrieval
# ==================

# Endpoint registry
_ENDPOINT_CLASSES: dict[str, type[_BaseEndpoint]] = {
    EndpointType.PBS_GRAPHQL.value: PBSGraphqlEndpoint,
    EndpointType.GLOBUS_MULTI_USER_ENDPOINT.value: GlobusMultiUserEndpoint,
}


# Function to retrieve an endpoint from its type
def get_endpoint(
    resource_name: str = None,
    operation: str = None,
    api_component: APIComponent = None
    ) -> _BaseEndpoint:

    # Error if the API component does not exist
    if api_component is None or api_component not in APIComponent:    
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, 
            detail=f"Endpoints for API component {api_component} do not exist."
        )

    # Error if the API component is not implemented yet
    if api_component not in ALCF_ENDPOINTS:
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED, 
            detail=f"Endpoints for API component {api_component} not available yet."
        )

    # Extract resource dictionary from input alcf_endpoints.json
    resource_dict = ALCF_ENDPOINTS[api_component].get(resource_name.lower(), {})
    if not resource_dict:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, 
            detail=f"Endpoint resource {resource_name} does not exist for API component {api_component}."
        )

    # Extract the endpoint dictionary from the resource dictionary
    endpoint_dict = resource_dict.get(operation.lower(), {})
    if not endpoint_dict:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, 
            detail=f"Endpoint operation {operation} does not exist for resource {resource_name}."
        )

    # Error if endpoint type does not exist
    endpoint_type = endpoint_dict.get("endpoint_type", "")
    if endpoint_type not in _ENDPOINT_CLASSES:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, 
            detail=f"Endpoint type {endpoint_type} does not exist."
        )

    # Recover the endpoint class from the endpoint type
    cls = _ENDPOINT_CLASSES.get(endpoint_type)

    # Initialize the endpoint and return the instance
    return cls(endpoint_dict)
