import httpx
import json
from json.decoder import JSONDecodeError
from fastapi import HTTPException
from app.routers.account import models as account_models
from app.routers.compute import models as compute_models
from alcf.compute.graphql import models as graphql_models
from alcf.config import GRAPHQL_HTTPX_TRUST_ENV
from starlette.status import (
    HTTP_400_BAD_REQUEST, 
    HTTP_408_REQUEST_TIMEOUT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

# Get indents
def get_indent_strings(indent: int, base_indent: int):
    return " " * indent, " " * base_indent


# Dictionary to GraphQL
def dictionary_to_graphql_str(d: dict, base_indent: int = 0, indent: int = 4) -> str:
    """Convert an input dictionary into a GraphQL-compatible string."""

    # Generate indent spacings
    base_indent_str, indent_str = get_indent_strings(base_indent, indent)
    
    # Initialize the GraphQL-compatible string
    string = "{\n"

    # Convert each key-value pair in the dictionary
    for key, value in d.items():
        convertion = format_graphql_block(value, base_indent=base_indent, indent=indent)
        string += base_indent_str + indent_str + f"{key}: {convertion}\n"

    # Close the dictionary and return the string
    return f"{string}{base_indent_str}}}"


# List to GraphQL
def list_to_graphql_str(l: list, indent: int = 4, base_indent: int = 0) -> str:
    """Convert an input list into a GraphQL-compatible string."""
    
    # Generate indent spacings
    base_indent_str, indent_str = get_indent_strings(base_indent, indent)
    
    # Initialize the GraphQL-compatible string
    string = "[\n"
    
    # Convert each item in the list
    last_i = len(l) - 1
    for i, item in enumerate(l):
        convertion = format_graphql_block(item, base_indent=base_indent, indent=indent)
        string += base_indent_str + indent_str + convertion
        if i != last_i:
            string += ",\n"
                
    # Remove trailingClose the list and return the string
    return f"{string}\n{base_indent_str}]"


# Format GraphQL block
def format_graphql_block(block, base_indent: int = 0, indent: int = 4) -> str:
    """Generic fonction to format a block of a dictionary into a GraphQL-compatible string."""

    # Boolean
    if isinstance(block, bool):
        return json.dumps(block)

    # String
    elif isinstance(block, str):
        return f"\"{block}\""
    
    # Number
    elif isinstance (block, (int, float)):
        return block
    
    # List
    elif isinstance(block, list):
        return list_to_graphql_str(block, base_indent=base_indent+indent, indent=indent)
        
    # Dictionary
    elif isinstance(block, dict):
        return dictionary_to_graphql_str(block, base_indent=base_indent+indent, indent=indent)
        
    # Error for unsupported type
    else:
        raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Type {type(block)} not supported in format_graphql_block."
            )


# Build submit job query
def build_submit_job_query(
    user: account_models.User, 
    graphql_job: graphql_models.Job
) -> str:

    # Generate and return the job submission GraphQL query
    input_data = graphql_job.model_dump(exclude_none=True)
    return f"""
        mutation {{
            createJob (
                input: {dictionary_to_graphql_str(input_data, base_indent=16, indent=4)}
            ) {{
                node {{
                    jobId
                    status {{
                        state
                        exitStatus
                    }}
                }}
                error {{
                    errorCode
                    errorMessage
                }}
            }}
        }}
    """
    

# Build get job query
def build_get_job_query(
    user: account_models.User, 
    job_id: str = None,
    historical: bool = False,
) -> str:
        
    # Build job query filter
    filter_data = graphql_models.QueryJobsFilter(
        withHistoryJobs=historical,
        jobIds=job_id
    )

    # Generate and return the job submission GraphQL query
    filter_data = filter_data.model_dump(exclude_none=True)
    return f"""
        query {{
            jobs (
                filter: {dictionary_to_graphql_str(filter_data, base_indent=16, indent=4)}
            ) {{
                edges {{
                    node {{
                        jobId
                        status {{
                            state
                            exitStatus
                        }}
                    }}
                }}
            }}
        }}
    """
    

# Build candel job query
def build_cancel_job_query(
    user: account_models.User, 
    job_id: str,
) -> str:
    
    # Generate and return the job submission GraphQL query
    return f"""
        mutation {{
            deleteJob (jobId: "{job_id}" input: {{}}) {{
                node {{
                    jobId
                }}
                error {{
                    jobId
                    errorCode
                    errorMessage
                }}
            }}
        }}
    """


# Build update job query
def build_update_job_query(
    user: account_models.User, 
    graphql_job: graphql_models.Job,
    job_id: str,
) -> str:
    
    # Generate and return the job submission GraphQL query
    input_data = graphql_job.model_dump(exclude_none=True)
    return f"""
        mutation {{
            updateJob (
                jobId: "{job_id}",
                input: {dictionary_to_graphql_str(input_data, base_indent=16, indent=4)}
            ) {{
                node {{
                    jobId
                    status {{
                        state
                        exitStatus
                    }}
                }}
                error {{
                    errorCode
                    errorMessage
                }}
            }}
        }}
    """


# Post GraphQL
# TODO: Remove verify_ssl once PBS GraphQL is outside of the dev environment
async def post_graphql(
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
        async with httpx.AsyncClient(verify=verify_ssl, trust_env=GRAPHQL_HTTPX_TRUST_ENV) as client:
            response = await client.post(url, json={"query": query}, headers=headers, timeout=10)
            response = response.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=HTTP_408_REQUEST_TIMEOUT,
            detail="Compute query timed out."
        )
    except JSONDecodeError as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compute query response could not be parsed: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compute query failed: {e}"
        )
        
    # Return the response (already parsed)
    return response


# Validate Job responses from GraphQL
def validate_job_response(data: dict) -> graphql_models.JobResponse:
    
    # Convert the targeted subset into a JobRequest object
    try:
        return graphql_models.JobResponse(**data)
    
    # Error message if something goes wrong
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compute query response could not be validated: {e}"
        )