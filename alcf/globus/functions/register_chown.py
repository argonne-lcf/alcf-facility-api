from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_compute_sdk import Client
import json
import os

# Constants
FILE_NAME = "function_ids.json"
COMMAND = "chown"

# Globus Compute function definition (subprocess - chown)
def chown(params):
    
    # Import all necessary packages
    from pydantic import BaseModel, ConfigDict, field_validator
    from typing import Optional
    import subprocess
    import os

    # Pydantic for function response
    class Response(BaseModel):
        output: Optional[str] = None
        error: Optional[str] = None

    # Pydantic for input data
    class InputData(BaseModel):
        path: str
        owner: str
        group: str
        
        # No extra argument
        model_config = ConfigDict(extra="forbid")

        # No semicolon and shell injection
        @field_validator("path", "owner", "group")
        @classmethod
        def no_semicolon(cls, v: str) -> str:
            if ";" in v:
                raise ValueError("Shell injection not allowed. Semicolon detected.")
            return v

    # Validate input data
    try:
        input_data = InputData(**params)
    except Exception as e:
        return Response(error=f"Input validation error: {str(e)}").model_dump()

    # Check if path exists
    if not os.path.exists(input_data.path):
        return Response(error=f"File {input_data.path} does not exist: {input_data.path}").model_dump()

    # Build command
    cmd = ["chown", f"{input_data.owner}:{input_data.group}", input_data.path]

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
    if result.stderr:
        return Response(error=result.stderr).model_dump()
    
    # Execute an ls command on the path to return the new state
    cmd = ["ls", "-lh", input_data.path]
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