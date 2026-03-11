import globus_sdk
import os
from dotenv import load_dotenv
load_dotenv()


# Load AmSC client credentials
GLOBUS_AMSC_CLIENT_ID = os.getenv("GLOBUS_AMSC_CLIENT_ID", None)
GLOBUS_AMSC_CLIENT_SECRET = os.getenv("GLOBUS_AMSC_CLIENT_SECRET", None)

# Create Globus client using the AmSC client credentials
client = globus_sdk.ConfidentialAppAuthClient(
    GLOBUS_AMSC_CLIENT_ID,
    GLOBUS_AMSC_CLIENT_SECRET
)

# Start auth flow
client.oauth2_start_flow(
    redirect_uri="http://localhost:5000/callback",
    requested_scopes=["openid", "profile", "email", "urn:globus:auth:scope:auth.globus.org:view_identities"]
)

# Login and gather the authorization code
authorize_url = client.oauth2_get_authorize_url()
print(f"\nGo to this URL and login:\n\n{authorize_url}")

# After visiting the URL and authorizing, you'll be redirected to http://localhost:5000/callback with a code parameter
# Copy the authorization code from the URL parameters
auth_code = input("\nEnter the authorization code: ")

# Exchange code for tokens
token_response = client.oauth2_exchange_code_for_tokens(auth_code)

# Recover the access token
access_token = token_response.by_resource_server["auth.globus.org"]["access_token"]
print("\nAccess token:", access_token)
