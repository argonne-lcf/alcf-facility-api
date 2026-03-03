from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_compute_sdk import Client
import json
import os

# Constants
FILE_NAME = "function_ids.json"
COMMAND = "tail"

# Globus Compute function definition (tail)
def tail(params):

    # Import all necessary packages
    from pathlib import Path
    from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
    from typing import Literal, Optional
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

    # Maximum number of bytes to read
    MAX_BYTES = 9_958_272  # 9.5 MB

    # Base class that excludes extra fields
    class BaseModelWithForbiddenExtra(BaseModel):
        model_config = ConfigDict(extra="forbid")

    # Pydantic for file content
    ContentUnit = Literal["lines", "bytes"]
    class FileContent(BaseModelWithForbiddenExtra):
        """Content of a file with metadata."""
        content: str
        content_type: ContentUnit
        start_position: int = 0
        end_position: int

    # Pydantic for file response
    class FileResponse(BaseModelWithForbiddenExtra):
        """Response for reading the end of a file."""
        output: Optional[FileContent] = None
        offset: int = 0

    # Pydantic for function response
    class Response(BaseModelWithForbiddenExtra):
        output: Optional[FileResponse] = None
        error: Optional[str] = None

    # Pydantic for input data
    class InputData(BaseModelWithForbiddenExtra):
        path: Path
        file_bytes: Optional[int] = Field(default=None, ge=0, le=MAX_BYTES)
        lines: Optional[int] = Field(default=None, ge=0)
        skip_trailing: Optional[bool] = Field(default=False)

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

        # file_bytes and lines: exactly one must be provided (mutually exclusive)
        @model_validator(mode="after")
        def validate_file_bytes_and_lines(self):
            if self.file_bytes is not None and self.lines is not None:
                raise ValueError("Cannot use 'file_bytes' and 'lines' at the same time.")
            if self.file_bytes is None and self.lines is None:
                raise ValueError("At least one of 'file_bytes' or 'lines' must be provided.")
            return self

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

    # =========================
    # Execute the tail command
    # =========================

    path_str = str(input_data.path)

    # Check if path is a file (not directory)
    if not input_data.path.is_file():
        return Response(error=f"Path is not a file: {input_data.path}").model_dump()

    # Check if O_NOFOLLOW is supported (TOCTOU protection)
    o_nofollow = getattr(os, "O_NOFOLLOW", None)
    if o_nofollow is None:
        return Response(
            error="Platform does not support O_NOFOLLOW; TOCTOU-safe tail unavailable."
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
        file_size = stat_before.st_size

        # If the number of bytes is provided ...
        if input_data.file_bytes is not None:
            read_size = min(input_data.file_bytes, file_size)
            start_offset = max(0, file_size - read_size)
            os.lseek(fd, start_offset, os.SEEK_SET)
            data = os.read(fd, read_size)
            content = data.decode("utf-8", errors="replace")
            bytes_read = len(data)
            response_offset = start_offset

        # If the number of lines is provided ...
        else:
            n_lines = input_data.lines
            if n_lines == 0:
                content = ""
                n_lines_actual = 0
                response_offset = file_size
            else:
                chunks = []
                line_count = 0
                total_bytes = 0
                chunk_size = 8192
                remaining = file_size

                # Read chunks from end until enough lines are collected
                while remaining > 0 and line_count <= n_lines:
                    start = max(0, remaining - chunk_size)
                    read_len = remaining - start
                    os.lseek(fd, start, os.SEEK_SET)
                    chunk = os.read(fd, read_len)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > MAX_BYTES:
                        return Response(error="Content exceeded 9.5 MB limit.").model_dump()
                    chunks.insert(0, chunk)
                    line_count += chunk.count(b"\n")
                    remaining = start

                text = b"".join(chunks).decode("utf-8", errors="replace")
                lines = text.split("\n")
                tail_lines = lines[-n_lines:]
                content = "\n".join(tail_lines)
                n_lines_actual = len(tail_lines)
                response_offset = remaining

        # Remove trailing newline if skip_trailing is True
        if input_data.skip_trailing and content.endswith("\n"):
            content = content.rstrip("\n")

        # Validate that the file was not changed during the operation (inode match)
        stat_after = os.fstat(fd)
        inode_after = (stat_after.st_ino, stat_after.st_dev)
        if inode_before != inode_after:
            return Response(
                error="File changed during operation (inode mismatch)."
            ).model_dump()

        # Build response
        if input_data.file_bytes is not None:
            content_type = "bytes"
            start_position = response_offset
            end_position = response_offset + bytes_read
        else:
            content_type = "lines"
            start_position = 0
            end_position = n_lines_actual
        file_content = FileContent(
            content=content,
            content_type=content_type,
            start_position=start_position,
            end_position=end_position,
        )

        # Format and return response
        file_response = FileResponse(output=file_content, offset=response_offset)
        return Response(output=file_response).model_dump()

    # Error if something went wrong
    except OSError:
        return Response(error=f"Could not execute tail command on file {path_str}.").model_dump()

    # Close file descriptor before returns or raises
    finally:
        os.close(fd)


# Create Globus Compute client
gcc = Client(code_serialization_strategy=CombinedCode())

# Register the function
COMPUTE_FUNCTION_ID = gcc.register_function(tail, public=True)

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