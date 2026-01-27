from fastapi import HTTPException
from alcf.globus import utils as globus_utils
from app.routers.filesystem.facility_adapter import FacilityAdapter as FilesystemFacilityAdapter
from app.routers.status import models as status_models
from app.routers.account import models as account_models
from app.routers.filesystem import models as filesystem_models
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter
from starlette.status import HTTP_501_NOT_IMPLEMENTED, HTTP_400_BAD_REQUEST 
from typing import Any, Tuple
from alcf.filesystem.utils import get_iri_file_from_ls_line
from alcf.filesystem import validation

class AlcfAdapter(FilesystemFacilityAdapter, AlcfAuthenticatedAdapter):
    """Filesystem facility adapter definition for the IRI Facility API."""

    # Chmod
    async def chmod(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PutFileChmodRequest
    ) -> filesystem_models.PutFileChmodResponse:
    
        # Build data for the command
        input_data = request_model.model_dump()

        # Validate data
        try:
            _ = validation.ChmodInputData(**input_data)
        except Exception as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Input validation error: {str(e)}")

        # Submit task to Globus Compute and wait for the result
        result = globus_utils.submit_task_and_get_result("chmod", resource, input_data, user)
        
        # Convert result (should only be one line) into IRI File and return the object
        return filesystem_models.PutFileChmodResponse(
            output=get_iri_file_from_ls_line(result)
        )


    # Chown
    async def chown(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PutFileChownRequest
    ) -> filesystem_models.PutFileChownResponse:

        # Build data for the command
        input_data = request_model.model_dump()

        # Validate data
        try:
            _ = validation.ChownInputData(**input_data)
        except Exception as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Input validation error: {str(e)}")

        # Submit task to Globus Compute and wait for the result
        result = globus_utils.submit_task_and_get_result("chown", resource, input_data, user)
        
        # Convert result (should only be one line) into IRI File and return the object
        return filesystem_models.PutFileChmodResponse(
            output=get_iri_file_from_ls_line(result)
        )


    # Ls
    async def ls(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
        show_hidden: bool, 
        numeric_uid: bool, 
        recursive: bool, 
        dereference: bool,
    ) -> str:
        
        # Disable options that are not ready yet
        if recursive:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'recursive' option not implemented yet.")
        
        # Build data for the command
        input_data = {
            "path": path,
            "show_hidden": show_hidden,
            "numeric_uid": numeric_uid,
            "recursive": recursive,
            "dereference": dereference
        }

        # Validate data
        try:
            _ = validation.LsInputData(**input_data)
        except Exception as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Input validation error: {str(e)}")

        # Submit task to Globus Compute and wait for the task ID
        task_id = await globus_utils.submit_task("ls", resource, input_data, user)

        # Return task ID to the user
        return task_id
    

    # Ls get result
    async def ls_get_result(
        self: "AlcfAdapter",
        user: account_models.User, 
        task_id: str
    ) -> filesystem_models.GetDirectoryLsResponse:
        
        return "A"
        # Recover all lines from the command
        #lines = [line.strip() for line in result.splitlines() if line.strip()]

        # Convert lines into IRI File and return array
        #return filesystem_models.GetDirectoryLsResponse(
        #    output=[get_iri_file_from_ls_line(line) for line in lines if len(line.split()) > 2]
        #)
          

    # Head
    async def head(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
        file_bytes: int, 
        lines: int, 
        skip_trailing: bool,
    ) -> Tuple[Any, int]:
        
        # Build data for the command
        input_data = {
            "path": path,
            "file_bytes": file_bytes,
            "lines": lines,
            "skip_trailing": skip_trailing
        }

        # Validate data
        try:
            _ = validation.HeadInputData(**input_data)
        except Exception as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Input validation error: {str(e)}")

        # Submit task to Globus Compute and wait for the result
        result = globus_utils.submit_task_and_get_result("head", resource, input_data, user)

        # Get the end_position
        end_position = len(result)

        # Return IRI response
        return result, end_position


    # Tail
    async def tail(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
        file_bytes: int | None, 
        lines: int | None, 
        skip_trailing: bool,
    ) -> Tuple[Any, int]:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # View
    async def view(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
        size: int,
        offset: int,
    ) -> filesystem_models.GetViewFileResponse:
        
        # Build data for the command
        input_data = {
            "path": path,
            "size": size,
            "offset": offset
        }

        # Validate data
        try:
            _ = validation.ViewInputData(**input_data)
        except Exception as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Input validation error: {str(e)}")

        # Submit task to Globus Compute and wait for the result
        result = globus_utils.submit_task_and_get_result("view", resource, input_data, user)

        # Return IRI response
        return filesystem_models.GetViewFileResponse(output=result)


    # Checksum
    async def checksum(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
    ) -> filesystem_models.GetFileChecksumResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # File
    async def file(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
    ) -> filesystem_models.GetFileTypeResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Stat
    async def stat(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
        dereference: bool,
    ) -> filesystem_models.GetFileStatResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Rm
    async def rm(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
    ):
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Mkdir
    async def mkdir(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostMakeDirRequest,
    ) -> filesystem_models.PostMkdirResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Sumlink
    async def symlink(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostFileSymlinkRequest,
    ) -> filesystem_models.PostFileSymlinkResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Download
    async def download(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str,
    ) -> Any:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Upload
    async def upload(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str,
        content: str,
    ) -> None:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Compress
    async def compress(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostCompressRequest,
    ) -> filesystem_models.PostCompressResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Extract
    async def extract(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostExtractRequest,
    ) -> filesystem_models.PostExtractResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Mv
    async def mv(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostMoveRequest,
    ) -> filesystem_models.PostMoveResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Cp
    async def cp(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostCopyRequest,
    ) -> filesystem_models.PostCopyResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")
