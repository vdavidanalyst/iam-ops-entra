import os
import json
import requests
import msal
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TENANT_ID = os.getenv("ENTRA_TENANT_ID")
CLIENT_ID = os.getenv("ENTRA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ENTRA_CLIENT_SECRET")
DOMAIN = os.getenv("ENTRA_DOMAIN")

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, DOMAIN]):
    raise RuntimeError(
        "Missing ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET or ENTRA_DOMAIN in .env"
    )

GRAPH = "https://graph.microsoft.com/v1.0"

DEPARTMENT_GROUPS = {
    "engineering": "GRP-Engineering",
    "finance": "GRP-Finance-Sensitive",
    "it": "GRP-IT-Admin",
    "standard": "GRP-Standard-Employee",
}

_app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET,
)


def get_token():
    result = _app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        raise RuntimeError(
            f"Token request failed: {result.get('error')} - {result.get('error_description')}"
        )
    return result["access_token"]


def graph(method, path, **kwargs):
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }
    return requests.request(
        method, f"{GRAPH}{path}", headers=headers, timeout=30, **kwargs
    )


def find_group(display_name):
    resp = graph(
        "GET", f"/groups?$filter=displayName eq '{display_name}'&$select=id,displayName"
    )
    resp.raise_for_status()
    items = resp.json()["value"]
    return items[0] if items else None


def log_action(filename, action):
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    action["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(log_dir / filename, "a") as f:
        f.write(json.dumps(action) + "\n")


def get_user(upn):
    r = graph(
        "GET",
        f"/users/{quote(upn, safe='@')}?$select=id,displayName,userPrincipalName,department,accountEnabled",
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def managed_memberships(user_id):
    """Names of the IAM-Ops department groups this user belongs to."""
    found = []
    for name in DEPARTMENT_GROUPS.values():
        group = find_group(name)
        if not group:
            continue
        url = f"/groups/{group['id']}/members?$select=id&$top=999"
        while url:
            r = graph("GET", url)
            r.raise_for_status()
            data = r.json()
            if any(m["id"] == user_id for m in data["value"]):
                found.append(name)
                break
            nxt = data.get("@odata.nextLink")
            url = nxt.replace(GRAPH, "") if nxt else None
    return found
