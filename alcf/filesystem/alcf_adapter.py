from fastapi import HTTPException
from alcf.globus import utils as globus_utils
from app.routers.filesystem.facility_adapter import FacilityAdapter as FilesystemFacilityAdapter
from app.routers.status import models as status_models
from app.types.user import User
from app.routers.filesystem import models as filesystem_models
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter
from starlette.status import HTTP_501_NOT_IMPLEMENTED 
from typing import Any, Tuple
from alcf.filesystem.validation import (
    validate_data_with_path,
    ChmodInputData,
    ChownInputData,
    LsInputData,
    HeadInputData,
    ViewInputData,
    MkdirInputData,
    BaseModelWithPath,
)
from alcf.maintenance import require_component_operational
from alcf.enums import APIComponent
from alcf.globus.schemas import GlobusSubmitResponse
from alcf.logging.decorators import log_filesystem_operation


class AlcfAdapter(FilesystemFacilityAdapter, AlcfAuthenticatedAdapter):
    """Filesystem facility adapter definition for the IRI Facility API."""

    # Chmod
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def chmod(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        request_model: filesystem_models.PutFileChmodRequest
    ) -> GlobusSubmitResponse:
        
        # Build data for the command
        input_data = request_model.model_dump()

        # Validate data
        validate_data_with_path(input_data, ChmodInputData, resource.name)

        # Submit task with Globus and return the task ID
        return await globus_utils.submit_task("chmod", resource.name, input_data, user)


    # Format chmod response
    def format_chmod_response(
        self: "AlcfAdapter",
        result
    ) -> filesystem_models.PutFileChmodResponse:        
        return filesystem_models.PutFileChmodResponse(output=result)


    # Chown
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def chown(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        request_model: filesystem_models.PutFileChownRequest
    ) -> GlobusSubmitResponse:

        # Build data for the command
        input_data = request_model.model_dump()
        input_data["user"] = input_data.pop("owner")

        # Validate data
        validate_data_with_path(input_data, ChownInputData, resource.name)

        # Submit task with Globus and return the task ID
        return await globus_utils.submit_task("chown", resource.name, input_data, user)


    # Format chown response
    def format_chown_response(
        self: "AlcfAdapter",
        result
    ) -> filesystem_models.PutFileChownResponse:
        return filesystem_models.PutFileChmodResponse(output=result)
    

    # Ls
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def ls(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str, 
        show_hidden: bool, 
        numeric_uid: bool, 
        recursive: bool, 
        dereference: bool,
    ) -> GlobusSubmitResponse:
        
        # Disable options that are not ready yet
        if recursive:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'recursive' option not implemented yet.")
        if dereference:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'dereference' option not implemented yet.")
        
        # Build data for the command
        input_data = {
            "path": path,
            "show_hidden": show_hidden,
            "numeric_uid": numeric_uid,
            "recursive": recursive,
            "dereference": dereference
        }

        # Validate data
        validate_data_with_path(input_data, LsInputData, resource.name)

        # Submit task with Globus and return the task ID
        return await globus_utils.submit_task("ls", resource.name, input_data, user)
    

    # Format ls response
    def format_ls_response(
        self: "AlcfAdapter",
        result
    ) -> filesystem_models.GetDirectoryLsResponse:
        return filesystem_models.GetDirectoryLsResponse(output=result)
          

    # Head
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def head(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str, 
        file_bytes: int, 
        lines: int, 
        skip_trailing: bool,
    ) -> GlobusSubmitResponse:
        
        # Build data for the command
        input_data = {
            "path": path,
            "file_bytes": file_bytes,
            "lines": lines,
            "skip_trailing": skip_trailing
        }

        # Validate data
        validate_data_with_path(input_data, HeadInputData, resource.name, forbid_hidden=True)

        # Submit task with Globus and return the task ID
        return await globus_utils.submit_task("head", resource.name, input_data, user)


    # Format head response
    def format_head_response(
        self: "AlcfAdapter",
        result
    ) -> filesystem_models.GetFileHeadResponse:
        return filesystem_models.GetFileHeadResponse(**result)
    

    # Tail
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def tail(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str, 
        file_bytes: int | None, 
        lines: int | None, 
        skip_trailing: bool,
    ) -> Tuple[Any, int]:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # View
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def view(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str, 
        size: int,
        offset: int,
    ) -> GlobusSubmitResponse:
        
        # Build data for the command
        input_data = {
            "path": path,
            "size": size,
            "offset": offset
        }

        # Validate data
        validate_data_with_path(input_data, ViewInputData, resource.name, forbid_hidden=True)

        # Submit task with Globus and return the task ID
        return await globus_utils.submit_task("view", resource.name, input_data, user)


    # Format view response
    def format_view_response(
        self: "AlcfAdapter",
        result
    ) -> filesystem_models.GetViewFileResponse:
        return filesystem_models.GetViewFileResponse(**result)


    # Checksum
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def checksum(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str, 
    ) -> filesystem_models.GetFileChecksumResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # File
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def file(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str, 
    ) -> GlobusSubmitResponse:
        
        # Build data for the command
        input_data = {
            "path": path
        }

        # Validate data
        validate_data_with_path(input_data, BaseModelWithPath, resource.name)

        # Submit task with Globus and return the task ID
        return await globus_utils.submit_task("file", resource.name, input_data, user)
    
    
    # Format file response
    def format_file_response(
        self: "AlcfAdapter",
        result
    ) -> filesystem_models.GetFileTypeResponse:
        return filesystem_models.GetFileTypeResponse(**result)


    # Stat
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def stat(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str, 
        dereference: bool,
    ) -> filesystem_models.GetFileStatResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Rm
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def rm(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str, 
    ) -> GlobusSubmitResponse:
        
        # Build data for the command
        input_data = {"path": path}

        # Validate data
        validate_data_with_path(input_data, BaseModelWithPath, resource.name, forbid_hidden=True)

        # Submit task with Globus and return the task ID
        return await globus_utils.submit_task("rm", resource.name, input_data, user)
    

    # Format rm response
    def format_rm_response(
        self: "AlcfAdapter",
        result
    ) -> filesystem_models.RemoveResponse:
        return filesystem_models.RemoveResponse(output=result)


    # Mkdir
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def mkdir(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        request_model: filesystem_models.PostMakeDirRequest,
    ) -> GlobusSubmitResponse:
        
        # Build data for the command
        input_data = request_model.model_dump()

        # Validate data
        validate_data_with_path(input_data, MkdirInputData, resource.name)

        # Submit task with Globus and return the task ID
        return await globus_utils.submit_task("mkdir", resource.name, input_data, user)


    # Format mkdir response
    def format_mkdir_response(
        self: "AlcfAdapter",
        result
    ) -> filesystem_models.PostMkdirResponse:
        return filesystem_models.PostMkdirResponse(**result)


    # Sumlink
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def symlink(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        request_model: filesystem_models.PostFileSymlinkRequest,
    ) -> filesystem_models.PostFileSymlinkResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Download
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def download(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str,
    ) -> Any:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Upload
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def upload(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        path: str,
        content: str,
    ) -> None:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Compress
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def compress(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        request_model: filesystem_models.PostCompressRequest,
    ) -> filesystem_models.PostCompressResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Extract
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def extract(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        request_model: filesystem_models.PostExtractRequest,
    ) -> filesystem_models.PostExtractResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Mv
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def mv(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        request_model: filesystem_models.PostMoveRequest,
    ) -> filesystem_models.PostMoveResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")


    # Cp
    @require_component_operational(APIComponent.FILESYSTEM)
    @log_filesystem_operation
    async def cp(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: User, 
        request_model: filesystem_models.PostCopyRequest,
    ) -> filesystem_models.PostCopyResponse:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet.")
