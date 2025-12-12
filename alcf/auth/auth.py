from pydantic import BaseModel
from typing import Dict
import secrets
from pathlib import Path
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuthError
from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
#from starlette.requests import Request
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_401_UNAUTHORIZED
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi import Request, APIRouter, HTTPException, Form
from fastapi.templating import Jinja2Templates
from alcf.config import (
    KEYCLOAK_SERVER_URL, 
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
    KEYCLOAK_REDIRECT_URI,
    SESSION_MIDDLEWARE_SECRET_KEY
)

# Create OAuth client to make calls to Keycloak
# https://docs.authlib.org/en/latest/client/httpx.html
# https://docs.authlib.org/en/latest/client/oauth2.html
oauth = OAuth()

# Create FastAPI router so that it can be added to the application (from main.py)
auth_router = APIRouter()

# Define where the HTML templates are
BASE_DIR = Path(__file__).resolve()
TEMPLATE_DIR = BASE_DIR.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# Add middleware to save temporary code and state in session
from app.main import app
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_MIDDLEWARE_SECRET_KEY, 
    session_cookie="session",
    max_age=3600,
)

# Load Keycloak config from its .well-known details
oauth = OAuth()
keycloak = oauth.register(
    name="keycloak",
    server_metadata_url=f"{KEYCLOAK_SERVER_URL}/.well-known/openid-configuration",
    client_id=KEYCLOAK_CLIENT_ID,
    client_secret=KEYCLOAK_CLIENT_SECRET,
    client_kwargs={
        "scope": "openid email profile"
    }
)

# Auth login to authenticate user 
@auth_router.get("/auth/login")
async def login(request: Request):
    try:
        return await keycloak.authorize_redirect(request, KEYCLOAK_REDIRECT_URI)
    except OAuthError as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"Authentication failed: {e.error}")
    

# Auth callback after user authentication
@auth_router.get("/auth/callback")
async def auth_callback(request: Request):

    # Collect raw response from Keycloak
    try:
        token = await keycloak.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"Authentication callback failed.")
    
    # Extract tokens
    access_token = token.get("access_token")
    if not access_token:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"No access token found in the response.")
    
    # Expose the token on the web page (password-style)
    return templates.TemplateResponse("token.html", {
        "request": request,
        "access_token": access_token
    })
