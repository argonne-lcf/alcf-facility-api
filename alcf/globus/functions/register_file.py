from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_compute_sdk import Client
import json
import os

# Constants
FILE_NAME = "function_ids.json"
COMMAND = "file"

# Globus Compute function definition file)
def file(params):

    # Import all necessary packages
    from pathlib import Path
    from pydantic import BaseModel, ConfigDict, field_validator
    from typing import Optional
    import os
    import pwd
    import re
    import stat

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

    # Pydantic for function response
    class Response(BaseModelWithForbiddenExtra):
        output: Optional[str] = None
        error: Optional[str] = None

    # Pydantic for input data
    class InputData(BaseModelWithForbiddenExtra):
        path: Path

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

    # Verify that the path exists
    try:
        st_path = os.lstat(str(input_data.path))
    except OSError:
        return Response(error=f"Path {input_data.path} does not exist.").model_dump()

    # Resolve path and check if it exists
    try:
        input_data.path = input_data.path.resolve(strict=True)
    except OSError:
        return Response(error=f"Path does not exist: {input_data.path}").model_dump()
    if not is_allowed_path(input_data.path):
        return Response(
            error=f"Resolved path must stay under one of: {ALLOWED_PATHS_TEXT}."
        ).model_dump()

    # =========================
    # Execute the file command
    # =========================

    path_str = str(input_data.path)

    # Check if O_NOFOLLOW is supported (TOCTOU protection)
    o_nofollow = getattr(os, "O_NOFOLLOW", None)
    if o_nofollow is None:
        return Response(
            error="Platform does not support O_NOFOLLOW; TOCTOU-safe file unavailable."
        ).model_dump()

    # Open path with O_NOFOLLOW
    try:
        fd = os.open(path_str, os.O_RDONLY | o_nofollow)
    except OSError:
        return Response(error=f"Could not open path {path_str}.").model_dump()

    try:
        # Get inode before operation (for validation)
        stat_before = os.fstat(fd)
        inode_before = (stat_before.st_ino, stat_before.st_dev)

        mode = stat_before.st_mode
        if stat.S_ISREG(mode):
            path_type = "file"
        elif stat.S_ISDIR(mode):
            path_type = "directory"
        elif stat.S_ISCHR(mode):
            path_type = "character_device"
        elif stat.S_ISBLK(mode):
            path_type = "block_device"
        elif stat.S_ISFIFO(mode):
            path_type = "fifo"
        elif stat.S_ISSOCK(mode):
            path_type = "socket"
        else:
            path_type = "unknown"

        # Validate that the path was not changed during the operation (inode match)
        stat_after = os.fstat(fd)
        inode_after = (stat_after.st_ino, stat_after.st_dev)
        if inode_before != inode_after:
            return Response(
                error="Path changed during operation (inode mismatch)."
            ).model_dump()

        # Return type of path
        return Response(output=path_type).model_dump()

    # Error if something went wrong
    except OSError:
        return Response(error=f"Could not execute file command on path {path_str}.").model_dump()

    # Close file descriptor before returns or raises
    finally:
        os.close(fd)

# Create Globus Compute client
gcc = Client(code_serialization_strategy=CombinedCode())

# Register the function
COMPUTE_FUNCTION_ID = gcc.register_function(file, public=True)

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