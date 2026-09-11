import os
import globus_sdk
from dotenv import load_dotenv
load_dotenv()

# ----------------------------------------------------------------------------
# The following is to generate an access token that will be valid for 48 hours
# ----------------------------------------------------------------------------

# Load your Globus service account client credentials
CLIENT_ID = os.getenv("GLOBUS_SERVICE_ACCOUNT_CLIENT_ID", None)
CLIENT_SECRET = os.getenv("GLOBUS_SERVICE_ACCOUNT_CLIENT_SECRET", None)

# ALCF Facility API Filesystem scope
SCOPE_CLIENT_ID = "6be511f6-a071-471f-9bc0-02a0d0836723"
SCOPE_STRING = f"https://auth.globus.org/scopes/{SCOPE_CLIENT_ID}/filesystem"

# Create an SDK client using the service account credentials
print("\nCreating Globus SDK client using credentials ...")
client = globus_sdk.ConfidentialAppAuthClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

# Request an access token for your targeted scope
print("Generating access token for the ALCF inference scope ...")
token_response = client.oauth2_client_credentials_tokens(requested_scopes=[SCOPE_STRING])

# Extract and print the access token
access_token = token_response.by_resource_server[SCOPE_CLIENT_ID]["access_token"]
print(f"Access token: {access_token}")

# ----------------------------------------------------------------------------
# The following is an optional introspection check to 
# ----------------------------------------------------------------------------

# Introspect token with Globus Auth
introspection = client.post(
    "/v2/oauth2/token/introspect",
    data={"token": access_token, "include":"session_info,identity_set_detail"}, 
    encoding="form",
)

# Display introspection on the terminal
print("\nToken introspection data")
print("------------------------")
print(introspection)