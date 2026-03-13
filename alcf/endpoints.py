from typing import Generic, TypeVar
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException

# ====================
# Reusable definitions
# ====================

# Endpoint type enumeration
class EndpointType(str, Enum):
    PBS_GRAPHQL = "pbs_graphql"
    GLOBUS_MULTI_USER_ENDPOINT = "globus_multi_user_endpoint"

# Common pydantic mode template for all types of endpoints
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
class _GraphqlEndpointConfig(BaseModel):
    url: str

# GraphQL endpoint implementation
class GraphqlEndpoint(_BaseEndpoint):

    # Data validation upon initialization
    def __init__(self, input_params: dict):
        super().__init__(input_params, _EndpointParams[_GraphqlEndpointConfig])

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
_ENDPOINTS: dict[str, type[_BaseEndpoint]] = {
    "pbs_graphql": GraphqlEndpoint,
    "globus_multi_user_endpoint": GlobusMultiUserEndpoint,
}

# Function to retrieve an endpoint from its type
def get_endpoint(input_params: dict) -> _BaseEndpoint:

    # Recover the class type from the endpoint type
    endpoint_type = input_params.get("endpoint_type")
    cls = _ENDPOINTS.get(endpoint_type, None)

    # Error if the endpoint type is unknown
    if cls is None:
        raise HTTPException(
            status_code=500,
            detail=f"Unknown endpoint type '{endpoint_type}'. Expected one of: {list(_ENDPOINTS)}"
        )

    # Initialize the endpoint and return the instance
    return cls(input_params)
