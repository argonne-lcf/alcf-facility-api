from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from app.routers.filesystem import models as filesystem_models


# Get IRI File from ls line
def get_iri_file_from_ls_line(ls_line: str) -> filesystem_models.File:
    """Convert a raw ls -l line into a IRI File object."""

    # Split line
    line_split = ls_line.split()

    # Build and return File object
    try:
        return filesystem_models.File(
            permissions=line_split[0],
            user=line_split[2],
            group=line_split[3],
            size=line_split[4],
            last_modified=f"{line_split[5]} {line_split[6]} {line_split[7]}",
            type="directory" if line_split[0][0] == "d" else "file",
            name=" ".join(line_split[8:]),
            link_target=""
        )
        
    # Error
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not generate IRI File object: {e}"
        )