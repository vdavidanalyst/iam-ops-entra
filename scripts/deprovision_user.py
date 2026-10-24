import sys
import argparse
from graph_client import (
    graph,
    find_group,
    get_user,
    managed_memberships,
    log_action,
    DEPARTMENT_GROUPS,
)


def deprovision(upn, dry_run):
    user = get_user(upn)
    if not user:
        print(f"User not found: {upn}")
        sys.exit(1)

    groups = managed_memberships(user["id"])
    print(f"User:             {user['displayName']} ({user['userPrincipalName']})")
    print(f"Account enabled:  {user['accountEnabled']}")
    print(f"IAM-Ops groups:   {groups}")

    # Guardrail: only act on accounts this tool manages, so it can never disable
    # the admin account or other unmanaged identities by mistake.
    if not groups:
        print("Refusing: user is not in any IAM-Ops department group.")
        sys.exit(1)

    if dry_run:
        print(
            "\n[DRY RUN] Would disable the account, revoke sign-in sessions and remove all group memberships. No changes made."
        )
        return

    r = graph("PATCH", f"/users/{user['id']}", json={"accountEnabled": False})
    if r.status_code != 204:
        print(f"Failed to disable account: {r.status_code} {r.text}")
        log_action(
            "deprovisioning.log",
            {
                "action": "deprovision_failed",
                "upn": upn,
                "step": "disable",
                "status": r.status_code,
            },
        )
        sys.exit(1)
    print("Account disabled.")

    # Disabling does not end sessions that already exist, so revoke them explicitly.
    r = graph("POST", f"/users/{user['id']}/revokeSignInSessions")
    revoked = r.status_code == 200
    print(
        "Sign-in sessions revoked."
        if revoked
        else f"Session revocation failed: {r.status_code} {r.text}"
    )

    # Disabling also leaves group memberships in place, so remove them.
    removed = []
    for name in groups:
        group = find_group(name)
        d = graph("DELETE", f"/groups/{group['id']}/members/{user['id']}/$ref")
        if d.status_code in (204, 404):
            removed.append(name)
    print(f"Removed from groups: {removed}")

    after = managed_memberships(user["id"])
    print(f"Group memberships after: {after}")

    log_action(
        "deprovisioning.log",
        {
            "action": "deprovision",
            "upn": upn,
            "user_id": user["id"],
            "groups_before": groups,
            "groups_after": after,
            "sessions_revoked": revoked,
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Deprovision (disable) a user in Entra ID")
    p.add_argument("--upn", required=True)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    deprovision(a.upn, a.dry_run)
