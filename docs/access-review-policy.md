# Access Review Policy (Entra ID)

This policy describes how access to the IAM-Ops groups is reviewed, who decides, and what happens to the result. It applies the same model as the Okta edition, using Microsoft Entra access reviews plus a scripted report.

## Purpose

Make sure people keep access only while they need it, and keep evidence of each review that an auditor could follow (for example for SOX-style access certification).

## Scope

All members of the four IAM-Ops groups:

- GRP-Standard-Employee
- GRP-Engineering
- GRP-Finance-Sensitive
- GRP-IT-Admin

GRP-Finance-Sensitive and GRP-IT-Admin are treated as **sensitive groups** because they carry financial data access and administrative roles.

## Cadence

- **Quarterly** for every group, matching the recurrence configured on the native review.
- **Ad hoc** after a security incident, a reorganization, or a bulk joiner/leaver event.
- The scripted report can be run at any time between reviews to catch errors early.

## Roles

| Role | Responsibility |
|---|---|
| Department Manager (mock role) | Reviews members of their own department group and decides approve or deny. |
| Security Lead (mock role) | Reviews the sensitive groups and any cross-department findings. |
| IAM Engineer | Runs the review and the report, applies and verifies the outcome, and keeps the evidence. |

**Separation of duties:** in this lab one person holds all three roles because the tenant has a single administrator. In a real organization the reviewer should not be the person who administers the group, and sensitive groups should be reviewed by someone outside IT.

## Flagging rules (scripted report)

`scripts/access_review.py` judges only accounts that currently hold an IAM-Ops department group, and flags an account when any of these apply:

1. The account is **disabled** but still holds group access.
2. The account belongs to **more than one** department group.
3. The account has **never signed in** and is at least the staleness threshold old.
4. The account has been **inactive** for at least the staleness threshold.

The default threshold is **30 days**. Priority is **High** when a flagged account holds a sensitive group, otherwise **Normal**. Output is a CSV in `docs/`, with the tenant domain redacted (`--redact-domain`) so it is safe to publish.

## Review decisions

- Reviewers record **approve** or **deny** with a written reason for every member.
- If a reviewer does not respond, the default is **no change**, and the item is escalated rather than silently removed.
- A reviewer may override the system recommendation, and the override is recorded with the reason.

## Applying the outcome

1. Stop the review instance when decisions are complete, or let it end on its scheduled date.
2. Confirm the results were applied (Auto apply is enabled; the Results page shows an Apply result).
3. Verify in the directory: the denied member no longer appears in the group.
4. Confirm the removal in the audit log (Remove member from group, with the user and group as targets).
5. Re-run the scripted report and check the denied member no longer holds the group.

## Timelines and escalation

- **High priority** findings (sensitive groups): reviewed and resolved within the same week.
- **Normal priority** findings: resolved within 5 business days.
- Any denied access to a sensitive group is logged with its reason and reported to the Security Lead.

## Evidence kept for each review

- Review configuration and settings
- Reviewer decisions with reasons
- Results page showing the outcome and the apply result
- Directory audit log entry for each removal
- Group membership after the review
- The scripted CSV report from after the review

## Evidence in this repository

| File | What it is |
|---|---|
| `docs/access-certification-report.csv` | The real 30-day report after the review: 5 accounts reviewed, 0 flagged. |
| `docs/access-certification-report-flag-demo.csv` | **Forced-threshold demonstration, not a real finding.** Generated with `--stale-days 0` on accounts that were a day old, purely to show the flagging logic and priority rules working. The flags in this file are not evidence of any access problem. |
| `screenshots/Phase 5/` | Native review configuration, decisions, results, audit entry, group membership, and script output (including the forced run). |

## The review performed in this project

- **Review:** Q4 Finance-Sensitive access review, scoped to GRP-Finance-Sensitive.
- **Recurrence:** quarterly. The first instance was stopped early so the outcome could be applied and verified.
- **Reviewer:** a single selected reviewer (the administrator).
- **Decision:** one member was initially approved, then changed to denied with the reason “Left the finance team”, overriding the system recommendation of Approve.
- **Result:** the denial was applied by Access Reviews and the group now has no members. The before-and-after scripted runs show the same account flagged High before the review and not flagged after.

## Limitations

- The review covered a single member, so it demonstrates the workflow rather than review volume.
- The tenant uses a time-limited Entra ID P2 trial. Native access reviews will not be available after it ends; the evidence and this policy remain.
- The staleness rules rely on sign-in data, so very new accounts are not judged until they reach the threshold.
