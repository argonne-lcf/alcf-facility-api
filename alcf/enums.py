from enum import Enum


class APIComponent(str, Enum):
    COMPUTE = "compute"
    FILESYSTEM = "filesystem"
    ACCOUNT = "account"


class EndpointType(str, Enum):
    PBS_GRAPHQL = "pbs_graphql"
    GLOBUS_MULTI_USER_ENDPOINT = "globus_multi_user_endpoint"
    GLOBUS_TRANSFER_ENDPOINT = "globus_transfer_endpoint"
