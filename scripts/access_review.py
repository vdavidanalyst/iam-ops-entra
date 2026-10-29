import csv
import argparse
from datetime import datetime, timezone
from graph_client import graph, find_group, log_action, ROOT, GRAPH, DEPARTMENT_GROUPS

SENSITIVE_GROUPS = {"GRP-Finance-Sensitive", "GRP-IT-Admin"}
REPORT = ROOT / "docs" / "access-certification-report.csv"


def paged(path):
    url = path
    while url:
        r = graph("GET", url)
        r.raise_for_status()
        data = r.json()
        yield from data["value"]
        nxt = data.get("@odata.nextLink")
        url = nxt.replace(GRAPH, "") if nxt else None


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def group_membership():
    """Map user id -> IAM-Ops groups the user belongs to."""
    membership = {}
    for name in DEPARTMENT_GROUPS.values():
        group = find_group(name)
        if not group:
            continue
        for m in paged(f"/groups/{group['id']}/members?$select=id&$top=999"):
            membership.setdefault(m["id"], []).append(name)
    return membership


def run(stale_days, redact):
    now = datetime.now(timezone.utc)
    membership = group_membership()
    rows = []

    # signInActivity limits page size to 100
    users = paged(
        "/users?$select=id,displayName,userPrincipalName,accountEnabled,createdDateTime,signInActivity&$top=100"
    )
    for u in users:
        groups = membership.get(u["id"], [])
        activity = u.get("signInActivity") or {}
        seen = [
            parse(activity.get("lastSignInDateTime")),
            parse(activity.get("lastNonInteractiveSignInDateTime")),
        ]
        last = max([t for t in seen if t], default=None)
        created = parse(u.get("createdDateTime"))

        reasons = []
        if groups:  # only judge accounts that actually hold managed access
            if not u["accountEnabled"]:
                reasons.append("Disabled account still holds group access")
            if len(groups) > 1:
                reasons.append("Member of more than one department group")
            if last is None:
                age = (now - created).days if created else 0
                if age >= stale_days:
                    reasons.append(f"Never signed in; account is {age} days old")
            elif (now - last).days >= stale_days:
                reasons.append(f"Inactive {(now - last).days} days")

        flagged = bool(reasons)
        priority = (
            "High"
            if flagged and set(groups) & SENSITIVE_GROUPS
            else ("Normal" if flagged else "")
        )
        upn = u["userPrincipalName"]
        if redact:
            upn = upn.split("@")[0] + "@<tenant>"

        rows.append(
            {
                "Name": u["displayName"],
                "UPN": upn,
                "Enabled": u["accountEnabled"],
                "Groups": "; ".join(groups) if groups else "None",
                "Last sign-in": last.strftime("%Y-%m-%d") if last else "Never",
                "Created": created.strftime("%Y-%m-%d") if created else "",
                "Flagged": "Y" if flagged else "N",
                "Priority": priority,
                "Reason": "; ".join(reasons),
            }
        )
        print(f"{u['displayName']:<22} flagged={'Y' if flagged else 'N'} {priority}")

    REPORT.parent.mkdir(exist_ok=True)
    with open(REPORT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n = sum(r["Flagged"] == "Y" for r in rows)
    print(
        f"\nReviewed {len(rows)} users; {n} flagged (stale threshold {stale_days} days)."
    )
    print(f"Report: {REPORT}")
    log_action(
        "access_review.log",
        {
            "action": "access_review",
            "users": len(rows),
            "flagged": n,
            "stale_days": stale_days,
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Entra ID access review report")
    p.add_argument("--stale-days", type=int, default=30)
    p.add_argument(
        "--redact-domain",
        action="store_true",
        help="Replace the tenant domain in the CSV before committing",
    )
    a = p.parse_args()
    run(a.stale_days, a.redact_domain)
