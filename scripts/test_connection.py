import os
import sys
import json
import base64
import requests
import msal
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TENANT_ID = os.getenv("ENTRA_TENANT_ID")
CLIENT_ID = os.getenv("ENTRA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ENTRA_CLIENT_SECRET")

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
    raise RuntimeError(
        "Missing ENTRA_TENANT_ID, ENTRA_CLIENT_ID or ENTRA_CLIENT_SECRET in .env"
    )

app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET,
)

result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

if "access_token" not in result:
    print("Token request failed:")
    print(result.get("error"))
    print(result.get("error_description"))
    sys.exit(1)

token = result["access_token"]

# Decode the token payload (no verification, display only) to show which
# application permissions were actually granted.
payload = token.split(".")[1]
payload += "=" * (-len(payload) % 4)
claims = json.loads(base64.urlsafe_b64decode(payload))
print(
    "Token acquired. Granted roles:",
    claims.get("roles", "NONE - admin consent missing"),
)

resp = requests.get(
    "https://graph.microsoft.com/v1.0/users?$select=displayName,userPrincipalName,accountEnabled",
    headers={"Authorization": f"Bearer {token}"},
)
print(f"\nGraph status: {resp.status_code}")

if resp.status_code == 200:
    for u in resp.json()["value"]:
        print(
            f"  {u['displayName']:<20} {u['userPrincipalName']:<50} enabled={u['accountEnabled']}"
        )
else:
    print(json.dumps(resp.json(), indent=2))
