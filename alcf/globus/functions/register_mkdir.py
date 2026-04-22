from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_compute_sdk import Client
import json
import os

# Constants
FILE_NAME = "function_ids.json"
COMMAND = "mkdir"

# Globus Compute function definition mkdir)
def mkdir(params):

    # Import all necessary packages
    from pathlib import Path
    from pydantic import BaseModel, ConfigDict, Field, field_validator
    from typing import Optional
    import grp
    import os
    import pwd
    import re
    import stat
    from datetime import datetime, timezone

    # Clear environment variables
    os.environ.clear()

    # ===================================
    # Pydantic models and data validation
    # ===================================

    # Define allowed paths
    CURRENT_USERNAME = pwd.getpwuid(os.getuid()).pw_name
    ALLOWED_PATH_BASES = (
        Path(f"/home/{CURRENT_USERNAME}"),
        Path("/eagle"),
        Path("/lus/eagle"),
    )
    ALLOWED_PATHS_TEXT = ", ".join(str(p) for p in ALLOWED_PATH_BASES)
    def is_allowed_path(path: Path) -> bool:
        return any(path == base or str(path).startswith(f"{base}/") for base in ALLOWED_PATH_BASES)

    # Base class that excludes extra fields
    class BaseModelWithForbiddenExtra(BaseModel):
        model_config = ConfigDict(extra="forbid")

    # Pydantic model for entry info
    class File(BaseModelWithForbiddenExtra):
        name: str
        type: str
        link_target: Optional[str] = None
        user: str
        group: str
        permissions: str
        last_modified: str
        size: str

    # Pydantic for function response
    class Response(BaseModelWithForbiddenExtra):
        output: Optional[File] = None
        error: Optional[str] = None

    # Pydantic for input data
    class InputData(BaseModelWithForbiddenExtra):
        path: Path
        parent: bool = Field(default=False)

        # Path validation: forbidden chars, absolute required
        @field_validator("path", mode="before")
        @classmethod
        def validate_path_format(cls, v) -> Path:
            s = str(v) if not isinstance(v, Path) else str(v)
            if "\0" in s:
                raise ValueError("Null byte not allowed in path.")
            if not re.compile(r"^[\w\-./\\]+$").fullmatch(s):
                raise ValueError("Path contains forbidden characters.")
            p = Path(s)
            if not p.is_absolute():
                raise ValueError("Path must be absolute.")
            if any(part in (".", "..") for part in p.parts):
                raise ValueError("Path cannot contain '.' or '..' segments.")
            return p

        # Path allowlist validation: /home/<username>, /eagle, /lus/eagle
        @field_validator("path")
        @classmethod
        def validate_path_prefix(cls, p: Path) -> Path:
            if not is_allowed_path(p):
                raise ValueError(f"Path must start with one of: {ALLOWED_PATHS_TEXT}.")
            return p

    # Validate input data
    try:
        input_data = InputData(**params)
    except ValueError as e:
        return Response(error=f"Input validation error: {e}").model_dump()
    except Exception:
        return Response(error="Unexpected error occurred during pydantic validation.").model_dump()

    # ======================
    # Helper function
    # ======================

    # Get file type
    def get_file_type(mode: int) -> str:
        if stat.S_ISDIR(mode):
            return "directory"
        if stat.S_ISREG(mode):
            return "file"
        if stat.S_ISLNK(mode):
            return "symlink"
        return "unknown"

    # Get user and group
    def get_user_group(stat_info):
        try:
            user = pwd.getpwuid(stat_info.st_uid).pw_name
        except KeyError:
            user = str(stat_info.st_uid)
        try:
            group = grp.getgrgid(stat_info.st_gid).gr_name
        except KeyError:
            group = str(stat_info.st_gid)
        return user, group

    # Build entry info dictionary
    def build_entry_info(file_path: Path, stat_info: os.stat_result) -> File:
        mode = stat_info.st_mode
        file_type = get_file_type(mode)
        user, group = get_user_group(stat_info)
        last_modified = datetime.fromtimestamp(
            stat_info.st_mtime, tz=timezone.utc
        ).isoformat().replace("+00:00", "Z")
        return File(
            name=file_path.name,
            type=file_type,
            link_target="",
            user=user,
            group=group,
            permissions=stat.filemode(mode)[1:],
            last_modified=last_modified,
            size=str(stat_info.st_size),
        )

    # =========================
    # Execute the mkdir command
    # =========================

    path = input_data.path

    # Start from provided path, and go down until the nearest existing ancestor is found
    ancestor = path
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent

    # Resolve nearest existing ancestor and make sure it stays in allowed bases
    try:
        resolved_ancestor = ancestor.resolve(strict=True)
    except OSError:
        return Response(error=f"Parent path {ancestor} does not exist.").model_dump()
    if not is_allowed_path(resolved_ancestor):
        return Response(
            error=f"Resolved parent path must stay under one of: {ALLOWED_PATHS_TEXT}."
        ).model_dump()

    # Pre-resolve full target path (non-strict) and ensure final destination stays in allowed bases
    # before executing mkdir, so we fail early instead of creating and then rejecting.
    resolved_target = path.resolve(strict=False)
    if not is_allowed_path(resolved_target):
        return Response(
            error=f"Resolved target path must stay under one of: {ALLOWED_PATHS_TEXT}."
        ).model_dump()

    # Create directory
    try:
        path.mkdir(parents=input_data.parent, exist_ok=False)
    except FileExistsError:
        return Response(error=f"Path {path} already exists.").model_dump()
    except Exception:
        return Response(error=f"Could not create directory {path}. Maybe try with parent=True?").model_dump()

    # Resolve created path for metadata
    try:
        resolved_created = path.resolve(strict=True)
    except OSError:
        return Response(error=f"mkdir error: could not resolve created path: {path}").model_dump()
    try:
        stat_info = os.lstat(str(resolved_created))
    except OSError:
        return Response(error=f"Unexpected mkdir error").model_dump()

    # Return the file information
    output = build_entry_info(resolved_created, stat_info)
    return Response(output=output).model_dump()


# Create Globus Compute client
gcc = Client(code_serialization_strategy=CombinedCode())

# Register the function
COMPUTE_FUNCTION_ID = gcc.register_function(mkdir, public=True)

# Load file that stores all function IDs
if os.path.exists(FILE_NAME):
    with open(FILE_NAME, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise e
else:
    data = {}

# Add or update the file content
data[COMMAND] = COMPUTE_FUNCTION_ID
with open(FILE_NAME, "w") as f:
    json.dump(data, f, indent=4)

# Print details
print(f"Updated {FILE_NAME} with {COMMAND}: {COMPUTE_FUNCTION_ID}")