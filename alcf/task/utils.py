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
    "tail": filesystem_adaptor.tail,
    "view": filesystem_adaptor.view,
    "checksum": filesystem_adaptor.checksum,
}

# Mapping between filesystem commands and result formating functions (needed for newly generate result)
filesystem_format_functions = {
    "ls": filesystem_adaptor.format_ls_response,
    "chmod": filesystem_adaptor.format_chmod_response,
    "chown": filesystem_adaptor.format_chown_response,
    "head": filesystem_adaptor.format_head_response,
    "tail": filesystem_adaptor.format_tail_response,
    "view": filesystem_adaptor.format_view_response,
    "checksum": filesystem_adaptor.format_checksum_response,
}

# Mapping between filesystem commands and response type (needed for database extraction)
filesystem_model_responses = {
    "ls": filesystem_models.GetDirectoryLsResponse,
    "chmod": filesystem_models.PutFileChmodResponse,
    "chown": filesystem_models.PutFileChownResponse,
    "tail": filesystem_models.GetFileTailResponse,
    "view": filesystem_models.GetViewFileResponse,
    "checksum": filesystem_models.GetFileChecksumResponse,
}