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


# Maximum number of bytes to read
MAX_BYTES = 9_958_272  # 9.5 MB


def _validate_path_format(v) -> Path:
    """Re-usable path validation function."""
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


def _validate_path_prefix(p: Path) -> Path:
    """Re-usable path prefix validation function."""
    is_allowed_path = any(
        p == base or p.is_relative_to(base)
        for bases in ALLOWED_PATH_BASES.values()
        for base in bases
    )
    if not is_allowed_path:
        raise ValueError(f"Path must start with one of: {ALLOWED_PATHS_TEXT}.")
    return p


class BaseModelWithForbiddenExtra(BaseModel):
    """Base class that excludes extra fields."""
    model_config = ConfigDict(extra="forbid")


class BaseModelWithPath(BaseModelWithForbiddenExtra):
    """Base class with input path."""
    path: Path

    @field_validator("path", mode="before")
    @classmethod
    def validate_path_format(cls, v) -> Path:
        return _validate_path_format(v)

    @field_validator("path")
    @classmethod
    def validate_path_prefix(cls, p: Path) -> Path:
        return _validate_path_prefix(p)


class ChmodInputData(BaseModelWithPath):
    """Input data for chmod command."""
    mode: int
    
    @field_validator("mode", mode="before")
    @classmethod
    def convert_mode_type(cls, v) -> int:
        int_v = str(v)
        if not int_v.isdigit():
            raise ValueError("'mode' must be digits only.")
        return int_v
        
    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        str_v = str(v)
        if not len(str_v) == 3:
            raise ValueError("mode must be 3 digits")
        if not re.fullmatch(r"[0-7]+", str_v):
            raise ValueError("mode must contain only digits 0-7")
        return v
    

class ChownInputData(BaseModelWithPath):
    """Input data for chown command."""
    user: str
    group: str

    @field_validator("user", mode="before")
    @classmethod
    def validate_user_format(cls, v):
        """User validation: ^[a-z][a-z0-9_-]*$, max 32 chars."""
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

    @field_validator("group", mode="before")
    @classmethod
    def validate_group_format(cls, v):
        """Group validation: ^[A-Za-z0-9_-]+$, max 64 chars."""
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

    @model_validator(mode="after")
    def validate_at_least_one(self):
        """At least one of user or group must be non-empty (otherwise nothing to change)."""
        if self.user == "" and self.group == "":
            raise ValueError("At least one of user or group must be non-empty.")
        return self
    

class FileContentInputData(BaseModelWithPath):
    """Base input data for file content commands (head/tail)."""
    file_bytes: Optional[int] = Field(default=None, ge=0, le=MAX_BYTES)
    lines: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_file_bytes_and_lines(self):
        """file_bytes and lines: exactly one must be provided (mutually exclusive)."""
        if self.file_bytes is not None and self.lines is not None:
            raise ValueError("Cannot use 'file_bytes' and 'lines' at the same time.")
        if self.file_bytes is None and self.lines is None:
            raise ValueError("At least one of 'file_bytes' or 'lines' must be provided.")
        return self


class HeadInputData(FileContentInputData):
    """Input data for head command."""
    skip_trailing: Optional[bool] = Field(default=False)


class TailInputData(FileContentInputData):
    """Input data for tail command."""
    skip_heading: Optional[bool] = Field(default=False)
    

class LsInputData(BaseModelWithPath):
    """Input data for ls command."""
    show_hidden: Optional[bool] = False
    numeric_uid: Optional[bool] = False
    recursive: Optional[bool] = False
    dereference: Optional[bool] = False


class ViewInputData(BaseModelWithPath):
    """Input data for view command."""
    size: int = Field(ge=0, le=MAX_BYTES)
    offset: int = Field(ge=0)


class MkdirInputData(BaseModelWithPath):
    """Input data for mkdir command."""
    parent: Optional[bool] = Field(default=False)
    

def _validate_base_path(path: Path, resource_name: str):
    """Function to restrict path based on the target resource."""

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


def _forbid_hidden_file(path: Path):
    """Raise an error if the path is a hidden file or part of a hidden folder."""
    for part in path.parts:
        if part.startswith(".") and part != ".":
            raise HTTPException(
                detail="Hidden content cannot be part of queries.",
                status_code=HTTP_400_BAD_REQUEST
            )


def validate_data_with_path(input_data: dict, pydantic_class: BaseModel, resource_name: str, forbid_hidden: bool = False):
    """Validate input parameters that include a path, and raise exception if something goes wrong."""
    try:
        validated = pydantic_class(**input_data)
        _validate_base_path(validated.path, resource_name)
        if forbid_hidden:
            _forbid_hidden_file(validated.path)
    except Exception as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Input validation error: {str(e)}")
