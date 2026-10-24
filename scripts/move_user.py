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


def move(upn, new_department):
    user = get_user(upn)
    if not user:
        print(f"User not found: {upn}")
        sys.exit(1)

    new_group = find_group(DEPARTMENT_GROUPS[new_department])
    if not new_group:
        print("Target group not found. Run create_groups.py first.")
        sys.exit(1)

    before = managed_memberships(user["id"])
    removed = []

    for name in DEPARTMENT_GROUPS.values():
        if name == new_group["displayName"]:
            continue
        group = find_group(name)
        r = graph("DELETE", f"/groups/{group['id']}/members/{user['id']}/$ref")
        if r.status_code == 204:
            removed.append(name)
            print(f"Removed from: {name}")
        elif r.status_code != 404:  # 404 just means they weren't a member
            print(f"Failed to remove from {name}: {r.status_code} {r.text}")
            sys.exit(1)

    r = graph(
        "POST",
        f"/groups/{new_group['id']}/members/$ref",
        json={
            "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user['id']}"
        },
    )
    if r.status_code == 204:
        print(f"Added to: {new_group['displayName']}")
    elif r.status_code == 400 and "already exist" in r.text:
        print(f"Already a member of: {new_group['displayName']}")
    else:
        print(f"Failed to add to {new_group['displayName']}: {r.status_code} {r.text}")
        sys.exit(1)

    p = graph("PATCH", f"/users/{user['id']}", json={"department": new_department})
    if p.status_code != 204:
        print(
            f"Group change done, but updating the department attribute failed: {p.status_code}"
        )

    log_action(
        "moves.log",
        {
            "action": "move",
            "upn": upn,
            "user_id": user["id"],
            "groups_before": before,
            "removed_from": removed,
            "new_group": new_group["displayName"],
            "new_department": new_department,
        },
    )
    print(f"Move complete: {upn} -> {new_department}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Move a user to a new department in Entra ID"
    )
    p.add_argument("--upn", required=True)
    p.add_argument("--new-department", required=True, choices=list(DEPARTMENT_GROUPS))
    a = p.parse_args()
    move(a.upn, a.new_department)
