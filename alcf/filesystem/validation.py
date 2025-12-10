from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
import pathlib
import os
import re


# Input data for chmod command
class ChmodInputData(BaseModel):
    path: str
    mode: str = Field(min_length=3, max_length=4)
    model_config = ConfigDict(extra="forbid")

    # Forbidden characters (prevent shell injection)
    @field_validator("path", "mode")
    @classmethod
    def forbidden_characters(cls, v: str) -> str:
        if not re.compile(r"^[\w\-./\\]+$").fullmatch(v):
            raise ValueError("Field contains forbidden characters.")
        if "\0" in v:
            raise ValueError("Null byte not allowed.")
        return v
        
    # Clean path (prevent remaining traversal)
    @field_validator("path")
    @classmethod
    def clean_path(cls, v: str) -> str:
        v = os.path.normpath(v)
        if ".." in pathlib.PurePath(v).parts:
            raise ValueError("Path traversal components '..' not allowed.")
        return v
        
    # Make sure mode must only contain digits
    @field_validator("mode")
    @classmethod
    def only_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("'mode' must only contains numbers.")
        return v
    

# # Input data for chown command
class ChownInputData(BaseModel):
    path: str
    owner: str
    group: str
    model_config = ConfigDict(extra="forbid")

    # Forbidden characters (prevent shell injection)
    @field_validator("path", "owner", "group")
    @classmethod
    def forbidden_characters(cls, v: str) -> str:
        if not re.compile(r"^[\w\-./\\]+$").fullmatch(v):
            raise ValueError("Field contains forbidden characters.")
        if "\0" in v:
            raise ValueError("Null byte not allowed.")
        return v
        
    # Clean path (prevent remaining traversal)
    @field_validator("path")
    @classmethod
    def clean_path(cls, v: str) -> str:
        v = os.path.normpath(v)
        if ".." in pathlib.PurePath(v).parts:
            raise ValueError("Path traversal components '..' not allowed.")
        return v
    

# Input data for head command
class HeadInputData(BaseModel):
    path: str
    file_bytes: Optional[int] = Field(default=None, ge=0)
    lines: Optional[int] = Field(default=None, ge=0)
    skip_trailing: Optional[bool] = Field(default=False)
    model_config = ConfigDict(extra="forbid")

    # Forbidden characters (prevent shell injection)
    @field_validator("path")
    @classmethod
    def forbidden_characters(cls, v: str) -> str:
        if not re.compile(r"^[\w\-./\\]+$").fullmatch(v):
            raise ValueError("Field contains forbidden characters.")
        if "\0" in v:
            raise ValueError("Null byte not allowed.")
        return v
        
    # Clean path (prevent remaining traversal)
    @field_validator("path")
    @classmethod
    def clean_path(cls, v: str) -> str:
        v = os.path.normpath(v)
        if ".." in pathlib.PurePath(v).parts:
            raise ValueError("Path traversal components '..' not allowed.")
        return v
    

# Input data for ls command
class LsInputData(BaseModel):
    path: str
    show_hidden: bool = False
    numeric_uid: bool = False
    recursive: bool = False
    dereference: bool = False
    model_config = ConfigDict(extra="forbid")

    # Forbidden characters (prevent shell injection)
    @field_validator("path")
    @classmethod
    def forbidden_characters(cls, v: str) -> str:
        if not re.compile(r"^[\w\-./\\]+$").fullmatch(v):
            raise ValueError("Field contains forbidden characters.")
        if "\0" in v:
            raise ValueError("Null byte not allowed.")
        return v
        
    # Clean path (prevent remaining traversal)
    @field_validator("path")
    @classmethod
    def clean_path(cls, v: str) -> str:
        v = os.path.normpath(v)
        if ".." in pathlib.PurePath(v).parts:
            raise ValueError("Path traversal components '..' not allowed.")
        return v
    

# Input data for view command
class ViewInputData(BaseModel):
    path: str
    size: Optional[int] = Field(default=None, ge=0)
    offset: Optional[int] = Field(default=None, ge=0)
    model_config = ConfigDict(extra="forbid")

    # Forbidden characters (prevent shell injection)
    @field_validator("path")
    @classmethod
    def forbidden_characters(cls, v: str) -> str:
        if not re.compile(r"^[\w\-./\\]+$").fullmatch(v):
            raise ValueError("Field contains forbidden characters.")
        if "\0" in v:
            raise ValueError("Null byte not allowed.")
        return v
        
    # Clean path (prevent remaining traversal)
    @field_validator("path")
    @classmethod
    def clean_path(cls, v: str) -> str:
        v = os.path.normpath(v)
        if ".." in pathlib.PurePath(v).parts:
            raise ValueError("Path traversal components '..' not allowed.")
        return v
