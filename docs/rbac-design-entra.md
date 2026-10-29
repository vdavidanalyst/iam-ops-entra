# RBAC Design (Entra ID)

This document describes the access model for the Entra ID edition of IAM-Ops. It uses the same mock organization as the Okta edition so the two builds can be compared directly.

## Environment

- **Phases 0 to 4** (tenant setup, repo, SSO, JML scripts) were built in a free Entra ID tenant.
- **Phases 2, 5 and 6** (Conditional Access, PIM, access reviews, sign-in logs) were built in a second tenant with an Entra ID P2 trial, because those features need paid licensing and the first tenant could not attach the trial (see `troubleshooting-log.md`).
- The automation scripts are identical in both tenants; only the `.env` values change.

## Mock organization

Departments: Engineering, Finance, HR, IT.

## Roles and groups

| Role | Group | Access | Justification |
|---|---|---|---|
| Standard Employee | GRP-Standard-Employee | Baseline apps | Minimum access every employee needs; no sensitive systems. |
| Engineering | GRP-Engineering | Baseline plus engineering tools | Team and product work; no finance data. |
| Finance-Sensitive User | GRP-Finance-Sensitive | Baseline plus finance apps | Handles sensitive financial data and is SOX-relevant, so it gets the strictest controls and the most frequent review. |
| IT Admin | GRP-IT-Admin | Scoped administrative roles | Supports the organization without holding broad standing privilege. |

Groups are created by `scripts/create_groups.py` and populated by `provision_user.py` and `move_user.py` using a department-to-group map. Group-based licensing assigns the P2 license through these groups.

## Administrative access (least privilege)

The IT user holds two built-in roles, not Global Administrator:

- Helpdesk Administrator
- Application Administrator

Both are **eligible** assignments managed through Privileged Identity Management (PIM), not permanent ones:

- Activation requires Azure MFA and a written justification.
- Activation is capped at 1 hour.
- Eligibility expires after 1 year and must be re-justified.
- Every activation is recorded in the PIM audit log with its justification.

The tenant owner account keeps a permanent Global Administrator assignment as a recovery path and is excluded from the blocking Conditional Access policies below. In a larger organization this would be a dedicated break-glass account with its own monitoring.

## Conditional Access

Security defaults were disabled because they cannot run alongside Conditional Access. CA03 was created straight away to replace the protection they provided.

| ID | Policy | Users | Control | Rollout |
|---|---|---|---|---|
| CA01 | Require MFA for Finance | GRP-Finance-Sensitive; admin excluded | Require multifactor authentication | Report-only, validated, then enabled |
| CA02 | Block legacy authentication | All users; admin excluded | Block access for legacy clients | Report-only, validated, then enabled |
| CA03 | Require MFA for all users | All users | Require multifactor authentication | Enabled after the admin’s own MFA method was confirmed |

Validation used the What If tool and a real sign-in, checked in the sign-in logs (Report-only tab) before enforcement.
Sign-in logs confirm CA03 evaluated and was satisfied on a real sign-in, while CA01 and CA02 correctly did not apply.

## Why this goes further than the Okta edition

| Area | Okta edition | Entra edition |
|---|---|---|
| Admin access | IT Admin group held scoped roles permanently | Roles are eligible only, with MFA, justification, a time limit and an audit trail |
| MFA scope | Single policy | Group-scoped rules, so Finance can be held to a stricter standard |
| Rollout safety | Not applicable | Report-only mode before enforcement |
| Access review | Scripted only | Native review plus a scripted version (Phase 5) |

## Limitations and what I would change at scale

- The P2 trial is time-limited. Features built on it will not persist after the trial ends, so the evidence is captured in `screenshots/` and the policy definitions are documented here.
- A production tenant would have a dedicated, monitored break-glass account instead of an excluded owner account.
- Approval workflows on role activation were left off because the lab has a single administrator; a real organization would require a second approver for sensitive roles.
- Assigning roles to groups, and assigning groups to applications, depends on license tier; this build assigns roles to individual users where needed.
