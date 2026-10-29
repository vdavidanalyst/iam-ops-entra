# Deployment

This document records how the IAM-Ops automation was run outside a laptop, what worked, and what did not.

## Okta edition (GCP VM)

The Okta project was deployed to a Google Cloud VM during the GCP free trial:

- The FastAPI demo app ran as a `systemd` service.
- The weekly access review ran from `cron`.
- The app was bound to `127.0.0.1` after I found it reachable from the internet through a pre-existing firewall rule shared with another project. I hardened the app instead of editing a rule I did not own. See the Okta repository’s troubleshooting log, entry 11.

The GCP free trial has since ended, so this deployment is documented by its screenshots and repository rather than as a live system.

## Entra ID edition

The Entra scripts were not deployed to a VM. The demo app was left out because its registration belongs to the first tenant, and the SSO flows are already evidenced in Phase 3.

- `scripts/run_signin_review.ps1` runs the sign-in review (`pull_signin_logs.py --hours 24`) and appends its output and exit code to `logs/task_run.log`.
- It was run **manually**. The log shows the pulled events, the rule results and `exit code: 0`.

### Scheduling attempt (not working)

I tried to schedule the wrapper with Windows Task Scheduler. The task reported a last result of 0, but it produced no output. Two minimal test tasks that only append a line to a file produced nothing either. The wrapper, the task definition, the account and the Task Scheduler service were all checked and looked correct, and the cause was not identified. I removed the task instead of leaving one that reported success without running.

No scheduled execution is claimed for the Entra scripts. The scheduling evidence for this portfolio is the Okta project’s `cron` job. The lesson: a result code of 0 does not prove a scheduled job ran, so a scheduled job needs its own log line.

### Dependency on the P2 trial

The sign-in log and Conditional Access checks use data that needs Entra ID P2 licensing. After the trial ends, those scripts are expected to return errors or reduced data. The evidence for Phases 2, 5 and 6 was captured while the trial was active.

## What production would look like

- A hosted scheduler (a managed job service, or `cron`/`systemd` timers on a server) with alerting when a run fails or produces no output.
- A managed identity or a secrets manager instead of a `.env` file holding a client secret.
- Certificate credentials for the automation app instead of a secret, with rotation.
- Logs sent to a central store with longer retention than the portal keeps.
