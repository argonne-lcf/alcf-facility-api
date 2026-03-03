from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_compute_sdk import Client
import json
import os

# Constants
FILE_NAME = "function_ids.json"
COMMAND = "chown"

# Globus Compute function definition (chown)
def chown(params):

    # Import all necessary packages
    from pathlib import Path
    from pydantic import BaseModel, ConfigDict, field_validator, model_validator
    from typing import Optional, Tuple
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

    # Pydantic for function response
    class Response(BaseModelWithForbiddenExtra):
        output: Optional[File] = None
        error: Optional[str] = None

    # Pydantic for input data
    class InputData(BaseModelWithForbiddenExtra):
        path: Path
        user: str
        group: str

        # User validation: ^[a-z][a-z0-9_-]*$, max 32 chars
        # Empty string = don't change.
        @field_validator("user", mode="before")
        @classmethod
        def validate_user_format(cls, v):
            s = str(v)
            if s == "":
                return s
            if s.isdigit():
                raise ValueError("User must be a name, not a numeric ID (digits).")
            if len(s) > 32:
                raise ValueError("User must be at most 32 characters.")
            if not re.fullmatch(r"^[a-z][a-z0-9_-]*$", s):
                raise ValueError("User must match ^[a-z][a-z0-9_-]* pattern.")
            return s

        # Group validation: ^[A-Za-z0-9_-]+$, max 64 chars
        # Empty string = don't change.
        @field_validator("group", mode="before")
        @classmethod
        def validate_group_format(cls, v):
            s = str(v)
            if s == "":
                return s
            if s.isdigit():
                raise ValueError("Group must be a name, not a numeric ID (digits).")
            if len(s) > 64:
                raise ValueError("Group must be at most 64 characters.")
            if not re.fullmatch(r"[A-Za-z0-9_-]+$", s):
                raise ValueError("Group must match [A-Za-z0-9_-]+ pattern.")
            return s

        # At least one of user or group must be non-empty (otherwise nothing to change)
        @model_validator(mode="after")
        def validate_at_least_one(self):
            if self.user == "" and self.group == "":
                raise ValueError("At least one of user or group must be non-empty.")
            return self

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
        return Response(error=f"File {input_data.path} does not exist.").model_dump()

    # Refuse symlink target paths
    try:
        if stat.S_ISLNK(st_path.st_mode):
            return Response(error="Symlink targets are not allowed.").model_dump()
    except OSError:
        return Response(error="Could not verify whether path is a symlink.").model_dump()

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
    def get_user_group(stat_info) -> Tuple[str, str]:
        """Return (user, group) from stat."""

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

    # Resolve user to uid (empty string = use current, don't change)
    def resolve_uid(user: str, stat_before) -> int:
        """Resolve user to uid. Empty string returns current uid."""
        if user == "":
            return stat_before.st_uid
        try:
            return pwd.getpwnam(user).pw_uid
        except KeyError:
            raise ValueError(f"User '{user}' does not exist on the system.")

    # Resolve group to gid (empty string = use current, don't change)
    def resolve_gid(group: str, stat_before) -> int:
        """Resolve group to gid. Empty string returns current gid."""
        if group == "":
            return stat_before.st_gid
        try:
            return grp.getgrnam(group).gr_gid
        except KeyError:
            raise ValueError(f"Group '{group}' does not exist on the system.")

    # Build entry info dictionary
    def build_entry_info(file_path: Path, stat_info: os.stat_result) -> File:
        """Build a dictionary for the details of a file or folder."""

        # Extract file mode
        mode = stat_info.st_mode

        # Extract file type from mode
        file_type = get_file_type(mode)

        # Extract user and group
        user, group = get_user_group(stat_info)

        # Generate last modified timestamp in UTC ISO format
        last_modified = datetime.fromtimestamp(
            stat_info.st_mtime, tz=timezone.utc
        ).isoformat().replace("+00:00", "Z")

        # Set link target to empty since chown will not follow symlinks
        link_target = ""

        # Build and return the entry info dictionary
        return File(
            name=file_path.name,
            type=file_type,
            link_target=link_target,
            user=user,
            group=group,
            permissions=stat.filemode(mode)[1:],
            last_modified=last_modified,
            size=str(stat_info.st_size),
        )

    # =========================
    # Execute the chown command
    # =========================

    path_str = str(input_data.path)

    # Check if O_NOFOLLOW is supported
    o_nofollow = getattr(os, "O_NOFOLLOW", None)
    if o_nofollow is None:
        return Response(
            error="Platform does not support O_NOFOLLOW; TOCTOU-safe chown unavailable."
        ).model_dump()

    # Open file with O_NOFOLLOW
    try:
        fd = os.open(path_str, os.O_RDONLY | o_nofollow)
    except OSError:
        return Response(error=f"Could not open file {path_str}.").model_dump()

    try:
        # Get inode before operation (for validation)
        stat_before = os.fstat(fd)
        inode_before = (stat_before.st_ino, stat_before.st_dev)

        # Resolve user/group to uid/gid (empty = don't change; validates existence when non-empty)
        try:
            uid = resolve_uid(input_data.user, stat_before)
            gid = resolve_gid(input_data.group, stat_before)
        except ValueError:
            return Response(error=f"Could not resolve user or group.").model_dump()

        # Execute the chown command
        os.fchown(fd, uid, gid)

        # If the file was changed during the operation ...
        stat_after = os.fstat(fd)
        inode_after = (stat_after.st_ino, stat_after.st_dev)
        if inode_before != inode_after:

            # Revert to original owner/group and return error
            os.fchown(fd, stat_before.st_uid, stat_before.st_gid)
            return Response(
                error="File changed during operation (inode mismatch); ownership reverted."
            ).model_dump()

        # Extract and return file information
        file_info = build_entry_info(input_data.path, stat_info=stat_after)
        return Response(output=file_info).model_dump()

    # Error if something went wrong
    except OSError:
        return Response(error=f"Could not execute chown command on file {path_str}.").model_dump()

    # Close file descriptor before returns or raises
    finally:
        os.close(fd)


# Create Globus Compute client
gcc = Client(code_serialization_strategy=CombinedCode())

# Register the function
COMPUTE_FUNCTION_ID = gcc.register_function(chown, public=True)

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