from app.routers.filesystem.facility_adapter import FacilityAdapter as FilesystemFacilityAdapter
from app.routers.status import models as status_models
from app.routers.account import models as account_models
from app.routers.filesystem import models as filesystem_models
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter
from typing import Any, Tuple

class AlcfAdapter(FilesystemFacilityAdapter, AlcfAuthenticatedAdapter):
    """Filesystem facility adapter definition for the IRI Facility API."""

    # Chmod
    async def chmod(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PutFileChmodRequest
    ) -> filesystem_models.PutFileChmodResponse:
        pass


    # Chown
    async def chown(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PutFileChownRequest
    ) -> filesystem_models.PutFileChownResponse:
        pass


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
    ) -> filesystem_models.GetDirectoryLsResponse:
        pass


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
        pass


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
        pass


    # View
    async def view(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
        size: int,
        offset: int,
    ) -> filesystem_models.GetViewFileResponse:
        pass


    # Checksum
    async def checksum(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
    ) -> filesystem_models.GetFileChecksumResponse:
        pass


    # File
    async def file(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
    ) -> filesystem_models.GetFileTypeResponse:
        pass


    # Stat
    async def stat(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
        dereference: bool,
    ) -> filesystem_models.GetFileStatResponse:
        pass


    # Rm
    async def rm(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str, 
    ):
        pass


    # Mkdir
    async def mkdir(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostMakeDirRequest,
    ) -> filesystem_models.PostMkdirResponse:
        pass


    # Sumlink
    async def symlink(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostFileSymlinkRequest,
    ) -> filesystem_models.PostFileSymlinkResponse:
        pass


    # Download
    async def download(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str,
    ) -> Any:
        pass


    # Upload
    async def upload(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        path: str,
        content: str,
    ) -> None:
        pass


    # Compress
    async def compress(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostCompressRequest,
    ) -> filesystem_models.PostCompressResponse:
        pass


    # Extract
    async def extract(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostExtractRequest,
    ) -> filesystem_models.PostExtractResponse:
        pass


    # Mv
    async def mv(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostMoveRequest,
    ) -> filesystem_models.PostMoveResponse:
        pass


    # Cp
    async def cp(
        self: "AlcfAdapter",
        resource: status_models.Resource, 
        user: account_models.User, 
        request_model: filesystem_models.PostCopyRequest,
    ) -> filesystem_models.PostCopyResponse:
        pass
