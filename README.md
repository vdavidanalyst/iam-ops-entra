# IAM-Ops: Entra ID Edition

Companion to [IAM-Ops (Okta)](https://github.com/vdavidanalyst/iam-ops). The same identity lifecycle and access governance project, rebuilt on Microsoft Entra ID with Python and the Microsoft Graph API, including Conditional Access, Privileged Identity Management and native access reviews.

Read [`docs/okta-vs-entra.md`](docs/okta-vs-entra.md) for what building it twice taught me about the differences between the platforms.

## Read this first: what is live and what is evidence

- **Two tenants.** Phases 0 to 4 (setup, SSO, user lifecycle scripts) were built in a free Entra ID tenant. Phases 2, 5 and 6 (Conditional Access, PIM, access reviews, sign-in logs) were built in a second tenant on a **time-limited Entra ID P2 trial**, because those features need paid licensing and the first tenant could not attach the trial.
- **The trial ends.** The P2 features will not stay available. The evidence is in `screenshots/` and the policy definitions are written up in `docs/`.
- **Labelled test data.** `docs/access-certification-report-flag-demo.csv` is a forced-threshold run, not a real finding, and the incident scenario is a controlled test with deliberately failed sign-ins.
- **Scheduling.** The sign-in review runs from a wrapper script that I run manually. I tried Windows Task Scheduler and could not make it run, so no scheduled execution is claimed here. See [`docs/deployment.md`](docs/deployment.md).

## What this demonstrates

| Job requirement | Where it is shown |
|---|---|
| Design, deploy and maintain IAM solutions | Two configured Entra tenants, with the Okta build in the companion repo |
| SSO, MFA, federation | OIDC and SAML sign-in; security defaults on the free tenant; Conditional Access MFA policies on the P2 tenant |
| SAML and OIDC integration | `demo-app/main.py` (OIDC) and a SAML enterprise app tested against a SAML test service provider |
| Joiner, mover, leaver | `scripts/provision_user.py`, `move_user.py`, `deprovision_user.py` |
| Automate provisioning and deprovisioning | Graph API scripts with logging, a dry-run flag, session revocation and a guardrail that refuses accounts outside the IAM-Ops groups |
| RBAC | [`docs/rbac-design-entra.md`](docs/rbac-design-entra.md) and group creation in `scripts/create_groups.py` |
| Access reviews and certifications | A native quarterly review plus `scripts/access_review.py` and [`docs/access-review-policy.md`](docs/access-review-policy.md) |
| Least privilege | Admin roles as PIM eligible assignments, separate app registrations for automation and login, read-only permissions where write is not needed |
| Compliance support | Review policy, evidence kept per review, audit log entries for removals |
| Monitor identity incidents | `scripts/pull_signin_logs.py` and [`docs/incident-scenario-entra.md`](docs/incident-scenario-entra.md) |
| Audit logs and documentation | `logs/signins.jsonl` and [`docs/troubleshooting-log.md`](docs/troubleshooting-log.md) |
| APIs and scripting | Python against Microsoft Graph through MSAL |
| Work across more than one platform | [`docs/okta-vs-entra.md`](docs/okta-vs-entra.md) |

## What I built

- **User lifecycle.** Create department groups, provision users with a temporary password and a forced change at first sign-in, move them between department groups, and deprovision them by disabling the account, revoking sessions and removing group memberships.
- **Conditional Access.** Three policies rolled out in Report-only mode, validated with the What If tool and a real sign-in, then enabled: MFA for the Finance group, a block on legacy authentication, and MFA for all users. Security defaults were turned off because they cannot run alongside Conditional Access.
- **PIM.** Helpdesk Administrator and Application Administrator are eligible assignments with MFA, a justification and a one-hour limit. An activation was tested and appears in the audit log.
- **Access review.** A native review of the Finance group, one member denied and the result applied, confirmed in the group membership and the audit log, then checked again with the scripted report.
- **Detection.** Three rules over the sign-in logs: a burst of failed sign-ins, sign-ins blocked by Conditional Access, and sign-ins from different countries within an hour. Only the first fired on real events.

## Repository structure

```
iam-ops-entra/
├── demo-app/                  FastAPI OIDC demo (first tenant)
│   └── main.py
├── scripts/
│   ├── graph_client.py        token handling, Graph helper, shared settings
│   ├── create_groups.py
│   ├── provision_user.py
│   ├── move_user.py
│   ├── deprovision_user.py
│   ├── access_review.py
│   ├── pull_signin_logs.py
│   ├── run_signin_review.ps1  manual runner that logs its own output
│   └── test_connection.py
├── docs/                      design, policy, incident, deployment and comparison docs
├── logs/                      stored sign-in events (user names only, no IP addresses or domain)
├── screenshots/               evidence, organised by phase
├── requirements.txt
└── .env.example
```

## Setup

1. Clone the repo, create a virtual environment and install `requirements.txt`.
2. Register an app in your Entra tenant for automation, create a client secret, and add these Microsoft Graph **application** permissions with admin consent: `User.ReadWrite.All`, `Group.ReadWrite.All`, `AuditLog.Read.All`, `Policy.Read.ConditionalAccess`. These four worked in my tenant.
3. Copy `.env.example` to `.env` and fill in the tenant ID, client ID, client secret and your tenant’s `.onmicrosoft.com` domain.
4. Run `python scripts/test_connection.py`; it prints the roles in the token and lists users.
5. Create the groups with `python scripts/create_groups.py`, then use the provisioning, move and deprovisioning scripts.
6. The sign-in and Conditional Access checks need Entra ID P1 or P2 licensing. The demo app needs its own web app registration and the `ENTRA_WEB_*` values.

Always run the access review with `--redact-domain` before committing its report, so the tenant domain stays out of the repository.

## Key design decisions

- **Two app registrations.** The login app and the automation app are separate, so the sign-in app does not share a secret with an app that can write to users and groups.
- **Report-only first.** Every blocking Conditional Access policy was validated before enforcement, and the admin account was excluded to avoid locking out the only administrator.
- **Guardrails in the scripts.** Deprovisioning refuses to touch an account that is not in an IAM-Ops group, and I confirmed it refuses my own admin account.
- **Nothing sensitive in the repo.** Stored logs keep only the user name before the `@` and no IP addresses, and report scripts can redact the tenant domain.

## What I would change at scale

- A dedicated, monitored break-glass account instead of an excluded owner account.
- Certificate credentials or a managed identity instead of a client secret in a file.
- A hosted scheduler with alerting when a run fails or produces nothing.
- Logs sent to a central store with longer retention, and alerts when a detection rule fires.
- Entra ID Protection risk policies, and a second approver on sensitive PIM roles.

## Documentation

- [`docs/okta-vs-entra.md`](docs/okta-vs-entra.md): what differed between the two builds
- [`docs/rbac-design-entra.md`](docs/rbac-design-entra.md): groups, roles, PIM and Conditional Access
- [`docs/access-review-policy.md`](docs/access-review-policy.md): cadence, rules, evidence and the review performed
- [`docs/incident-scenario-entra.md`](docs/incident-scenario-entra.md): controlled failed sign-in test and response
- [`docs/deployment.md`](docs/deployment.md): what ran where, including the scheduling attempt that did not work
- [`docs/troubleshooting-log.md`](docs/troubleshooting-log.md): problems I hit and how I resolved them

## Author

Victor David Sarkibaka · [GitHub](https://github.com/vdavidanalyst) · [X](https://x.com/vdanalyst1)