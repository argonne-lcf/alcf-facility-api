from alcf.filesystem.alcf_adapter import AlcfAdapter as FilesystemAdaptor
from app.routers.filesystem import models as filesystem_models

# Instantiate the Filesystem adaptor
filesystem_adaptor = FilesystemAdaptor()

# Maping between filesystem commands and the adaptor functions
filesystem_commands = {
    "ls": filesystem_adaptor.ls,
    "chmod": filesystem_adaptor.chmod,
    "chown": filesystem_adaptor.chown,
    "head": filesystem_adaptor.head,
    "view": filesystem_adaptor.view
}

# Mapping between filesystem commands and result formating functions (needed for newly generate result)
filesystem_format_functions = {
    "ls": filesystem_adaptor.format_ls_response,
    "chmod": filesystem_adaptor.format_chmod_response,
    "chown": filesystem_adaptor.format_chown_response,
    "head": filesystem_adaptor.format_head_response,
    "view": filesystem_adaptor.format_view_response
}

# Mapping between filesystem commands and response type (needed for database extraction)
filesystem_model_responses = {
    "ls": filesystem_models.GetDirectoryLsResponse,
    "chmod": filesystem_models.PutFileChmodResponse,
    "chown": filesystem_models.PutFileChownResponse,
    "view": filesystem_models.GetViewFileResponse
}