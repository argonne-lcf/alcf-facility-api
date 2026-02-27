import globus_sdk

# Public Globus Auth client
AUTH_CLIENT_ID = "8b84fc2d-49e9-49ea-b54d-b3a29a70cf31"

# ALCF Facility API Filesystem scope
SCOPE_CLIENT_ID = "6be511f6-a071-471f-9bc0-02a0d0836723"
SCOPE_STRING = f"https://auth.globus.org/scopes/{SCOPE_CLIENT_ID}/filesystem"

# Prepare the authentication flow with the targetted scope
client = globus_sdk.NativeAppAuthClient(client_id=AUTH_CLIENT_ID)
client.oauth2_start_flow(requested_scopes=[SCOPE_STRING])

# Trigger the authentication flow
auth_url = client.oauth2_get_authorize_url()
print("\nCopy-past this URL in your browser to login:\n")
print(auth_url)
print("\nPaste the authorization code here:")
auth_code = input().strip()
print()

# Exchange the returned code for tokens
token_response = client.oauth2_exchange_code_for_tokens(auth_code)

# Collect access token for ALCF Facility API
access_token = token_response.by_resource_server[SCOPE_CLIENT_ID]["access_token"]
