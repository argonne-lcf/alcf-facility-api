import json

from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from typing import Any, Callable, Tuple

from app.routers.filesystem import models as filesystem_models
from app.routers.task.models import TaskStatus
from alcf.auth.utils import generate_error_message
from alcf.filesystem.alcf_adapter import AlcfAdapter as FilesystemAdaptor

# Instantiate the Filesystem adaptor
filesystem_adaptor = FilesystemAdaptor()

# Maping between filesystem commands and the adaptor functions
filesystem_commands = {
    "ls": filesystem_adaptor.ls,
    "chmod": filesystem_adaptor.chmod,
    "chown": filesystem_adaptor.chown,
    "head": filesystem_adaptor.head,
    "view": filesystem_adaptor.view,
    "mkdir": filesystem_adaptor.mkdir,
    "rm": filesystem_adaptor.rm,
    "file": filesystem_adaptor.file,
    "mv": filesystem_adaptor.mv,
    "cp": filesystem_adaptor.cp,
}

# Mapping between filesystem commands and result formating functions (needed for newly generate result)
filesystem_format_functions = {
    "ls": filesystem_adaptor.format_ls_response,
    "chmod": filesystem_adaptor.format_chmod_response,
    "chown": filesystem_adaptor.format_chown_response,
    "head": filesystem_adaptor.format_head_response,
    "view": filesystem_adaptor.format_view_response,
    "mkdir": filesystem_adaptor.format_mkdir_response,
    "rm": filesystem_adaptor.format_rm_response,
    "file": filesystem_adaptor.format_file_response,
    "mv": filesystem_adaptor.format_mv_response,
    "cp": filesystem_adaptor.format_cp_response,
}

# Mapping between filesystem commands and response type (needed for database extraction)
filesystem_model_responses = {
    "ls": filesystem_models.GetDirectoryLsResponse,
    "chmod": filesystem_models.PutFileChmodResponse,
    "chown": filesystem_models.PutFileChownResponse,
    "view": filesystem_models.GetViewFileResponse,
    "mkdir": filesystem_models.PostMkdirResponse,
    "file": filesystem_models.GetFileTypeResponse,
    "mv": filesystem_models.PostMoveResponse,
    "cp": filesystem_models.PostCopyResponse,
}

# Format result for database
def format_result_for_db(
    result: Any,
    status: TaskStatus,
    format_function: Callable
) -> Any:
    """Format result field and return json string for database."""

    # None if no result was provided
    if result is None:
        return None
    
    # Successful completed tasks
    if status == TaskStatus.completed.value:
        
        # Format result to the IRI spec
        try:
            result = format_function(result) # This should give a pydantic model instance
        except Exception as e:
            error_message = generate_error_message("Completed task result not compliant with IRI spec.", e)
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )
        
        # Return json string
        if isinstance(result, Tuple):
            return json.dumps(result)
        else:
            return json.dumps(result.model_dump())
    
    # Failed tasks
    elif status == TaskStatus.failed.value:
                
        # Add dictionary wrap if needed
        if isinstance(result, str):
            result = {"error": result}

        # Return json string
        try:
            return json.dumps(result)
        except Exception as e:
            error_message = generate_error_message("Failed task result cannot be converted to JSON.", e)
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )

    # Skip formatting if task still active or pending
    else:
        return result