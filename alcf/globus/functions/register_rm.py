from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode
from globus_compute_sdk import Client
import json
import os

# Constants
FILE_NAME = "function_ids.json"
COMMAND = "rm"

# Globus Compute function definition (rm)
def rm(params):

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

    # Validate input data
    try:
        input_data = InputData(**params)
    except ValueError as e:
        return Response(error=f"Input validation error: {e}").model_dump()
    except Exception:
        return Response(error="Unexpected error occurred during pydantic validation.").model_dump()

    # Keep the original path string
    path_str = str(input_data.path) # E.g. /home/user/my-directory/my-file.txt
    parent_str = str(input_data.path.parent) # E.g. /home/user/my-directory
    name = input_data.path.name # E.g. my-file.txt

    # Ensure target exists without following symlinks
    try:
        st_path = os.lstat(path_str)
    except OSError:
        return Response(error=f"Path does not exist: {input_data.path}").model_dump()

    # ================
    # Define functions
    # ================

    # Define flags/capabilities for secure fd-based removal
    o_nofollow = getattr(os, "O_NOFOLLOW", None)
    o_directory = getattr(os, "O_DIRECTORY", None)
    supports_dir_fd = getattr(os, "supports_dir_fd", set())
    use_secure_fd_ops = (
        o_nofollow is not None
        and o_directory is not None
        and os.unlink in supports_dir_fd
        and os.rmdir in supports_dir_fd
    )

    # File removal via dir_fd from parent fd
    def secure_remove_file(path_str, parent_str, name):
        fd = None
        parent_fd = None

        # Open the file to be removed using the full path string
        try:
            fd = os.open(path_str, os.O_RDONLY | o_nofollow)
        except OSError:
            return Response(error=f"Could not open file {path_str}.").model_dump()

        # Get the inode of the file
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                return Response(error="Expected a regular file, got something else.").model_dump()
            inode_before = (st.st_ino, st.st_dev)
        finally:
            os.close(fd)

        # Open the parent directory containing the file to be removed
        try:
            parent_fd = os.open(parent_str, os.O_RDONLY | o_directory | o_nofollow)
        except OSError:
            return Response(error=f"Could not open parent directory {parent_str}.").model_dump()

        try:
            # Gather the inode of the file using the parent directory fd
            child_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (child_stat.st_ino, child_stat.st_dev) != inode_before:
                return Response(
                    error="File changed during operation (inode mismatch)."
                ).model_dump()

            # Remove the file from the parent directory
            os.unlink(name, dir_fd=parent_fd)

        # Error if something went wrong
        except OSError:
            return Response(error=f"Could not remove file {name} from parent directory {parent_str}.").model_dump()

        # Close the parent directory before returning or raising an error
        finally:
            os.close(parent_fd)

        # Return success message
        return Response(output=f"File {path_str} removed.").model_dump()

    # Recursively remove directory content via dir_fd operations
    def remove_tree_fd(dir_fd):

        # Get list of entries to be removed from the input directory
        try:
            entries = list(os.scandir(dir_fd))
        except OSError:
            return Response(error=f"Could not get list of entries from directory.").model_dump()

        # For each entry in that directory ...
        for entry in entries:
            entry_name = entry.name
            
            # Get the inode of the entry
            try:
                entry_stat = os.stat(entry_name, dir_fd=dir_fd, follow_symlinks=False)
            except OSError:
                return Response(error=f"Could not get inode of entry {entry_name}.").model_dump()

            # Refuse symlink entries explicitly.
            if stat.S_ISLNK(entry_stat.st_mode):
                raise OSError("Symlinks are not allowed during recursive deletion.")

            # If the entry is a directory ...
            if stat.S_ISDIR(entry_stat.st_mode):

                # Open the directory to be removed
                try:
                    child_fd = os.open(
                        entry_name,
                        os.O_RDONLY | o_directory | o_nofollow,
                        dir_fd=dir_fd,
                    )
                except OSError:
                    return Response(error=f"Could not open directory {entry_name}.").model_dump()

                try:
                    # Error if the entry was changed during the operation (inode mismatch)
                    child_stat = os.fstat(child_fd)
                    if (child_stat.st_ino, child_stat.st_dev) != (
                        entry_stat.st_ino,
                        entry_stat.st_dev,
                    ):
                        raise OSError("File changed during operation (inode mismatch).")

                    # Recursively remove content of the directory to be removed
                    remove_tree_fd(child_fd)

                # Close the child directory before returning or raising an error
                finally:
                    os.close(child_fd)

                # Remove the now-empty directory from the input parent directory
                try:
                    os.rmdir(entry_name, dir_fd=dir_fd)
                except OSError:
                    return Response(error=f"Could not remove directory {entry_name} from parent directory {dir_fd}.").model_dump()

            # If the entry is a file ...
            else:
                try:
                    # Re-check inode right before delete to detect swaps.
                    entry_stat_after = os.stat(
                        entry_name, dir_fd=dir_fd, follow_symlinks=False
                    )
                    if (entry_stat_after.st_ino, entry_stat_after.st_dev) != (
                        entry_stat.st_ino,
                        entry_stat.st_dev,
                    ):
                        raise OSError("File changed during operation (inode mismatch).")

                    # Remove the file from the input parent directory
                    os.unlink(entry_name, dir_fd=dir_fd)

                # Error if something went wrong
                except OSError:
                    return Response(error=f"Could not remove file {entry_name} from parent directory.").model_dump()

    # Directory removal via dir_fd from parent fd
    def secure_remove_dir(path_str, parent_str, name):
        parent_fd = None
        child_fd = None
        try:
            # Open the parent directory containing the directory to be removed
            parent_fd = os.open(parent_str, os.O_RDONLY | o_directory | o_nofollow)

            # Get the inode of the directory to be removed
            child_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)

            # Error if the target is not a directory
            if not stat.S_ISDIR(child_stat.st_mode):
                return Response(error="Expected a directory, got something else.").model_dump()

            # Open the child directory, which is the directory to be removed
            try:
                child_fd = os.open(
                    name,
                    os.O_RDONLY | o_directory | o_nofollow,
                    dir_fd=parent_fd,
                )
            except OSError:
                return Response(error=f"Could not open directory {name}.").model_dump()

            try:
                # Error if the entry was changed during the operation (inode mismatch)
                child_open_stat = os.fstat(child_fd)
                if (child_open_stat.st_ino, child_open_stat.st_dev) != (
                    child_stat.st_ino,
                    child_stat.st_dev,
                ):
                    return Response(
                        error="Directory changed during operation (inode mismatch)."
                    ).model_dump()

                # Recursively remove directory content
                remove_tree_fd(child_fd)

            # Error if something went wrong
            except OSError:
                return Response(error=f"Could not recursively remove content of {name}.").model_dump()

            # Close the child directory before returning or raising an error
            finally:
                os.close(child_fd)

            # Re-check inode before removing final directory entry.
            try:
                child_stat_after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except OSError:
                return Response(error=f"rm error: {e}").model_dump()
            if (child_stat_after.st_ino, child_stat_after.st_dev) != (
                child_stat.st_ino,
                child_stat.st_dev,
            ):
                return Response(
                    error="Directory changed during operation (inode mismatch)."
                ).model_dump()

            # Remove the now-empty directory from the parent directory
            try:
                os.rmdir(name, dir_fd=parent_fd)
            except OSError:
                return Response(error=f"Could not remove directory {name} from parent directory.").model_dump()

        # Error if something went wrong
        except OSError:
            return Response(error=f"Could not remove directory {name} from parent directory.").model_dump()

        # Close the parent directory before returning or raising an error
        finally:
            if parent_fd is not None:
                os.close(parent_fd)

        # Return success message
        return Response(output=f"Directory {path_str} removed.").model_dump()

    # ======================
    # Execute the rm command
    # ======================

    if not use_secure_fd_ops:
        return Response(
            error="Platform does not support required secure dir_fd operations."
        ).model_dump()

    # Error if trying to remove root directory
    if path_str in ("/", "\\"):
        return Response(error="Cannot remove root directory.").model_dump()

    # Refuse deleting a symlink target path.
    if stat.S_ISLNK(st_path.st_mode):
        return Response(error="Symlink targets are not allowed.").model_dump()

    # Remove file
    if stat.S_ISREG(st_path.st_mode):
        return secure_remove_file(path_str, parent_str, name)

    # Remove directory
    if stat.S_ISDIR(st_path.st_mode):
        return secure_remove_dir(path_str, parent_str, name)

    # Error if path is not a file or directory
    return Response(
        error=f"Path is not a file or directory: {input_data.path}"
    ).model_dump()


# Create Globus Compute client
gcc = Client(code_serialization_strategy=CombinedCode())

# Register the function
COMPUTE_FUNCTION_ID = gcc.register_function(rm, public=True)

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