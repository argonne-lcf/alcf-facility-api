from common_filesystem import submit

# Targeted resource
#resource_id = "7f7d0593-162e-43b9-8476-07d7d137d6ab" # Edith
resource_id = "9674c7e1-aecc-4dbb-bf01-c9197e027cd6" # Sophia

# Build input data
data = {
    "path": "/home/bcote"
}

# Send request to Facility API
submit(
    resource_id=resource_id,
    data=data,
    function="ls",
    method="get"
)
