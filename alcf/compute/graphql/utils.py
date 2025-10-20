import httpx
import json
from json.decoder import JSONDecodeError
from fastapi import HTTPException
from app.routers.account.models import User
from app.routers.compute.models import JobSpec
from alcf.compute.graphql.models import (
    Job,
    JobResponse,
    JobResources,
    JobTasksResources,
    Queue,
    QueryJobsFilter,
)
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
    user: User, 
    job_spec: JobSpec
) -> str:
        
    # Build queue
    queue = Queue(
        name=job_spec.attributes.queue_name
    )

    # Build job resources
    jobResources = JobTasksResources(
        physicalMemory=job_spec.resources.memory,
        wallClockTime=job_spec.attributes.duration.seconds
    )

    # Build resources requested
    resourcesRequested = JobResources(
        jobResources=jobResources
    )
        
    # Build query data
    input_data = Job(
        remoteCommand=job_spec.executable,
        commandArgs=job_spec.arguments,
        name=job_spec.name,
        errorPath=job_spec.stderr_path,
        outputPath=job_spec.stdout_path,
        queue=queue,
        resourcesRequested=resourcesRequested
    )

    # Generate and return the job submission GraphQL query
    input_data = input_data.model_dump(exclude_none=True)
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
    user: User, 
    job_id: str,
    historical: bool = False,
) -> str:
        
    # Build job query filter
    filter_data = QueryJobsFilter(
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
    user: User, 
    job_id: str,
) -> str:
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


# Post GraphQL
# TODO: Remove verify_ssl once PBS GraphQL is outside of the dev environment
async def post_graphql(
    query: str = None,
    user: User = None,
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
def validate_job_response(data: dict, keys: list) -> JobResponse:
    try:

        # Access the subset of data within the dictionary
        for key in keys:
            data = data[key]

        # Convert the targeted subset into a JobRequest object
        return JobResponse(**data)
    
    # Error message if something goes wrong
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compute query response could not be parsed: {e}"
        )