from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_compute_sdk import Client
import json
import os

# Constants
FILE_NAME = "function_ids.json"
COMMAND = "ls"

# Globus Compute function definition (subprocess - ls)
def ls(params):
    
    # Import all necessary packages
    from pydantic import BaseModel, ConfigDict, field_validator
    from typing import Optional
    import subprocess
    import pathlib
    import os
    import re

    # Pydantic for function response
    class Response(BaseModel):
        output: Optional[str] = None
        error: Optional[str] = None

    # Pydantic for input data
    class InputData(BaseModel):
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

    # Validate input data
    try:
        input_data = InputData(**params)
    except Exception as e:
        return Response(error=f"Input validation error: {str(e)}").model_dump()

    # Check if path exists
    if not os.path.exists(input_data.path):
        return Response(error=f"File {input_data.path} does not exist.").model_dump()

    # Build command flags
    flags = "-lh" 
    if input_data.show_hidden:
        flags += "a"
    if input_data.numeric_uid:
        flags += "n"
    if input_data.recursive:
        flags += "R"
    if input_data.dereference:
        flags += "L"

    # Build subprocess command
    cmd = ["ls", flags, input_data.path]

    # Run subprocess command
    try:
        result = subprocess.run(
            cmd,
            check=True,          # Raise error if command fails
            capture_output=True, # Capture stdout/stderr
            text=True,           # Return strings instead of bytes
            shell=False          # Avoid shell injection
        )
    except Exception as e:
        return Response(error=f"subprocess.run error: {str(e)}").model_dump()

    # Return result
    return Response(output=result.stdout, error=result.stderr).model_dump()


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