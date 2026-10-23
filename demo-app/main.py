import os
import html
import secrets
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TENANT_ID = os.getenv("ENTRA_TENANT_ID")
CLIENT_ID = os.getenv("ENTRA_WEB_CLIENT_ID")
CLIENT_SECRET = os.getenv("ENTRA_WEB_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ENTRA_REDIRECT_URI")

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
    raise RuntimeError("Missing Entra web app settings in .env")

app = FastAPI(title="IAM-Ops Entra Portal")
# Random per-start secret; sessions reset whenever the app restarts (fine for a demo).
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET") or secrets.token_urlsafe(32),
)

oauth = OAuth()
oauth.register(
    name="entra",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url=f"https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration",
    client_kwargs={"scope": "openid profile email"},
)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("user")
    if user:
        name = html.escape(user.get("name", "Unknown"))
        upn = html.escape(user.get("preferred_username", "Unknown"))
        return f"""
        <h2>IAM-Ops Entra Portal</h2>
        <p>Logged in as: {name} ({upn})</p>
        <a href="/logout">Logout</a>
        """
    return """
    <h2>IAM-Ops Entra Portal</h2>
    <a href="/login">Login with Microsoft Entra ID</a>
    """


@app.get("/login")
async def login(request: Request):
    return await oauth.entra.authorize_redirect(request, REDIRECT_URI)


@app.get("/authorization-code/callback")
async def callback(request: Request):
    try:
        token = await oauth.entra.authorize_access_token(request)
    except OAuthError as e:
        return HTMLResponse(
            f"<h3>Sign-in failed</h3><p>{html.escape(e.error)}</p><a href='/'>Back</a>",
            status_code=400,
        )

    claims = token.get("userinfo") or {}
    # Keep only what the app needs; session cookies have a size limit.
    request.session["user"] = {
        "name": claims.get("name"),
        "preferred_username": claims.get("preferred_username"),
        "oid": claims.get("oid"),
        "tid": claims.get("tid"),
    }
    return RedirectResponse(url="/")


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")
