from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_compute_sdk import Client
import json
import os

# Constants
FILE_NAME = "function_ids.json"
COMMAND = "ls"

# Globus Compute function definition ls)
def ls(params):

    # Import all necessary packages
    from pathlib import Path
    from pydantic import BaseModel, ConfigDict, field_validator
    from typing import Optional, List
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
        link_target: Optional[str] = ""
        user: str
        group: str
        permissions: str
        last_modified: str
        size: str

    # Pydantic model for function response
    class Response(BaseModelWithForbiddenExtra):
        output: Optional[List[File]] = None
        error: Optional[str] = None

    # Pydantic model for input data
    class InputData(BaseModelWithForbiddenExtra):
        path: Path
        show_hidden: Optional[bool] = False
        numeric_uid: Optional[bool] = False
        recursive: Optional[bool] = False
        dereference: Optional[bool] = False

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

    # Resolve path and check if it exists
    try:
        input_data.path = input_data.path.resolve(strict=True)
    except OSError:
        return Response(error=f"Path does not exist: {input_data.path}").model_dump()
    if not is_allowed_path(input_data.path):
        return Response(
            error=f"Resolved path must stay under one of: {ALLOWED_PATHS_TEXT}."
        ).model_dump()

    # ====================
    # Function definitions
    # ====================

    # Get file type
    def get_file_type(mode: int) -> str:
        """Return file type based on mode."""
        if stat.S_ISDIR(mode):
            return "directory"
        if stat.S_ISLNK(mode):
            return "symlink"
        if stat.S_ISREG(mode):
            return "file"
        return "unknown"

    # Get user and group
    def get_user_group(stat_info, numeric_uid: bool):
        """Return (user, group) - names or numeric UID/GID based on numeric_uid flag."""

        # Numeric user and group
        if numeric_uid:
            return str(stat_info.st_uid), str(stat_info.st_gid)

        # User name
        try:
            user = pwd.getpwuid(stat_info.st_uid).pw_name
        except KeyError:
            user = str(stat_info.st_uid)

        # Group name
        try:
            group = grp.getgrgid(stat_info.st_gid).gr_name
        except KeyError:
            group = str(stat_info.st_gid)

        # Return user and group
        return user, group

    # Build entry info dictionary
    def build_entry_info(
        file_path: Path,
        name: Optional[str] = None,
        stat_info: Optional[os.stat_result] = None,
    ) -> File:
        """Build a dictionary for the details of a file or folder."""

        # Extract file name (use provided name when recursive to include parent path)
        name = name or file_path.name

        # Use provided stat when available (TOCTOU-safe: avoids path.stat() after fd operations)
        if stat_info is None:
            stat_info = file_path.stat(follow_symlinks=input_data.dereference)

        mode = stat_info.st_mode

        # Extract file type from mode
        file_type = get_file_type(mode)

        # Extract user and group
        user, group = get_user_group(stat_info, input_data.numeric_uid)

        # Generate last modified timestamp in UTC ISO format
        last_modified = datetime.fromtimestamp(
            stat_info.st_mtime, tz=timezone.utc
        ).isoformat().replace("+00:00", "Z")

        # Set link target to empty since ls will not follow symlinks
        link_target = ""

        # Build and return the entry info dictionary
        return File(
            name=name,
            type=file_type,
            link_target=link_target,
            user=user,
            group=group,
            permissions=stat.filemode(mode)[1:],
            last_modified=last_modified,
            size=str(stat_info.st_size),
        )

    # Get entry info with TOCTOU protection (open with O_NOFOLLOW, fstat, validate inode)
    def get_entry_info_safe(entry_path: Path, name: str) -> File:
        """Open entry with O_NOFOLLOW, fstat, build info. Raises if file changed during operation."""

        # Open entry with O_NOFOLLOW
        fd = os.open(str(entry_path), os.O_RDONLY | o_nofollow)

        try:
            # Get inode before operation (for validation)
            stat_before = os.fstat(fd)
            inode_before = (stat_before.st_ino, stat_before.st_dev)

            # Build entry info 
            entry_info = build_entry_info(entry_path, name=name, stat_info=stat_before)

            # Validate that the file was not changed during the operation (inode match)
            stat_after = os.fstat(fd)
            inode_after = (stat_after.st_ino, stat_after.st_dev)
            if inode_before != inode_after:
                raise OSError("File changed during ls operation (inode mismatch).")

            # Return entry info if the file was not changed during the operation
            return entry_info

        # Close file descriptor before returns or raises
        finally:
            os.close(fd)

    # Scan all entries of a directory
    def process_directory(dir_path: Path, base_path: str = "") -> list:
        """List directory entries, optionally recursively."""

        # For each entry in the directory ...
        results = []
        try:
            for entry in dir_path.iterdir():

                # Skip hidden entry if necessary
                if not input_data.show_hidden and entry.name.startswith("."):
                    continue

                # rel_path: include parent folder when recursive
                rel_path = os.path.join(base_path, entry.name) if base_path else entry.name

                # TOCTOU-safe: open with O_NOFOLLOW, fstat, validate inode
                entry_info = get_entry_info_safe(entry, rel_path)
                results.append(entry_info)

                # Traverse subdirectory if necessary
                if input_data.recursive and entry_info.type == "directory":
                    results.extend(process_directory(entry, rel_path))

        # Skip directories we can't read
        except PermissionError:
            pass

        # Return list of entries
        return results

    # ======================
    # Execute the ls command
    # ======================

    # Check if O_NOFOLLOW is supported (required for TOCTOU protection)
    o_nofollow = getattr(os, "O_NOFOLLOW", None)
    if o_nofollow is None:
        return Response(
            error="Platform does not support O_NOFOLLOW; TOCTOU-safe ls unavailable."
        ).model_dump()

    # Attempt to process the path
    try:

        # Process directory
        if input_data.path.is_dir():
            results = process_directory(input_data.path)

        # Process file
        else:
            results = [get_entry_info_safe(input_data.path, input_data.path.name)]

    # Error if something went wrong
    except Exception:
        return Response(error=f"Could not ls path {input_data.path}.").model_dump()    

    # Return result
    return Response(output=results).model_dump()


# Create Globus Compute client
gcc = Client(code_serialization_strategy=CombinedCode())

# Register the function
COMPUTE_FUNCTION_ID = gcc.register_function(ls, public=True)

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