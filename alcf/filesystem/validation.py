# 
# These validations should be similar to the ones adopted in the Globus functions
#

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_501_NOT_IMPLEMENTED
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Optional
from pathlib import Path
import re


# Define allowed paths
ALLOWED_PATH_BASES = {
    "home": [Path("/home")],
    "eagle": [Path("/eagle"), Path("/lus/eagle")],
}

# Define allowed paths (string version for error messages)
ALLOWED_PATHS_TEXT = []
for paths in ALLOWED_PATH_BASES.values():
    ALLOWED_PATHS_TEXT.extend([str(path) for path in paths])
ALLOWED_PATHS_TEXT = ", ".join(ALLOWED_PATHS_TEXT)

# Function to check whether a path has the right base
def is_allowed_path(path: Path) -> bool:
    return any(
        path == base or path.is_relative_to(base)
        for bases in ALLOWED_PATH_BASES.values()
        for base in bases
    )

# Maximum number of bytes to read
MAX_BYTES = 9_958_272  # 9.5 MB

# Base class that excludes extra fields
class BaseModelWithForbiddenExtra(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Input data for chmod command
class ChmodInputData(BaseModelWithForbiddenExtra):
    path: Path
    mode: int

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
    
    # Path validation: convert string to int
    @field_validator("mode", mode="before")
    @classmethod
    def convert_mode_type(cls, v) -> int:
        int_v = str(v)
        if not int_v.isdigit():
            raise ValueError("'mode' must be digits only.")
        return int_v
        
    # Mode validation: 3 digits, only digits 0-7
    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        str_v = str(v)
        if not len(str_v) == 3:
            raise ValueError("mode must be 3 digits")
        if not re.fullmatch(r"[0-7]+", str_v):
            raise ValueError("mode must contain only digits 0-7")
        return v
    

# # Input data for chown command
class ChownInputData(BaseModelWithForbiddenExtra):
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
    

# Input data for head command
class HeadInputData(BaseModelWithForbiddenExtra):
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
    

# Input data for ls command
class LsInputData(BaseModelWithForbiddenExtra):
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
    

# Input data for rm command
class RmInputData(BaseModelWithForbiddenExtra):
    path: Path

    # Path validation: forbidden chars, absolute required, no ..
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


# Input data for view command
class ViewInputData(BaseModelWithForbiddenExtra):
    path: Path
    size: int = Field(ge=0, le=MAX_BYTES)
    offset: int = Field(ge=0)

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
    

# Function to restrict path based on the target resource
def validate_base_path(path: Path, resource_name: str):

    # Recover the allowed path bases for the given resource
    allowed_bases = ALLOWED_PATH_BASES.get(resource_name.lower(), None)
    if allowed_bases is None:
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED,
            detail=f"{resource_name} not supported yet."
        )

    # For each allowed path base for this resource ...
    for base in allowed_bases:

        # Return if this is the base path of the user's input path
        try:
            if path == base or path.is_relative_to(base):
                return
            
        # Continue search if needed (go to next allowed base path)
        except Exception:
            continue

    # Error if the user's path does not have a valid base path
    allowed_text = ", ".join(str(b) for b in allowed_bases)
    raise HTTPException(
        status_code=HTTP_400_BAD_REQUEST,
        detail=f"Allowed base paths for filesystem {resource_name} are: {allowed_text}."
    )