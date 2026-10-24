import sys
import time
import secrets
import string
import argparse
from graph_client import graph, find_group, log_action, DOMAIN, DEPARTMENT_GROUPS


def temp_password():
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    # Guarantee all complexity classes, then pad with random characters.
    pw = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
    ]
    pw += [secrets.choice(alphabet) for _ in range(12)]
    secrets.SystemRandom().shuffle(pw)
    return "".join(pw)


def provision(first, last, department, personal_email=None):
    nickname = f"{first}.{last}".lower().replace(" ", "")
    upn = f"{nickname}@{DOMAIN}"
    password = temp_password()

    body = {
        "accountEnabled": True,
        "displayName": f"{first} {last}",
        "givenName": first,
        "surname": last,
        "mailNickname": nickname,
        "userPrincipalName": upn,
        "department": department,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": password,
        },
    }
    if personal_email:
        body["otherMails"] = [personal_email]

    resp = graph("POST", "/users", json=body)
    if resp.status_code != 201:
        print(f"Failed to create user: {resp.status_code}\n{resp.text}")
        log_action(
            "provisioning.log",
            {
                "action": "provision_failed",
                "upn": upn,
                "department": department,
                "status": resp.status_code,
            },
        )
        sys.exit(1)

    user_id = resp.json()["id"]
    print(f"User created: {upn} (ID: {user_id})")

    group = find_group(DEPARTMENT_GROUPS[department])
    if not group:
        print(
            f"Group {DEPARTMENT_GROUPS[department]} not found. Run create_groups.py first."
        )
        sys.exit(1)

    # A brand-new user can take a few seconds to be visible for group operations.
    added = False
    for attempt in range(6):
        r = graph(
            "POST",
            f"/groups/{group['id']}/members/$ref",
            json={
                "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"
            },
        )
        if r.status_code == 204:
            added = True
            break
        time.sleep(3)

    print(
        f"Added to group: {group['displayName']}"
        if added
        else f"Could not add to group (last status {r.status_code}): {r.text}"
    )

    log_action(
        "provisioning.log",
        {
            "action": "provision",
            "upn": upn,
            "user_id": user_id,
            "department": department,
            "group": group["displayName"],
            "group_added": added,
        },
    )

    print(
        "\nTemporary password (shown once, not logged; user must change it at first sign-in):"
    )
    print(password)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Provision a new user in Entra ID")
    p.add_argument("--first-name", required=True)
    p.add_argument("--last-name", required=True)
    p.add_argument("--department", required=True, choices=list(DEPARTMENT_GROUPS))
    p.add_argument(
        "--personal-email", help="Optional contact email stored in otherMails"
    )
    a = p.parse_args()
    provision(a.first_name, a.last_name, a.department, a.personal_email)
