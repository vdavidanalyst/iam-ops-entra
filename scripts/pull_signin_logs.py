import json
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from graph_client import graph, GRAPH, ROOT, log_action

# Error codes that mean "success" or "more input needed", not a failed sign-in.
# This list is a tunable assumption: 0 success, 50074/50076/50072/50079 MFA
# required or enrollment prompts, 50140 "stay signed in" prompt.
NOT_FAILURES = {0, 50074, 50076, 50072, 50079, 50140}
FAIL_THRESHOLD = 3
FAIL_WINDOW_MIN = 10
TRAVEL_WINDOW_MIN = 60
OUT = ROOT / "logs" / "signins.jsonl"


def paged(path):
    url = path
    while url:
        r = graph("GET", url)
        if r.status_code != 200:
            raise RuntimeError(f"{r.status_code}: {r.text}")
        data = r.json()
        yield from data["value"]
        nxt = data.get("@odata.nextLink")
        url = nxt.replace(GRAPH, "") if nxt else None


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def slim(e):
    st = e.get("status") or {}
    loc = e.get("location") or {}
    return {
        "time": e["createdDateTime"],
        "user": (e.get("userPrincipalName") or "").split("@")[
            0
        ],  # no tenant domain in stored logs
        "app": e.get("appDisplayName"),
        "error": st.get("errorCode", 0),
        "reason": st.get("failureReason"),
        "country": loc.get("countryOrRegion"),
        "ca_status": e.get("conditionalAccessStatus"),
        "ca": [
            {"policy": p.get("displayName"), "result": p.get("result")}
            for p in (e.get("appliedConditionalAccessPolicies") or [])
        ],
    }  # IP addresses are deliberately not stored


def failure_clusters(records):
    by_user = defaultdict(list)
    for r in records:
        if r["error"] not in NOT_FAILURES:
            by_user[r["user"]].append(parse(r["time"]))
    found = []
    for user, times in by_user.items():
        times.sort()
        for i in range(len(times) - FAIL_THRESHOLD + 1):
            if times[i + FAIL_THRESHOLD - 1] - times[i] <= timedelta(
                minutes=FAIL_WINDOW_MIN
            ):
                found.append((user, times[i], times[i + FAIL_THRESHOLD - 1]))
                break
    return found


def country_changes(records):
    by_user = defaultdict(list)
    for r in records:
        if r["error"] == 0 and r["country"]:
            by_user[r["user"]].append((parse(r["time"]), r["country"]))
    found = []
    for user, items in by_user.items():
        items.sort()
        for (t1, c1), (t2, c2) in zip(items, items[1:]):
            if c1 != c2 and t2 - t1 <= timedelta(minutes=TRAVEL_WINDOW_MIN):
                found.append((user, c1, c2, t1, t2))
    return found


def pim_activations(since):
    path = (
        "/auditLogs/directoryAudits?$filter=activityDisplayName eq "
        f"'Add member to role completed (PIM activation)' and activityDateTime ge {since}&$top=50"
    )
    out = []
    try:
        for e in paged(path):
            who = ((e.get("initiatedBy") or {}).get("user") or {}).get(
                "userPrincipalName", ""
            )
            out.append(
                (
                    e["activityDateTime"],
                    who.split("@")[0],
                    [
                        t.get("displayName")
                        for t in e.get("targetResources", [])
                        if t.get("type") == "Role"
                    ],
                )
            )
    except RuntimeError as err:
        print(f"(PIM activation lookup skipped: {err})")
    return out


def run(hours):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    raw = list(paged(f"/auditLogs/signIns?$filter=createdDateTime ge {since}&$top=100"))
    records = [slim(e) for e in raw]
    print(f"Pulled {len(records)} sign-in events from the last {hours}h.\n")

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    findings = 0

    print("Rule 1: 3+ failed sign-ins within 10 minutes")
    clusters = failure_clusters(records)
    for user, start, end in clusters:
        findings += 1
        print(f"  FLAG {user}: {start:%H:%M:%S} to {end:%H:%M:%S} UTC")
    if not clusters:
        print("  none")
    print()

    print("Rule 2: sign-ins blocked by Conditional Access (error 53003)")
    blocks = [r for r in records if r["error"] == 53003]
    for r in blocks:
        findings += 1
        print(
            f"  FLAG {r['user']} at {r['time']}: {[p['policy'] for p in r['ca'] if p['result'] == 'failure']}"
        )
    if not blocks:
        print("  none")
    print()

    print("Rule 3: successful sign-ins from different countries within 60 minutes")
    moves = country_changes(records)
    for user, c1, c2, t1, t2 in moves:
        findings += 1
        print(f"  FLAG {user}: {c1} -> {c2} between {t1:%H:%M} and {t2:%H:%M} UTC")
    if not moves:
        print("  none")
    print()

    print("PIM role activations (information, not a finding)")
    acts = pim_activations(since)
    for ts, who, targets in acts:
        print(f"  {ts}  {who}  {targets}")
    if not acts:
        print("  none")

    print(f"\n{findings} finding(s). Events saved to {OUT}")
    log_action(
        "signin_review.log",
        {
            "action": "signin_review",
            "events": len(records),
            "findings": findings,
            "hours": hours,
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Pull Entra sign-in logs and flag suspicious patterns"
    )
    p.add_argument("--hours", type=int, default=24)
    a = p.parse_args()
    run(a.hours)
