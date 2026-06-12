from enum import Enum


class APIComponent(str, Enum):
    COMPUTE = "compute"
    FILESYSTEM = "filesystem"
    ACCOUNT = "account"


class EndpointType(str, Enum):
    PBS_GRAPHQL = "pbs_graphql"
    GLOBUS_MULTI_USER_ENDPOINT = "globus_multi_user_endpoint"
    NI_REST_API = "ni_rest_api"


class AllType(str, Enum):
    ALL = "all"


class IdentitySourceType(str, Enum):
    GLOBUS_CLIENT = "globus-client"
